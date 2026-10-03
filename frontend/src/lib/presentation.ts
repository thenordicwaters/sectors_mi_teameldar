import { formatPercent, formatRupiah, formatScore, formatShares } from './format';
import { text, type Locale, type MessageKey } from './i18n';
import type { AnomalyFlag, MethodResult, ScreenerRow, SignalBadge, SignalKind } from './types';

export const METHOD_ORDER = [
  'piotroski',
  'magic_formula',
  'momentum',
  'foreign_flow',
  'financials_quality'
] as const;

export type MethodKey = (typeof METHOD_ORDER)[number];

export type SortKey =
  | 'overall_score'
  | 'quality_score'
  | 'value_score'
  | 'momentum_score'
  | 'flow_score';

type MethodMeta = {
  title: string;
  source: string;
  sourceDetail: string;
  methodology: string;
};

export const METHOD_META: Record<MethodKey, MethodMeta> = {
  piotroski: {
    title: 'Piotroski',
    source: 'Sectors',
    sourceDetail: 'Sectors financial data',
    methodology:
      'Nine yes-or-no tests against the prior fiscal year. The score is how many pass. At least six tests must be computable. Financials are excluded, and their quality score uses Financial Quality instead.'
  },
  magic_formula: {
    title: 'Magic Formula',
    source: 'Sectors',
    sourceDetail: 'Sectors market and fundamental data',
    methodology:
      'Earnings yield and return on capital are ranked and combined into a percentile where 100 is best. In this cache, earnings yield is 1/P/E and return on capital is ROE. Financials and utilities are excluded. The value pillar then re-ranks the result among sector peers when enough peers exist.'
  },
  momentum: {
    title: 'Momentum',
    source: 'Yahoo Finance',
    sourceDetail: 'Yahoo Finance price history',
    methodology:
      '12-1 momentum is the return from twelve months ago to one month ago, then percentile-ranked across the universe. When that history is missing, the daily close change is ranked as a one-day proxy.'
  },
  foreign_flow: {
    title: 'Foreign Flow',
    source: 'Sectors',
    sourceDetail: 'Sectors foreign-flow data',
    methodology:
      'Net foreign buying divided by foreign turnover, blended with how large that turnover is versus the universe, then percentile-ranked. This is a strength score, separate from the unusual-activity Z-score.'
  },
  financials_quality: {
    title: 'Financial Quality',
    source: 'Sectors',
    sourceDetail: 'Sectors financial data',
    methodology:
      'Used for banks and other financials only. Available metrics are percentile-ranked within financials. Net interest margin and non-performing loans are often missing in this cache, so ROE may be the only input.'
  }
};

export const SIGNAL_METHODOLOGY: Record<SignalKind, string> = {
  mover:
    'Flagged when the absolute daily close change is at least 5%. The change comes from the Sectors universe cache.',
  fifty_two_week_high:
    'Flagged from the Sectors 52-w-high tag, or when the close is within 2% of the 52-week high on the Yahoo Finance price overlay.',
  foreign_accumulation:
    'Flagged when net foreign inflow is at least Rp 1 billion and at least 15% of foreign turnover on the latest cached Sectors foreign-flow day.',
  insider_buying: 'Flagged from a Sectors insider buy filing in the cached filing window.'
};

const FIELD_LABELS: Record<string, string> = {
  return_12m: '12-month return',
  return_1m: '1-month return',
  twelve_minus_one: '12-1 momentum',
  daily_return: 'Daily return',
  source: 'Return used',
  ranked_value: 'Value that was ranked',
  earnings_yield: 'Earnings yield',
  return_on_capital: 'Return on capital',
  earnings_yield_rank: 'Earnings-yield rank',
  return_on_capital_rank: 'Return-on-capital rank',
  combined_rank: 'Combined rank',
  percentile: 'Percentile',
  net_foreign_inflow: 'Net foreign inflow',
  foreign_turnover: 'Foreign turnover',
  net_ratio: 'Net / foreign turnover',
  relative_volume: 'Turnover vs universe median',
  return_on_equity: 'ROE',
  net_interest_margin: 'Net interest margin',
  non_performing_loans: 'Non-performing loans',
  roe_percentile: 'ROE percentile',
  nim_percentile: 'NIM percentile',
  npl_percentile: 'NPL percentile',
  parts_used: 'Metrics used',
  tests_computable: 'Tests computable',
  tests_passed: 'Tests passed',
  f_score: 'F-score'
};

const PERCENT_FIELDS = new Set([
  'return_12m',
  'return_1m',
  'twelve_minus_one',
  'daily_return',
  'net_ratio',
  'earnings_yield',
  'return_on_capital',
  'return_on_equity',
  'net_interest_margin',
  'non_performing_loans',
  'ranked_value'
]);

const RUPIAH_FIELDS = new Set(['net_foreign_inflow', 'foreign_turnover']);

