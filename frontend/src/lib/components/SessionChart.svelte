<script lang="ts">
  import { formatClock, formatIndex, formatPrice } from '$lib/format';
  import { locale } from '$lib/i18n';
  import type { IntradayPoint } from '$lib/types';

  let {
    points,
    referencePrice = null,
    priceKind = 'price'
  }: {
    points: IntradayPoint[];
    referencePrice?: number | null;
    priceKind?: 'price' | 'index';
  } = $props();

  const chart = $derived.by(() => {
    if (points.length < 2) return null;
    const values = points.map((point) => point.price);
    if (referencePrice != null) values.push(referencePrice);
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const width = 640;
    const height = 220;
    const pad = { left: 8, right: 72, top: 16, bottom: 28 };
    const innerWidth = width - pad.left - pad.right;
    const innerHeight = height - pad.top - pad.bottom;
    const yFor = (price: number) => pad.top + (1 - (price - min) / (max - min)) * innerHeight;
    const coords = points.map((point, index) => ({
      x: pad.left + (index / (points.length - 1)) * innerWidth,
      y: yFor(point.price),
      time: point.time
    }));
    const line = coords
      .map((coord, index) => `${index === 0 ? 'M' : 'L'}${coord.x.toFixed(1)},${coord.y.toFixed(1)}`)
      .join(' ');
    const baseline = pad.top + innerHeight;
    const area = `${line} L${coords[coords.length - 1].x.toFixed(1)},${baseline} L${coords[0].x.toFixed(1)},${baseline} Z`;
    const ticks = [0, Math.floor((points.length - 1) / 2), points.length - 1];
    return {
      width,
      height,
      line,
      area,
      coords,
      ticks,
      pad,
      min,
      max,
      referenceY: referencePrice == null ? null : yFor(referencePrice)
    };
  });

  function axisPrice(value: number): string {
    return priceKind === 'index' ? formatIndex(value, $locale) : formatPrice(value, $locale);
  }
</script>

{#if chart}
  <svg
    viewBox="0 0 {chart.width} {chart.height}"
    class="h-56 w-full"
    role="img"
  >
    <line
      x1={chart.pad.left}
      x2={chart.width - chart.pad.right}
      y1={chart.pad.top + (chart.height - chart.pad.top - chart.pad.bottom)}
      y2={chart.pad.top + (chart.height - chart.pad.top - chart.pad.bottom)}
      stroke="#e4dcd0"
    />
    {#if chart.referenceY != null}
      <line
        x1={chart.pad.left}
        x2={chart.width - chart.pad.right}
        y1={chart.referenceY}
        y2={chart.referenceY}
        stroke="#8f3d1f"
        stroke-dasharray="5 4"
        stroke-width="1.5"
      />
    {/if}
    <path d={chart.area} fill="rgba(15, 106, 74, 0.12)" />
    <path d={chart.line} fill="none" stroke="#0f6a4a" stroke-width="2.5" stroke-linejoin="round" />
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
    {#each chart.ticks as tick}
      <text x={chart.coords[tick].x} y={chart.height - 6} text-anchor="middle" fill="#6f675e" font-size="12">
        {formatClock(chart.coords[tick].time, $locale)}
      </text>
    {/each}
  </svg>
{/if}
