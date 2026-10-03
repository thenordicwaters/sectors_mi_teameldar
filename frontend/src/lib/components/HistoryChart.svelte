<script lang="ts">
  import { browser } from '$app/environment';
  import Notice from './Notice.svelte';
  import PriceChart from './PriceChart.svelte';
  import SourceTag from './SourceTag.svelte';
  import { fetchPriceHistory } from '$lib/api';
  import { formatIndex, formatPercent, formatPrice, formatSessionDate } from '$lib/format';
  import { locale, text } from '$lib/i18n';
  import type { PriceHistory, PriceRange } from '$lib/types';

  let {
    resource,
    title,
    kicker = '',
    priceKind = 'index'
  }: {
    resource: string;
    title: string;
    kicker?: string;
    priceKind?: 'price' | 'index';
  } = $props();

  const ranges = [
    ['1m', '1M'],
    ['3m', '3M'],
    ['1y', '1Y'],
    ['all', 'ALL']
  ] as const;

  let range = $state<PriceRange>('3m');
  let history = $state<PriceHistory | null>(null);
  let status = $state<'loading' | 'ready' | 'error'>('loading');
  let errorDetail = $state('');
  let seenResource = '';

  const up = $derived((history?.change ?? 0) >= 0);

  $effect(() => {
    if (!browser) return;
    const requestedResource = resource;
    const requestedRange = range;
    if (requestedResource !== seenResource) {
      history = null;
      seenResource = requestedResource;
    }
    let cancelled = false;
    status = 'loading';
    errorDetail = '';
    fetchPriceHistory(requestedResource, requestedRange)
      .then((loaded) => {
        if (cancelled || loaded.range !== requestedRange) return;
        history = loaded;
        status = 'ready';
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        history = null;
        errorDetail = error instanceof Error ? error.message : text($locale, 'chart.error');
        status = 'error';
      });
    return () => {
      cancelled = true;
    };
  });

  function shownPrice(current: PriceHistory): string {
    return priceKind === 'index' ? formatIndex(current.close, $locale) : formatPrice(current.close, $locale);
  }
</script>

<section class="mt-8 rounded-2xl border border-line bg-white p-4 sm:p-5">
  <div class="flex items-start justify-between gap-4">
    <div>
      {#if kicker}
        <p class="text-xs font-medium uppercase tracking-[0.16em] text-forest">{kicker}</p>
      {/if}
      <h2 class="mt-1 font-serif text-3xl">{title}</h2>
    </div>
    <SourceTag label={history?.source ?? text($locale, 'chart.sectors')} />
  </div>

  {#if status === 'loading' && !history}
    <p class="mt-4 text-sm text-muted">{text($locale, 'chart.loading')}</p>
  {:else if status === 'error' || !history}
    <div class="mt-4">
      <Notice title={text($locale, 'chart.error')} detail={errorDetail} />
    </div>
  {:else}
    <p class="numeral mt-3 font-serif text-5xl leading-none {up ? 'text-forest' : 'text-clay'}">
      {shownPrice(history)}
    </p>
    <p class="mt-2 text-sm {up ? 'text-forest' : 'text-clay'}">{formatPercent(history.change)}</p>
    {#if history.session_date}
      <p class="mt-2 text-sm font-medium text-ink">
        {text($locale, 'chart.session', { date: formatSessionDate(history.session_date, $locale) })}
      </p>
    {/if}
    <div
      class="mt-4 inline-flex flex-wrap rounded-full border border-line bg-sand/50 p-0.5"
      role="group"
      aria-label={text($locale, 'chart.rangeLabel')}
    >
      {#each ranges as [option, label]}
        <button
          class={range === option
            ? 'rounded-full bg-ink px-3 py-1 text-xs font-semibold text-paper'
            : 'rounded-full px-3 py-1 text-xs font-semibold text-muted hover:text-ink'}
          type="button"
          aria-pressed={range === option}
          onclick={() => (range = option)}
        >
          {label}
        </button>
      {/each}
    </div>
    {#if history.points.length > 0}
      <div class="mt-3 {status === 'loading' ? 'opacity-60' : ''}">
        <PriceChart points={history.points} {priceKind} {up} />
      </div>
    {:else}
      <p class="mt-3 text-sm text-muted">{text($locale, 'chart.emptyHistory')}</p>
    {/if}
  {/if}
</section>
