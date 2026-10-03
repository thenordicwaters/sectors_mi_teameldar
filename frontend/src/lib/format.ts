export function displaySymbol(ticker: string): string {
  return ticker.trim().toUpperCase().replace(/\.JK$/, '');
}

export function formatScore(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return Math.round(value).toString();
}

export function formatZScore(value: number): string {
  return value.toFixed(1);
}

export function formatPercent(decimal: number | null | undefined): string {
  if (decimal == null || Number.isNaN(decimal)) return '—';
  const percent = decimal * 100;
  const sign = percent > 0 ? '+' : '';
  return `${sign}${percent.toFixed(1)}%`;
}

export function formatRupiah(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  const absolute = Math.abs(value);
  const sign = value < 0 ? '−' : '';
  if (absolute >= 1_000_000_000_000) return `${sign}Rp ${(absolute / 1_000_000_000_000).toFixed(2)}T`;
  if (absolute >= 1_000_000_000) return `${sign}Rp ${(absolute / 1_000_000_000).toFixed(1)}B`;
  if (absolute >= 1_000_000) return `${sign}Rp ${(absolute / 1_000_000).toFixed(1)}M`;
  return `${sign}Rp ${Math.round(absolute).toLocaleString('en-US')}`;
}

export function formatShares(value: number | null | undefined, locale: 'en' | 'id' = 'en'): string {
  if (value == null || Number.isNaN(value)) return '—';
  const absolute = Math.abs(value);
  const unit = locale === 'id' ? 'lembar' : 'shares';
  const numberLocale = locale === 'id' ? 'id-ID' : 'en-US';
  if (absolute >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toLocaleString(numberLocale, { maximumFractionDigits: 1 })} ${locale === 'id' ? 'miliar' : 'B'} ${unit}`;
  }
  if (absolute >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString(numberLocale, { maximumFractionDigits: 1 })} ${locale === 'id' ? 'juta' : 'M'} ${unit}`;
  }
  if (absolute >= 1_000) {
    return `${(value / 1_000).toLocaleString(numberLocale, { maximumFractionDigits: 1 })} ${locale === 'id' ? 'ribu' : 'k'} ${unit}`;
  }
  return `${Math.round(value).toLocaleString(numberLocale)} ${unit}`;
}

export function formatSessionDate(value: string | null | undefined, locale: 'en' | 'id'): string {
  if (!value) return '—';
  const datePart = value.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(datePart)) return value;
  const [year, month, day] = datePart.split('-').map(Number);
  return new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC'
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function formatAsOfRange(
  start: string | null | undefined,
  end: string | null | undefined,
  locale: 'en' | 'id'
): string {
  const left = formatSessionDate(start, locale);
  const right = formatSessionDate(end, locale);
  if (left === '—') return right;
  if (right === '—' || left === right) return left;
  return `${left} – ${right}`;
}

export function formatPrice(value: number | null | undefined, locale: 'en' | 'id'): string {
  if (value == null || Number.isNaN(value)) return '—';
  const digits = Number.isInteger(value) ? 0 : 2;
  const formatted = value.toLocaleString(locale === 'id' ? 'id-ID' : 'en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
  return `Rp ${formatted}`;
}

export function formatIndex(value: number | null | undefined, locale: 'en' | 'id'): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toLocaleString(locale === 'id' ? 'id-ID' : 'en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

export function formatClock(value: string, locale: 'en' | 'id'): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'Asia/Jakarta'
  }).format(parsed);
}

export function uniqueSorted(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort((left, right) =>
    left.localeCompare(right)
  );
}
