export type ViewTab = 'overview' | 'valuation' | 'flow';

export type SignalKind =
  | 'mover'
  | 'fifty_two_week_high'
  | 'foreign_accumulation'
  | 'insider_buying';

export type AnomalyKind = 'volume_standard_score' | 'foreign_flow_standard_score';

export type ScoreBreakdown = {
  overall_score: number;
  value_score: number;
  quality_score: number;
  momentum_score: number;
  flow_score: number;
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
};

export type ScreenerResponse = {
  results: ScreenerRow[];
  pagination: Pagination;
  view_tab: ViewTab;
  disclaimer: string;
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
  disclaimer: string;
};

export type CompareResponse = {
  ticker_symbols: string[];
  company_names: Record<string, string>;
  metrics: { metric_name: string; values_by_ticker: Record<string, number | string | null> }[];
  disclaimer: string;
};

export type UnusualActivityResponse = {
  results: {
    ticker_symbol: string;
    company_name: string;
    anomaly_kind: AnomalyKind;
    standard_score: number;
    as_of_date: string;
    reason: string;
  }[];
  pagination: Pagination;
  disclaimer: string;
};
