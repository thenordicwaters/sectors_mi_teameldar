import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.common import Pagination, SignalKind, ViewTab
from app.models.screener import (
    CustomScreenerResponse,
    ScreenerFieldsResponse,
    ScreenerQuery,
    ScreenerResponse,
)
from app.sectors.client import (
    SectorsAuthError,
    SectorsClient,
    SectorsCreditBudgetError,
)
from app.sectors.paths import (
    COMPANIES_SCREENER_CREDITS_PER_PAGE,
    COMPANIES_SCREENER_MAX_PAGE_SIZE,
    COMPANIES_SCREENER_PATH,
)
from app.sectors.repository import (
    get_screener_row,
    list_screener_page,
    screener_row_from_sectors_payload,
)
from app.sectors.where_clause import (
    ARRAY_FIELDS,
    DIRECT_FIELDS,
    EXAMPLE_CLAUSES,
    LATEST_VALUE_FIELDS,
    LIST_OBJECT_FIELDS,
    LOGIC_KEYWORDS,
    MAX_CLAUSE_LENGTH,
    MAX_CONDITIONS,
    OPERATORS,
    QUARTERLY_FIELDS,
    YEARLY_FIELDS,
    WhereClauseError,
    validate_order_by,
    validate_where_clause,
)

logger = logging.getLogger("sectors.screener")

router = APIRouter(prefix="/api/screener", tags=["screener"])

@router.get("", response_model=ScreenerResponse)
def list_screener_results(
    filter_clause: str | None = None,
    sort_by: str = "-overall_score",
    view_tab: ViewTab = ViewTab.overview,
    signal_filter: SignalKind | None = None,
    anomaly_only: bool = False,
    page_size: int = Query(default=20, ge=1, le=200),
    page_offset: int = Query(default=0, ge=0),
) -> ScreenerResponse:
    """Serve the cached snapshot only. Does not call Sectors (0 credits)."""
    if filter_clause:
        raise HTTPException(
            status_code=400,
            detail=(
                "This endpoint only serves the cached snapshot. Send a where clause to "
                "GET /api/screener/custom, which calls Sectors at 1 credit per page."
            ),
        )
    ScreenerQuery(
        filter_clause=filter_clause,
        sort_by=sort_by,
        view_tab=view_tab,
        signal_filter=None if signal_filter is None else signal_filter.value,
        page_size=page_size,
        page_offset=page_offset,
    )
    return list_screener_page(
        sort_by=sort_by,
        page_size=page_size,
        page_offset=page_offset,
        view_tab=view_tab,
        signal_filter=None if signal_filter is None else signal_filter.value,
        anomaly_only=anomaly_only,
    )


@router.get("/custom/fields", response_model=ScreenerFieldsResponse)
def list_custom_query_fields() -> ScreenerFieldsResponse:
    """What the custom-logic box accepts. Does not call Sectors (0 credits)."""
    return ScreenerFieldsResponse(
        operators=list(OPERATORS),
        logic_keywords=list(LOGIC_KEYWORDS),
        direct_fields=sorted(DIRECT_FIELDS),
        array_fields=sorted(ARRAY_FIELDS),
        latest_value_fields=sorted(LATEST_VALUE_FIELDS | LIST_OBJECT_FIELDS),
        yearly_fields=sorted(YEARLY_FIELDS),
        quarterly_fields=sorted(QUARTERLY_FIELDS),
        examples=list(EXAMPLE_CLAUSES),
        max_clause_length=MAX_CLAUSE_LENGTH,
        max_conditions=MAX_CONDITIONS,
        credits_per_page=COMPANIES_SCREENER_CREDITS_PER_PAGE,
    )