const SOURCE_VALUES: Record<string, string> = {
  twelve_minus_one: '12-month return through 1 month ago',
  daily_return: 'Daily price change'
};

export function signalLabel(kind: SignalKind, locale: Locale): string {
  return text(locale, `signal.${kind}` as MessageKey);
}

export function signalMethodology(kind: SignalKind, locale: Locale): string {
  return text(locale, `signal.${kind}.method` as MessageKey);
}

export function methodTitle(key: MethodKey, locale: Locale): string {
  return text(locale, `method.${key}.title` as MessageKey);
}

export function methodBeginner(key: MethodKey, locale: Locale): string {
  return text(locale, `method.${key}.beginner` as MessageKey);
}

export function methodMethodology(key: MethodKey, locale: Locale): string {
  return text(locale, `method.${key}.methodology` as MessageKey);
}

export function signalPresentation(signal: SignalBadge): { emoji: string; source: string } {
  switch (signal.signal_kind) {
    case 'mover':
      return { emoji: '🚀', source: 'Sectors' };
    case 'fifty_two_week_high':
      return {
        emoji: '📈',
        source: signal.reason.includes('Yahoo') ? 'Yahoo Finance' : 'Sectors'
      };
    case 'foreign_accumulation':
      return { emoji: '💰', source: 'Sectors' };
    case 'insider_buying':
      return { emoji: '🏦', source: 'Sectors' };
  }
}

export function anomalyPresentation(
  flag: AnomalyFlag,
  locale: Locale
): {
  emoji: string;
  source: string;
  zLabel: string;
  label: string;
  reference: string;
  methodology: string;
  reason: string;
} {
  const direction = text(locale, flag.standard_score >= 0 ? 'anomaly.above' : 'anomaly.below');
  if (flag.anomaly_kind === 'volume_standard_score') {
    const high = flag.standard_score >= 0;
    return {
      emoji: '🔥',
      source: 'Yahoo Finance',
      zLabel: text(locale, 'anomaly.z'),
      label: text(locale, high ? 'anomaly.volume.high' : 'anomaly.volume.low'),
      reference: text(locale, high ? 'anomaly.volume.referenceHigh' : 'anomaly.volume.referenceLow'),
      methodology: text(locale, 'anomaly.volume.method'),
      reason: text(locale, 'anomaly.volume.reason', {
        observed: formatShares(flag.observed_value, locale),
        baseline: formatShares(flag.baseline_value, locale),
        z: formatZ(flag.standard_score),
        direction
      })
    };
  }
  const high = flag.standard_score >= 0;
  return {
    emoji: '💰',
    source: 'Sectors + Yahoo Finance',
    zLabel: text(locale, 'anomaly.z'),
    label: text(locale, high ? 'anomaly.flow.high' : 'anomaly.flow.low'),
    reference: text(locale, high ? 'anomaly.flow.referenceHigh' : 'anomaly.flow.referenceLow'),
    methodology: text(locale, 'anomaly.flow.method'),
    reason: text(locale, 'anomaly.flow.reason', {
      multiple: flag.observed_value == null ? '—' : Math.abs(flag.observed_value).toFixed(1),
      z: formatZ(flag.standard_score),
      direction
    })
  };
}

function formatZ(value: number): string {
  return Math.abs(value).toFixed(1);
}

export function methodHeadline(key: string, method: MethodResult | undefined, locale: Locale): string {
  if (!method) return text(locale, 'method.none');
  if (!method.applicable) return text(locale, 'method.notApplied');
  if (method.score == null) return text(locale, 'method.noScore');

  if (key === 'piotroski') {
    return text(locale, 'method.piotroski.headline', { score: Math.round(method.score) });
  }

  if (key === 'momentum') {
    const ranked = method.breakdown.ranked_value;
    const percentile = formatScore(method.score);
    if (method.breakdown.source === 'twelve_minus_one' && typeof ranked === 'number') {
      return text(locale, 'method.momentum.twelve', { ret: formatPercent(ranked), pct: percentile });
    }
    if (method.breakdown.source === 'daily_return' && typeof ranked === 'number') {
      return text(locale, 'method.momentum.daily', { ret: formatPercent(ranked), pct: percentile });
    }
  }

  if (key === 'foreign_flow' && typeof method.breakdown.net_ratio === 'number') {
    return text(locale, 'method.foreign_flow.headline', {
      ratio: formatPercent(method.breakdown.net_ratio),
      pct: formatScore(method.score)
    });
  }

  if (
    key === 'magic_formula' &&
    typeof method.breakdown.earnings_yield === 'number' &&
    typeof method.breakdown.return_on_capital === 'number'
  ) {
    return text(locale, 'method.magic_formula.headline', {
      ey: formatPercent(method.breakdown.earnings_yield),
      roc: formatPercent(method.breakdown.return_on_capital),
      pct: formatScore(method.score)
    });
  }

  return text(locale, 'method.fallback');
}

