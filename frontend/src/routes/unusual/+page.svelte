<script lang="ts">
  import { onMount } from 'svelte';
  import Disclosure from '$lib/components/Disclosure.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import SourceTag from '$lib/components/SourceTag.svelte';
  import { loadUniverse, loadUnusual } from '$lib/api';
  import { displaySymbol, formatAsOfRange, formatShares, formatZScore, uniqueSorted } from '$lib/format';
  import { locale, text } from '$lib/i18n';
  import { anomalyPresentation } from '$lib/presentation';
  import type { AnomalyFlag, AnomalyKind, ScreenerRow } from '$lib/types';

  let flags = $state<AnomalyFlag[]>([]);
  let rows = $state<ScreenerRow[]>([]);
  let status = $state<'loading' | 'ready' | 'error'>('loading');
  let errorDetail = $state('');
  let sector = $state('All');
  let subsector = $state('All');
  let kind = $state<'All' | AnomalyKind>('All');
  let visibleCount = $state(12);

  const rowBySymbol = $derived(new Map(rows.map((row) => [row.ticker_symbol, row])));
  const sectors = $derived(uniqueSorted(rows.map((row) => row.sector)));
  const subsectors = $derived(
    uniqueSorted(
      rows
        .filter((row) => sector === 'All' || row.sector === sector)
        .map((row) => row.sub_sector)
    )
  );

  const filtered = $derived(
    flags.filter((flag) => {
      const row = rowBySymbol.get(flag.ticker_symbol);
      if (sector !== 'All' && row?.sector !== sector) return false;
      if (subsector !== 'All' && row?.sub_sector !== subsector) return false;
      if (kind !== 'All' && flag.anomaly_kind !== kind) return false;
      return true;
    })
  );

  const visibleFlags = $derived(filtered.slice(0, visibleCount));
  const dateSpan = $derived.by(() => {
    const dates = filtered.map((flag) => flag.as_of_date).filter((value) => value).sort();
    if (dates.length === 0) return null;
    return { start: dates[0], end: dates[dates.length - 1] };
  });

  $effect(() => {
    sector;
    subsector;
    kind;
    visibleCount = 12;
  });

  $effect(() => {
    if (subsector !== 'All' && !subsectors.includes(subsector)) subsector = 'All';
  });

  onMount(() => {
    Promise.all([loadUnusual(), loadUniverse()])
      .then(([unusual, universe]) => {
        flags = unusual.results;
        rows = universe;
        status = 'ready';
      })
      .catch((error: unknown) => {
        errorDetail = error instanceof Error ? error.message : 'Unusual activity could not be loaded.';
        status = 'error';
      });
  });

  function observedLabel(flag: AnomalyFlag): string {
    if (flag.anomaly_kind === 'volume_standard_score') return text($locale, 'unusual.latestVolume');
    return text($locale, 'unusual.flowVsValue');
  }

  function baselineLabel(flag: AnomalyFlag): string {
    if (flag.anomaly_kind === 'volume_standard_score') return text($locale, 'unusual.ownAverage');
    return text($locale, 'unusual.sameDayMedian');
  }

  function formatObserved(flag: AnomalyFlag): string {
    if (flag.observed_value == null) return '—';
    if (flag.anomaly_kind === 'volume_standard_score') return formatShares(flag.observed_value, $locale);
    return `${flag.observed_value.toFixed(1)}x`;
  }

  function formatBaseline(flag: AnomalyFlag): string {
    if (flag.baseline_value == null) return '—';
    if (flag.anomaly_kind === 'volume_standard_score') return formatShares(flag.baseline_value, $locale);
    return `${flag.baseline_value.toFixed(2)}x`;
  }
</script>

<section class="max-w-3xl">
  <p class="text-sm font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'unusual.kicker')}</p>
  <h1 class="mt-2 font-serif text-4xl leading-tight sm:text-5xl">{text($locale, 'unusual.title')}</h1>
  <p class="mt-4 max-w-xl text-base leading-7 text-muted">{text($locale, 'unusual.intro')}</p>
</section>

<div class="mt-8 grid gap-3 sm:grid-cols-3">
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'unusual.sector')}</span>
    <select class="field mt-2" bind:value={sector}>
      <option value="All">{text($locale, 'unusual.all')}</option>
      {#each sectors as sectorName}
        <option value={sectorName}>{sectorName}</option>
      {/each}
    </select>
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'unusual.subsector')}</span>
    <select class="field mt-2" bind:value={subsector}>
      <option value="All">{text($locale, 'unusual.all')}</option>
      {#each subsectors as subsectorName}
        <option value={subsectorName}>{subsectorName}</option>
      {/each}
    </select>
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'unusual.kind')}</span>
    <select class="field mt-2" bind:value={kind}>
      <option value="All">{text($locale, 'unusual.all')}</option>
      <option value="volume_standard_score">{text($locale, 'unusual.volume')}</option>
      <option value="foreign_flow_standard_score">{text($locale, 'unusual.flow')}</option>
    </select>
  </label>