@router.get("/custom", response_model=CustomScreenerResponse)
def run_custom_screen(
    where: str = Query(description="Sectors structured where clause. 1 credit per page."),
    order_by: str = "-market_cap",
    page_size: int = Query(default=50, ge=1, le=COMPANIES_SCREENER_MAX_PAGE_SIZE),
    page_offset: int = Query(default=0, ge=0),
    dry_run: bool = Query(
        default=False,
        description="Validate and report the planned cost without calling Sectors.",
    ),
) -> CustomScreenerResponse:
    """Validate a where clause, then screen live on Sectors.

    One page per request: 1 credit, or 0 when the same query is already cached.
    A clause we reject never reaches Sectors and costs nothing.
    """
    try:
        validated = validate_where_clause(where)
        validated_order_by = validate_order_by(order_by)
    except WhereClauseError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": error.message,
                "suggestions": error.suggestions,
                "credits_charged": 0,
                "help": "GET /api/screener/custom/fields lists every accepted field.",
            },
        ) from error

    query_parameters = {
        "where": validated.clause,
        "order_by": validated_order_by,
        "include_query_values": True,
    }
    if dry_run:
        return CustomScreenerResponse(
            where_clause=validated.clause,
            order_by=validated_order_by,
            results=[],
            pagination=_empty_pagination(page_size, page_offset),
            credits_charged=0,
            cache_hit=False,
            scored_from_cache=0,
            notes=[
                "Dry run: nothing was sent to Sectors.",
                f"Clause is valid and references {', '.join(validated.fields)}.",
                f"Running it would cost {COMPANIES_SCREENER_CREDITS_PER_PAGE} credit "
                "for this page, or 0 if the same query is already cached.",
            ],
        )

    client = SectorsClient(max_credits_this_run=COMPANIES_SCREENER_CREDITS_PER_PAGE)
    try:
        response = client.get(
            COMPANIES_SCREENER_PATH,
            {**query_parameters, "limit": page_size, "offset": page_offset},
            success_credit_cost=COMPANIES_SCREENER_CREDITS_PER_PAGE,
        )
    except SectorsAuthError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SectorsCreditBudgetError as error:
        raise HTTPException(status_code=402, detail=str(error)) from error
    finally:
        client.close()

    if response.status_code == 400:
        raise HTTPException(
            status_code=422,
            detail={
                "message": _sectors_message(response.payload),
                "source": "Sectors rejected the clause. A structured 400 is free.",
                "credits_charged": response.credits_charged,
            },
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Sectors returned {response.status_code} for this query.",
        )

    payload = response.payload if isinstance(response.payload, dict) else {}
    sectors_rows = payload.get("results") or []
    rows = []
    scored_from_cache = 0
    for sectors_row in sectors_rows:
        symbol = sectors_row.get("symbol")
        cached = get_screener_row(str(symbol)) if symbol else None
        if cached is not None:
            rows.append(cached)
            scored_from_cache += 1
            continue
        live_row = screener_row_from_sectors_payload(sectors_row)
        if live_row is not None:
            rows.append(live_row)

    notes = [
        f"Sectors matched {len(sectors_rows)} companies on this page for "
        f"{response.credits_charged} credit(s)."
    ]
    if scored_from_cache < len(rows):
        notes.append(
            f"{len(rows) - scored_from_cache} match(es) are outside the snapshot, so "
            "their Score, Signals and Anomaly flags are empty until the next snapshot."
        )
    if response.cache_hit:
        notes.append("Served from the local HTTP cache: 0 credits.")
    return CustomScreenerResponse(
        where_clause=validated.clause,
        order_by=validated_order_by,
        results=rows,
        pagination=_pagination_from_sectors(
            payload.get("pagination") or {}, len(rows), page_size, page_offset
        ),
        credits_charged=response.credits_charged,
        cache_hit=response.cache_hit,
        scored_from_cache=scored_from_cache,
        notes=notes,
    )


def _pagination_from_sectors(
    sectors_pagination: dict,
    shown_count: int,
    page_size: int,
    page_offset: int,
) -> Pagination:
    total_count = sectors_pagination.get("total_count")
    has_next_page = bool(sectors_pagination.get("has_next"))
    next_page_offset = sectors_pagination.get("next_offset")
    return Pagination(
        total_count=int(total_count) if total_count is not None else shown_count,
        shown_count=shown_count,
        page_size=page_size,
        page_offset=page_offset,
        has_next_page=has_next_page,
        has_previous_page=page_offset > 0,
        next_page_offset=int(next_page_offset) if has_next_page and next_page_offset is not None else None,
        previous_page_offset=None if page_offset == 0 else max(page_offset - page_size, 0),
    )


def _empty_pagination(page_size: int, page_offset: int) -> Pagination:
    return Pagination(
        total_count=0,
        shown_count=0,
        page_size=page_size,
        page_offset=page_offset,
        has_next_page=False,
        has_previous_page=page_offset > 0,
        next_page_offset=None,
        previous_page_offset=None if page_offset == 0 else max(page_offset - page_size, 0),
    )


def _sectors_message(payload) -> str:
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("error") or payload)
    return str(payload)