export function methodScoreText(key: string, method: MethodResult | undefined): string {
  if (!method || !method.applicable || method.score == null) return '—';
  if (key === 'piotroski') return `${Math.round(method.score)}/9`;
  return formatScore(method.score);
}

export function methodSource(key: string, method: MethodResult | undefined): string {
  if (key === 'momentum' && method) {
    if (method.breakdown.source === 'daily_return') return 'Sectors';
    if (method.notes.some((note) => note.includes('Yahoo'))) return 'Yahoo Finance';
    return 'Sectors';
  }
  if (key in METHOD_META) return METHOD_META[key as MethodKey].source;
  return 'Sectors';
}

export function methodSourceDetail(key: string, method: MethodResult | undefined): string {
  if (key === 'momentum' && method?.breakdown.source === 'daily_return') {
    return 'Sectors daily close change';
  }
  if (key === 'momentum' && methodSource(key, method) === 'Yahoo Finance') {
    return 'Yahoo Finance price history';
  }
  if (key in METHOD_META) return METHOD_META[key as MethodKey].sourceDetail;
  return 'Sectors';
}

export function primaryAnomaly(anomalies: AnomalyFlag[]): AnomalyFlag | null {
  if (anomalies.length === 0) return null;
  return [...anomalies].sort(
    (left, right) => Math.abs(right.standard_score) - Math.abs(left.standard_score)
  )[0];
}

export function pillarValue(row: ScreenerRow, sort: SortKey): number | null {
  return row.score[sort];
}

export type PiotroskiTest = { key: string; label: string; result: string };

export function piotroskiTests(breakdown: Record<string, unknown>): PiotroskiTest[] {
  const tests: PiotroskiTest[] = [];
  for (const value of Object.values(breakdown)) {
    if (value && typeof value === 'object' && 'label' in value && 'result' in value) {
      const record = value as { key?: unknown; label: unknown; result: unknown };
      const key = typeof record.key === 'string' ? record.key : '';
      tests.push({ key, label: String(record.label), result: String(record.result) });
    }
  }
  return tests;
}

export function piotroskiTestLabel(test: PiotroskiTest, locale: Locale): string {
  const message = FIELD_MESSAGE_KEYS[test.key];
  if (message) return text(locale, message);
  return test.label;
}

export function piotroskiResultLabel(result: string, locale: Locale): string {
  if (result === 'pass' || result === 'fail' || result === 'unknown') {
    return text(locale, `piotroski.${result}`);
  }
  return result;
}

const FIELD_MESSAGE_KEYS: Record<string, MessageKey> = {
  roa_positive: 'piotroski.roa_positive',
  cfo_positive: 'piotroski.cfo_positive',
  roa_increased: 'piotroski.roa_increased',
  accrual: 'piotroski.accrual',
  leverage_decreased: 'piotroski.leverage_decreased',
  current_ratio_increased: 'piotroski.current_ratio_increased',
  no_new_shares: 'piotroski.no_new_shares',
  gross_margin_increased: 'piotroski.gross_margin_increased',
  asset_turnover_increased: 'piotroski.asset_turnover_increased'
};

export function evidenceLines(
  breakdown: Record<string, unknown>,
  locale: Locale
): { label: string; value: string }[] {
  const lines: { label: string; value: string }[] = [];
  for (const [key, raw] of Object.entries(breakdown)) {
    if (raw !== null && typeof raw === 'object') continue;
    if (!FIELD_LABELS[key]) continue;
    lines.push({ label: text(locale, `field.${key}` as MessageKey), value: formatEvidence(key, raw, locale) });
  }
  return lines;
}

function formatEvidence(key: string, raw: unknown, locale: Locale): string {
  if (raw == null || raw === '') return locale === 'id' ? 'Kosong' : 'Missing';
  if (key === 'source' && typeof raw === 'string') {
    if (raw === 'twelve_minus_one' || raw === 'daily_return') {
      return text(locale, `source.${raw}`);
    }
    return SOURCE_VALUES[raw] ?? raw;
  }
  if (typeof raw === 'number') {
    if (Number.isNaN(raw)) return 'Missing';
    if (PERCENT_FIELDS.has(key)) return formatPercent(raw);
    if (RUPIAH_FIELDS.has(key)) return formatRupiah(raw);
    if (key.endsWith('percentile') || key === 'percentile') return formatScore(raw);
    if (
      key.endsWith('_rank') ||
      key === 'combined_rank' ||
      key === 'parts_used' ||
      key === 'tests_computable' ||
      key === 'tests_passed' ||
      key === 'f_score'
    ) {
      return Number.isInteger(raw) ? String(raw) : raw.toFixed(1);
    }
    return raw.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
  return String(raw);
}
