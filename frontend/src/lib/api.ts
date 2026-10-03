import type {
  AnomalyFlag,
  CompositeResult,
  IndexSession,
  ScreenerResponse,
  ScreenerRow,
  StockDetail,
  StockQuote,
  UnusualActivityResponse
} from './types';

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
    if (typeof body?.detail?.message === 'string') return body.detail.message;
  } catch {
    // The error body was not JSON.
  }
  return `Request failed (${response.status}).`;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(await errorMessage(response));
  return (await response.json()) as T;
}

export function fetchStock(symbol: string): Promise<StockDetail> {
  return fetchJson(`/api/stocks/${encodeURIComponent(symbol)}`);
}

export function fetchScore(symbol: string): Promise<CompositeResult> {
  return fetchJson(`/api/scores/${encodeURIComponent(symbol)}`);
}

export function fetchQuote(symbol: string): Promise<StockQuote> {
  return fetchJson(`/api/quotes/${encodeURIComponent(symbol)}`);
}

export function fetchIhsg(): Promise<IndexSession> {
  return fetchJson('/api/market/ihsg');
}

let universeRequest: Promise<ScreenerRow[]> | null = null;

export function loadUniverse(): Promise<ScreenerRow[]> {
  if (!universeRequest) {
    universeRequest = fetchUniverse().catch((error: unknown) => {
      universeRequest = null;
      throw error;
    });
  }
  return universeRequest;
}

async function fetchUniverse(): Promise<ScreenerRow[]> {
  const rows: ScreenerRow[] = [];
  let offset = 0;
  let total = Number.POSITIVE_INFINITY;

  while (offset < total) {
    const page = await fetchJson<ScreenerResponse>(
      `/api/screener?sort_by=-overall_score&page_size=200&page_offset=${offset}`
    );
    rows.push(...page.results);
    total = page.pagination.total_count;
    if (page.results.length === 0) break;
    offset += page.results.length;
  }

  return rows;
}

export async function loadUnusual(): Promise<{
  results: AnomalyFlag[];
  method_notes: string[];
  disclaimer: string;
}> {
  const results: AnomalyFlag[] = [];
  let offset = 0;
  let total = Number.POSITIVE_INFINITY;
  let methodNotes: string[] = [];
  let disclaimer = 'Information and analysis only. Not investment advice.';

  while (offset < total) {
    const page = await fetchJson<UnusualActivityResponse>(
      `/api/unusual?page_size=200&page_offset=${offset}`
    );
    results.push(...page.results);
    methodNotes = page.method_notes;
    disclaimer = page.disclaimer;
    total = page.pagination.total_count;
    if (page.results.length === 0) break;
    offset += page.results.length;
  }

  return { results, method_notes: methodNotes, disclaimer };
}