</div>

{#if status === 'loading'}
  <div class="mt-8">
    <Notice title={text($locale, 'unusual.loading')} />
  </div>
{:else if status === 'error'}
  <div class="mt-8">
    <Notice title={text($locale, 'unusual.errorTitle')} detail={errorDetail} />
  </div>
{:else if filtered.length === 0}
  <div class="mt-8">
    <Notice title={text($locale, 'unusual.emptyTitle')} detail={text($locale, 'unusual.emptyDetail')} />
  </div>
{:else}
  {#if dateSpan}
    <div class="mt-8 rounded-2xl border border-forest/30 bg-white px-4 py-4 sm:px-5">
      <p class="text-xs font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'unusual.spanLabel')}</p>
      <p class="mt-1 font-serif text-3xl leading-tight">
        {formatAsOfRange(dateSpan.start, dateSpan.end, $locale)}
      </p>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-muted">{text($locale, 'unusual.spanHelp')}</p>
    </div>
  {/if}

  <p class="mt-6 text-sm text-muted">
    {text($locale, 'unusual.count', { count: filtered.length })}
    {#if subsector !== 'All'}
      {text($locale, 'unusual.in', { name: subsector })}
    {:else if sector !== 'All'}
      {text($locale, 'unusual.in', { name: sector })}
    {/if}
  </p>

  <div class="mt-4 grid gap-3">
    {#each visibleFlags as flag (`${flag.ticker_symbol}-${flag.anomaly_kind}`)}
      {@const view = anomalyPresentation(flag, $locale)}
      {@const row = rowBySymbol.get(flag.ticker_symbol)}
      <article class="rounded-2xl border border-line bg-white p-4 sm:p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <a class="font-serif text-3xl tracking-tight hover:text-forest" href={`/stock/${displaySymbol(flag.ticker_symbol)}`}>
              {displaySymbol(flag.ticker_symbol)}
            </a>
            <p class="mt-1 text-sm text-ink">{flag.company_name}</p>
            <p class="mt-1 text-sm text-muted">
              {row?.sector ?? '—'}
              {#if row?.sub_sector}
                · {row.sub_sector}
              {/if}
            </p>
          </div>
          <div class="text-right">
            <p class="numeral font-serif text-5xl leading-none text-forest">{formatZScore(flag.standard_score)}</p>
            <p class="mt-1 text-xs uppercase tracking-[0.14em] text-muted">{view.zLabel}</p>
            <div class="mt-3"><SourceTag label={view.source} /></div>
          </div>
        </div>
        <div class="mt-4 rounded-xl bg-sand px-3 py-3">
          <p class="text-xs font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'unusual.spanLabel')}</p>
          <p class="mt-1 font-serif text-2xl">{formatAsOfRange(flag.as_of_date, flag.as_of_date, $locale)}</p>
        </div>
        <p class="mt-4 text-base font-medium">{view.emoji} {view.label}</p>
        <p class="mt-2 max-w-xl text-sm leading-6 text-ink">{view.reference}</p>
        <Disclosure label={text($locale, 'unusual.why')}>
          <p class="text-sm leading-6">{view.reason}</p>
          <dl class="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div class="flex justify-between gap-4">
              <dt class="text-muted">{observedLabel(flag)}</dt>
              <dd>{formatObserved(flag)}</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-muted">{baselineLabel(flag)}</dt>
              <dd>{formatBaseline(flag)}</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-muted">{text($locale, 'unusual.flaggedFrom')}</dt>
              <dd>{flag.threshold.toFixed(1)}</dd>
            </div>
          </dl>
          <p class="mt-4 text-xs font-medium uppercase tracking-wide text-muted">{text($locale, 'unusual.method')}</p>
          <p class="mt-2 text-sm leading-6">{view.methodology}</p>
        </Disclosure>
      </article>
    {/each}
  </div>

  {#if visibleCount < filtered.length}
    <button
      class="mt-4 rounded-full border border-line bg-white px-4 py-2 text-sm font-medium"
      type="button"
      onclick={() => (visibleCount += 12)}
    >
      {text($locale, 'unusual.showMore')}
    </button>
  {/if}
{/if}

<Disclosure label={text($locale, 'unusual.how')}>
  <ul class="space-y-3 text-sm leading-6">
    <li>{text($locale, 'unusual.noteVolume')}</li>
    <li>{text($locale, 'unusual.noteFlow')}</li>
  </ul>
</Disclosure>
