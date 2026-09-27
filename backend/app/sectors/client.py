from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import settings
from app.sectors.credits import (
    charge_for_status,
    credits_remaining,
    record_credit_event,
    utc_now_iso,
)
from app.sectors.database import get_database
from app.sectors.paths import (
    COMPANIES_SCREENER_NATURAL_LANGUAGE_CREDITS,
    COMPANIES_SCREENER_PATH,
)

logger = logging.getLogger("sectors.client")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5


class SectorsClientError(Exception):
    pass


class SectorsAuthError(SectorsClientError):
    pass


class SectorsCreditBudgetError(SectorsClientError):
    pass


@dataclass
class SectorsResponse:
    status_code: int
    payload: Any
    credits_charged: int
    cache_hit: bool
    path: str


class SectorsClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        force_refresh: bool = False,
        max_credits_this_run: int | None = None,
    ) -> None:
        self.force_refresh = force_refresh
        self.max_credits_this_run = max_credits_this_run
        self._credits_spent_this_run = 0
        self._last_live_request_at = 0.0
        self._owns_http_client = http_client is None
        timeout = httpx.Timeout(settings.sectors_request_timeout_seconds)
        self._http_client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def get(
        self,
        path: str,
        query_parameters: dict[str, Any] | None = None,
        *,
        success_credit_cost: int,
        allow_natural_language: bool = False,
    ) -> SectorsResponse:
        query_parameters = _normalize_query(query_parameters or {})
        used_natural_language_query = "q" in query_parameters
        if used_natural_language_query and not allow_natural_language:
            raise SectorsClientError(
                "Natural-language screener parameter q= costs "
                f"{COMPANIES_SCREENER_NATURAL_LANGUAGE_CREDITS} credits. "
                "Use a structured filter_clause instead."
            )
        if path == COMPANIES_SCREENER_PATH and used_natural_language_query:
            success_credit_cost = COMPANIES_SCREENER_NATURAL_LANGUAGE_CREDITS

        cache_key = _cache_key("GET", path, query_parameters)
        if not self.force_refresh:
            cached = _read_cache(cache_key)
            if cached is not None:
                record_credit_event(
                    path=path,
                    status_code=cached["status_code"],
                    credits_charged=0,
                    cache_hit=True,
                )
                return SectorsResponse(
                    status_code=cached["status_code"],
                    payload=json.loads(cached["response_json"]),
                    credits_charged=0,
                    cache_hit=True,
                    path=path,
                )

        if self.max_credits_this_run is not None:
            if self._credits_spent_this_run + success_credit_cost > self.max_credits_this_run:
                raise SectorsCreditBudgetError(
                    "Run would exceed --max-credits "
                    f"{self.max_credits_this_run}; spent {self._credits_spent_this_run}."
                )
        if credits_remaining() < success_credit_cost:
            raise SectorsCreditBudgetError(
                "Not enough credits remaining in the 1,000 budget for this call."
            )

        response = self._get_with_retry(path, query_parameters)
        credits_charged = charge_for_status(
            status_code=response.status_code,
            success_credit_cost=success_credit_cost,
            used_natural_language_query=used_natural_language_query,
        )
        self._credits_spent_this_run += credits_charged
        record_credit_event(
            path=path,
            status_code=response.status_code,
            credits_charged=credits_charged,
            cache_hit=False,
        )

        payload: Any
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"raw_text": response.text}

        if response.status_code in {401, 403}:
            raise SectorsAuthError(
                "Sectors rejected the API key. Check SECTORS_API_KEY in .env."
            )

        if 200 <= response.status_code < 300:
            _write_cache(
                cache_key=cache_key,
                path=path,
                query_parameters=query_parameters,
                status_code=response.status_code,
                payload=payload,
                credits_charged=credits_charged,
            )

        return SectorsResponse(
            status_code=response.status_code,
            payload=payload,
            credits_charged=credits_charged,
            cache_hit=False,
            path=path,
        )

    def get_all_pages(
        self,
        path: str,
        query_parameters: dict[str, Any] | None = None,
        *,
        success_credit_cost_per_page: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        query_parameters = dict(query_parameters or {})
        page_offset = 0
        collected: list[dict[str, Any]] = []
        while True:
            page_query = {
                **query_parameters,
                "limit": page_size,
                "offset": page_offset,
            }
            page = self.get(
                path,
                page_query,
                success_credit_cost=success_credit_cost_per_page,
            )
            if page.status_code != 200:
                raise SectorsClientError(
                    f"{path} returned {page.status_code}: {page.payload!r}"
                )
            payload = page.payload
            if not isinstance(payload, dict) or "results" not in payload:
                raise SectorsClientError(f"{path} response missing results list.")
            page_rows = payload["results"]
            if not isinstance(page_rows, list):
                raise SectorsClientError(f"{path} results is not a list.")
            collected.extend(page_rows)
            pagination = payload.get("pagination") or {}
            has_next_page = bool(pagination.get("has_next"))
            next_page_offset = pagination.get("next_offset")
            if not has_next_page or next_page_offset is None:
                break
            if next_page_offset == page_offset:
                raise SectorsClientError(f"{path} pagination offset did not advance.")
            page_offset = int(next_page_offset)
        return collected

    def continue_pagination(
        self,
        path: str,
        query_parameters: dict[str, Any],
        first_response: SectorsResponse,
        *,
        success_credit_cost_per_page: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        if first_response.status_code != 200:
            raise SectorsClientError(
                f"{path} returned {first_response.status_code}: {first_response.payload!r}"
            )
        payload = first_response.payload
        if not isinstance(payload, dict) or "results" not in payload:
            raise SectorsClientError(f"{path} response missing results list.")
        collected = list(payload["results"])
        pagination = payload.get("pagination") or {}
        page_offset = pagination.get("next_offset")
        while bool(pagination.get("has_next")) and page_offset is not None:
            page_query = {
                **query_parameters,
                "limit": page_size,
                "offset": int(page_offset),
            }
            page = self.get(
                path,
                page_query,
                success_credit_cost=success_credit_cost_per_page,
            )
            if page.status_code != 200:
                raise SectorsClientError(
                    f"{path} returned {page.status_code}: {page.payload!r}"
                )
            page_payload = page.payload
            collected.extend(page_payload["results"])
            pagination = page_payload.get("pagination") or {}
            next_page_offset = pagination.get("next_offset")
            if next_page_offset == page_offset:
                raise SectorsClientError(f"{path} pagination offset did not advance.")
            page_offset = next_page_offset
        return collected

    def _get_with_retry(
        self,
        path: str,
        query_parameters: dict[str, Any],
    ) -> httpx.Response:
        if not settings.sectors_api_key:
            raise SectorsAuthError("SECTORS_API_KEY is missing from .env.")
        url = _build_url(settings.sectors_api_base_url, path)
        headers = {"Authorization": settings.sectors_api_key}
        last_response: httpx.Response | None = None
        for attempt_number in range(1, MAX_ATTEMPTS + 1):
            self._respect_min_interval()
            response = self._http_client.get(
                url,
                params=query_parameters,
                headers=headers,
            )
            last_response = response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            retry_after_seconds = _retry_after_seconds(response, attempt_number)
            logger.warning(
                "retryable status=%s path=%s attempt=%s sleeping=%.1fs",
                response.status_code,
                path,
                attempt_number,
                retry_after_seconds,
            )
            time.sleep(retry_after_seconds)
        assert last_response is not None
        return last_response

    def _respect_min_interval(self) -> None:
        elapsed = time.monotonic() - self._last_live_request_at
        wait_seconds = settings.sectors_min_interval_seconds - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self._last_live_request_at = time.monotonic()


def _build_url(base_url: str, path: str) -> str:
    host = base_url.rstrip("/")
    if path.startswith("/v2/"):
        host = host.removesuffix("/v2")
        return host + path
    return urljoin(host + "/", path.lstrip("/"))


def _normalize_query(query_parameters: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in sorted(query_parameters):
        value = query_parameters[key]
        if value is None:
            continue
        if isinstance(value, bool):
            normalized[key] = "true" if value else "false"
        else:
            normalized[key] = value
    return normalized


def _cache_key(method: str, path: str, query_parameters: dict[str, Any]) -> str:
    encoded = json.dumps(
        {"method": method, "path": path, "query": query_parameters},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_cache(cache_key: str) -> dict | None:
    row = get_database().execute(
        "SELECT status_code, response_json FROM http_cache WHERE cache_key = ?",
        (cache_key,),
    ).fetchone()
    return dict(row) if row is not None else None


def _write_cache(
    *,
    cache_key: str,
    path: str,
    query_parameters: dict[str, Any],
    status_code: int,
    payload: Any,
    credits_charged: int,
) -> None:
    get_database().execute(
        """
        INSERT OR REPLACE INTO http_cache (
            cache_key, method, path, query_json, status_code,
            response_json, credits_charged, fetched_at
        ) VALUES (?, 'GET', ?, ?, ?, ?, ?, ?)
        """,
        (
            cache_key,
            path,
            json.dumps(query_parameters, sort_keys=True),
            status_code,
            json.dumps(payload),
            credits_charged,
            utc_now_iso(),
        ),
    )


def _retry_after_seconds(response: httpx.Response, attempt_number: int) -> float:
    retry_after_header = response.headers.get("Retry-After")
    if retry_after_header:
        try:
            return max(float(retry_after_header), 0.5)
        except ValueError:
            pass
    return min(2 ** (attempt_number - 1), 16)
