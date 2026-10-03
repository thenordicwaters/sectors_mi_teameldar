export type ViewTab = 'overview' | 'valuation' | 'flow';

export type SignalKind =
  | 'mover'
  | 'fifty_two_week_high'
  | 'foreign_accumulation'
  | 'insider_buying';

export type AnomalyKind = 'volume_standard_score' | 'foreign_flow_standard_score';

export type AnomalyFlag = {
  ticker_symbol: string;
  company_name: string;
  anomaly_kind: AnomalyKind;
  label: string;
  standard_score: number;
  observed_value: number | null;
  baseline_value: number | null;
  threshold: number;
  as_of_date: string;
  reason: string;
};

export type ScoreBreakdown = {
  overall_score: number | null;
  value_score: number | null;
  quality_score: number | null;
  momentum_score: number | null;
  flow_score: number | null;
  universe_rank: number | null;
};

export type SignalBadge = {
  signal_kind: SignalKind;
  label: string;
  reason: string;
};

export type Pagination = {
  total_count: number;
  shown_count: number;
  page_size: number;
  page_offset: number;
  has_next_page: boolean;
  has_previous_page: boolean;
  next_page_offset: number | null;
  previous_page_offset: number | null;
};

export type ScreenerRow = {
  ticker_symbol: string;
  company_name: string;
  sector: string | null;
  sub_sector: string | null;
  last_close_price: number | null;
  daily_close_change: number | null;
  market_capitalization: number | null;
  price_to_earnings_trailing_twelve_months: number | null;
  price_to_book_most_recent_quarter: number | null;
  price_to_sales_trailing_twelve_months: number | null;
  return_on_equity_trailing_twelve_months: number | null;
  dividend_yield_trailing_twelve_months: number | null;
  net_foreign_inflow: number | null;
  volume: number | null;
  score: ScoreBreakdown;
  signals: SignalBadge[];
  has_anomaly: boolean;
  anomalies: AnomalyFlag[];
};

export type ScreenerResponse = {
  results: ScreenerRow[];
  pagination: Pagination;
  view_tab: ViewTab;
  disclaimer: string;
};

export type CustomScreenerResponse = {
  where_clause: string;
  order_by: string;
  results: ScreenerRow[];
  pagination: Pagination;
  credits_charged: number;
  cache_hit: boolean;
  scored_from_cache: number;
  notes: string[];
  disclaimer: string;
};

export type ScreenerFieldsResponse = {
  operators: string[];
  logic_keywords: string[];
  direct_fields: string[];
  array_fields: string[];
  latest_value_fields: string[];
  yearly_fields: string[];
  quarterly_fields: string[];
  examples: string[];
  max_clause_length: number;
  max_conditions: number;
  credits_per_page: number;
};

export type StockOverview = {
  listing_board: string | null;
  industry: string | null;
  sub_industry: string | null;
  sector: string | null;
  sub_sector: string | null;
  market_capitalization: number | null;
  market_capitalization_rank: number | null;
  last_close_price: number | null;
  daily_close_change: number | null;
  listing_date: string | null;
  tags: string[];
  indices: string[];
};

export type StockValuation = {
  price_to_earnings_trailing_twelve_months: number | null;
  price_to_book_most_recent_quarter: number | null;
  price_to_sales_trailing_twelve_months: number | null;
  forward_price_to_earnings: number | null;
  intrinsic_value: number | null;
};

export type StockFlow = {
  net_foreign_inflow: number | null;
  foreign_buy_value_rupiah: number | null;
  foreign_sell_value_rupiah: number | null;
  as_of_date: string | null;
};

export type StockDetail = {
  ticker_symbol: string;
  company_name: string;
  overview: StockOverview;
  valuation: StockValuation;
  flow: StockFlow;
  score: ScoreBreakdown;
  signals: SignalBadge[];
  has_anomaly: boolean;
  anomalies: AnomalyFlag[];
  disclaimer: string;
};

export type CompareResponse = {
  ticker_symbols: string[];
  company_names: Record<string, string>;
  metrics: { metric_name: string; values_by_ticker: Record<string, number | string | null> }[];
  disclaimer: string;
};

export type SessionStatus = 'today' | 'weekend' | 'earlier' | 'unavailable';

export type IntradayPoint = {
  time: string;
  price: number;
};

export type StockQuote = {
  ticker_symbol: string;
  close: number | null;
  previous_close: number | null;
  change: number | null;
  session_date: string | null;
  session_status: SessionStatus;
  snapshot_close: number | null;
  snapshot_fetched_at: string | null;
  prior_session_date: string | null;
  prior_high: number | null;
  points: IntradayPoint[];
  source: string;
};

export type PriceRange = '1m' | '3m' | '1y' | 'all';

export type HistoryPoint = {
  date: string;
  close: number;
};

export type PriceHistory = {
  symbol: string;
  name: string;
  range: PriceRange;
  as_of_date: string;
  session_date: string | null;
  close: number | null;
  previous_close: number | null;
  change: number | null;
  points: HistoryPoint[];
  source: string;
};

export type IndexSession = {
  symbol: string;
  name: string;
  session_date: string | null;
  session_status: SessionStatus;
  last_price: number | null;
  previous_close: number | null;
  change: number | null;
  prior_session_date: string | null;
  prior_high: number | null;
  points: IntradayPoint[];
  source: string;
};

export type UnusualActivityResponse = {
  results: AnomalyFlag[];
  pagination: Pagination;
  method_notes: string[];
  disclaimer: string;
};

export type MethodResult = {
  method: string;
  version: string;
  score: number | null;
  breakdown: Record<string, unknown>;
  reasons: string[];
  missing_fields: string[];
  applicable: boolean;
  notes: string[];
};

export type ComponentScores = {
  quality: number | null;
  value: number | null;
  momentum: number | null;
  flow: number | null;
};

export type CompositeResult = {
  symbol: string;
  score: number | null;
  rank: number | null;
  components: ComponentScores;
  methods: Record<string, MethodResult>;
  coverage: number;
  excluded_reason: string | null;
  notes: string[];
  weights_used: Record<string, number>;
};
