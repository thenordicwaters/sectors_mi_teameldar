export type ViewTab = 'overview' | 'valuation' | 'flow';

export type SignalKind =
  | 'mover'
  | 'week_52_high'
  | 'foreign_accumulation'
  | 'insider_buying';

export type AnomalyKind = 'volume_zscore' | 'foreign_flow_zscore';

export type ScoreBreakdown = {
  overall: number;
  value: number;
  quality: number;
  momentum: number;
  flow: number;
  rank: number | null;
};

export type SignalBadge = {
  kind: SignalKind;
  label: string;
  reason: string;
};

export type Pagination = {
  total_count: number;
  showing: number;
  limit: number;
  offset: number;
  has_next: boolean;
  has_previous: boolean;
  next_offset: number | null;
  previous_offset: number | null;
};

export type ScreenerRow = {
  symbol: string;
  company_name: string;
  sector: string | null;
  sub_sector: string | null;
  last_close_price: number | null;
  daily_close_change: number | null;
  market_cap: number | null;
  pe_ttm: number | null;
  pb_mrq: number | null;
  ps_ttm: number | null;
  roe_ttm: number | null;
  yield_ttm: number | null;
  net_foreign_inflow: number | null;
  volume: number | null;
  score: ScoreBreakdown;
  signals: SignalBadge[];
  anomaly: boolean;
};

export type ScreenerResponse = {
  results: ScreenerRow[];
  pagination: Pagination;
  view: ViewTab;
  disclaimer: string;
};

export type StockDetail = {
  symbol: string;
  company_name: string;
  overview: Record<string, unknown>;
  valuation: Record<string, unknown>;
  flow: Record<string, unknown>;
  score: ScoreBreakdown;
  signals: SignalBadge[];
  anomaly: boolean;
  disclaimer: string;
};

export type CompareResponse = {
  symbols: string[];
  company_names: Record<string, string>;
  metrics: { metric: string; values: Record<string, number | string | null> }[];
  disclaimer: string;
};

export type UnusualActivityResponse = {
  results: {
    symbol: string;
    company_name: string;
    kind: AnomalyKind;
    z_score: number;
    as_of: string;
    reason: string;
  }[];
  pagination: Pagination;
  disclaimer: string;
};
