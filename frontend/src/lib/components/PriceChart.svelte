<script lang="ts">
  import { formatIndex, formatPrice } from '$lib/format';
  import { locale } from '$lib/i18n';
  import type { HistoryPoint } from '$lib/types';

  let {
    points,
    priceKind = 'price',
    up = true
  }: {
    points: HistoryPoint[];
    priceKind?: 'price' | 'index';
    up?: boolean;
  } = $props();

  const chart = $derived.by(() => {
    if (points.length === 0) return null;
    const values = points.map((point) => point.close);
    let min = Math.min(...values);
    let max = Math.max(...values);
    const span = Math.max(max - min, max * 0.01, 1);
    min -= span * 0.08;
    max += span * 0.08;
    const width = 640;
    const height = 220;
    const pad = { left: 8, right: 78, top: 16, bottom: 28 };
    const innerWidth = width - pad.left - pad.right;
    const innerHeight = height - pad.top - pad.bottom;
    const yFor = (price: number) => pad.top + (1 - (price - min) / (max - min)) * innerHeight;
    const xFor = (index: number) =>
      points.length === 1 ? pad.left + innerWidth / 2 : pad.left + (index / (points.length - 1)) * innerWidth;
    const coords = points.map((point, index) => ({
      x: xFor(index),
      y: yFor(point.close),
      date: point.date
    }));
    const line = coords
      .map((coord, index) => `${index === 0 ? 'M' : 'L'}${coord.x.toFixed(1)},${coord.y.toFixed(1)}`)
      .join(' ');
    const baseline = pad.top + innerHeight;
    const area =
      coords.length < 2
        ? ''
        : `${line} L${coords[coords.length - 1].x.toFixed(1)},${baseline} L${coords[0].x.toFixed(1)},${baseline} Z`;
    const tickIndexes = tickPositions(points.length);
    return { width, height, line, area, coords, tickIndexes, pad, min, max };
  });

  function axisPrice(value: number): string {
    return priceKind === 'index' ? formatIndex(value, $locale) : formatPrice(value, $locale);
  }

  function tickLabel(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-').map(Number);
    const stamp = new Date(Date.UTC(year, month - 1, day));
    const longSeries = points.length > 180;
    return new Intl.DateTimeFormat($locale === 'id' ? 'id-ID' : 'en-GB', {
      day: longSeries ? undefined : 'numeric',
      month: 'short',
      year: longSeries || points.length > 40 ? '2-digit' : undefined,
      timeZone: 'UTC'
    }).format(stamp);
  }

  function tickAnchor(index: number, indexes: number[]): 'start' | 'middle' | 'end' {
    if (indexes.length === 1) return 'middle';
    if (index === indexes[0]) return 'start';
    if (index === indexes[indexes.length - 1]) return 'end';
    return 'middle';
  }

  function tickPositions(length: number): number[] {
    if (length <= 1) return [0];
    if (length <= 4) return Array.from({ length }, (_, index) => index);
    const slots = 4;
    return Array.from({ length: slots }, (_, slot) => Math.round((slot / (slots - 1)) * (length - 1)));
  }
</script>

{#if chart}
  <svg viewBox="0 0 {chart.width} {chart.height}" class="h-56 w-full" role="img">
    <line
      x1={chart.pad.left}
      x2={chart.width - chart.pad.right}
      y1={chart.pad.top + (chart.height - chart.pad.top - chart.pad.bottom)}
      y2={chart.pad.top + (chart.height - chart.pad.top - chart.pad.bottom)}
      stroke="#e4dcd0"
    />
    {#if chart.area}
      <path d={chart.area} fill={up ? 'rgba(15, 106, 74, 0.12)' : 'rgba(143, 61, 31, 0.12)'} />
    {/if}
    {#if chart.coords.length > 1}
      <path
        d={chart.line}
        fill="none"
        stroke={up ? '#0f6a4a' : '#8f3d1f'}
        stroke-width="2.5"
        stroke-linejoin="round"
      />
    {/if}
    <circle
      cx={chart.coords[chart.coords.length - 1].x}
      cy={chart.coords[chart.coords.length - 1].y}
      r="4"
      fill={up ? '#0f6a4a' : '#8f3d1f'}
    />
    <text x={chart.width - chart.pad.right + 8} y={chart.pad.top + 4} fill="#6f675e" font-size="12">
      {axisPrice(chart.max)}
    </text>
    <text
      x={chart.width - chart.pad.right + 8}
      y={chart.pad.top + (chart.height - chart.pad.top - chart.pad.bottom)}
      fill="#6f675e"
      font-size="12"
    >
      {axisPrice(chart.min)}
    </text>
    {#each chart.tickIndexes as tick}
      <text
        x={chart.coords[tick].x}
        y={chart.height - 6}
        text-anchor={tickAnchor(tick, chart.tickIndexes)}
        fill="#6f675e"
        font-size="12"
      >
        {tickLabel(chart.coords[tick].date)}
      </text>
    {/each}
  </svg>
{/if}
