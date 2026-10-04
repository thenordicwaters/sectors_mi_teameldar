<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import HistoryChart from '$lib/components/HistoryChart.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { loadUniverse } from '$lib/api';
  import { displaySymbol, formatScore, uniqueSorted } from '$lib/format';
  import { locale, text } from '$lib/i18n';
  import {
    anomalyPresentation,
    pillarValue,
    primaryAnomaly,
    signalLabel,
    signalPresentation,
    type SortKey
  } from '$lib/presentation';
  import type { ScreenerRow, SignalKind } from '$lib/types';

  let rows = $state<ScreenerRow[]>([]);
  let status = $state<'loading' | 'ready' | 'error'>('loading');
  let errorDetail = $state('');

  let query = $state('');
  let sector = $state('All');
  let subsector = $state('All');
  let signal = $state<'All' | SignalKind>('All');
  let anomalyOnly = $state(false);
  // Number inputs bind a number once the user types, and null once cleared.
  let minScore = $state<string | number | null>('');
  let sortKey = $state<SortKey>('overall_score');
  let visibleCount = $state(20);

  const sectors = $derived(uniqueSorted(rows.map((row) => row.sector)));
  const subsectors = $derived(
    uniqueSorted(
      rows
        .filter((row) => sector === 'All' || row.sector === sector)
        .map((row) => row.sub_sector)
    )
  );

  const filtered = $derived.by(() => {
    const needle = searchNeedle(query);
    const minimum = minimumOverallScore(minScore);
    const matched = rows.filter((row) => {
      if (sector !== 'All' && row.sector !== sector) return false;
      if (subsector !== 'All' && row.sub_sector !== subsector) return false;
      if (signal !== 'All' && !row.signals.some((badge) => badge.signal_kind === signal)) return false;
      if (anomalyOnly && !row.has_anomaly) return false;
      if (minimum != null && !Number.isNaN(minimum)) {
        if (row.score.overall_score == null || row.score.overall_score < minimum) return false;
      }
      if (!needle) return true;
      return (
        displaySymbol(row.ticker_symbol).toLowerCase().includes(needle) ||
        row.company_name.toLowerCase().includes(needle)
      );
    });
    const present = matched.filter((row) => pillarValue(row, sortKey) != null);
    const missing = matched.filter((row) => pillarValue(row, sortKey) == null);
    present.sort((left, right) => {
      const leftValue = pillarValue(left, sortKey) ?? 0;
      const rightValue = pillarValue(right, sortKey) ?? 0;
      if (rightValue !== leftValue) return rightValue - leftValue;
      return left.ticker_symbol.localeCompare(right.ticker_symbol);
    });
    missing.sort((left, right) => left.ticker_symbol.localeCompare(right.ticker_symbol));
    return [...present, ...missing];
  });

  const visibleRows = $derived(filtered.slice(0, visibleCount));

  $effect(() => {
    query;
    sector;
    subsector;
    signal;
    anomalyOnly;
    minScore;
    sortKey;
    visibleCount = 20;
  });

  $effect(() => {
    if (subsector !== 'All' && !subsectors.includes(subsector)) subsector = 'All';
  });

  onMount(() => {
    loadUniverse()
      .then((loaded) => {
        rows = loaded;
        status = 'ready';
      })
      .catch((error: unknown) => {
        errorDetail = error instanceof Error ? error.message : 'The screener could not be loaded.';
        status = 'error';
      });
  });

  function openSearch(event: SubmitEvent) {
    event.preventDefault();
    const exact = query.trim().toUpperCase().replace(/\.JK$/, '');
    if (/^[A-Z]{4}$/.test(exact)) {
      void goto(`/stock/${exact}`);
      return;
    }
    if (filtered.length === 1) {
      void goto(`/stock/${displaySymbol(filtered[0].ticker_symbol)}`);
    }
  }

  function clearFilters() {
    query = '';
    sector = 'All';
    subsector = 'All';
    signal = 'All';
    anomalyOnly = false;
    minScore = '';
    sortKey = 'overall_score';
  }

  function searchNeedle(raw: string): string {
    return raw.trim().toLowerCase().replace(/\.jk$/, '');
  }

  function minimumOverallScore(raw: string | number | null): number | null {
    if (raw == null) return null;
    if (typeof raw === 'number') return Number.isNaN(raw) ? null : raw;
    const text = raw.trim();
    if (text === '') return null;
    const value = Number(text);
    return Number.isNaN(value) ? null : value;
  }

  function scopeLabel(): string {
    if (subsector !== 'All') return subsector;
    if (sector !== 'All') return sector;
    return text($locale, 'home.market');
  }
</script>

<section class="max-w-3xl">
  <p class="text-sm font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'home.kicker')}</p>
  <h1 class="mt-2 font-serif text-4xl leading-tight text-ink sm:text-5xl">
    {text($locale, 'home.title')}
  </h1>
  <p class="mt-4 max-w-xl text-base leading-7 text-muted">
    {#if status === 'ready'}
      {text($locale, 'home.ready', { count: rows.length.toLocaleString($locale === 'id' ? 'id-ID' : 'en-US') })}
    {:else}
      {text($locale, 'home.intro')}
    {/if}
  </p>
</section>

<HistoryChart
  resource="/api/market/ihsg/history"
  kicker={text($locale, 'ihsg.kicker')}
  title={text($locale, 'ihsg.title')}
  priceKind="index"
/>

<form class="mt-8" onsubmit={openSearch}>
  <label class="text-sm font-medium" for="ticker-search">{text($locale, 'home.searchLabel')}</label>
  <input
    id="ticker-search"
    class="field mt-2 text-lg"
    bind:value={query}
    placeholder={text($locale, 'home.searchPlaceholder')}
    autocomplete="off"
  />
</form>

<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'home.sector')}</span>
    <select class="field mt-2" bind:value={sector}>
      <option value="All">{text($locale, 'home.all')}</option>
      {#each sectors as sectorName}
        <option value={sectorName}>{sectorName}</option>
      {/each}
    </select>
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'home.subsector')}</span>
    <select class="field mt-2" bind:value={subsector}>
      <option value="All">{text($locale, 'home.all')}</option>
      {#each subsectors as subsectorName}
        <option value={subsectorName}>{subsectorName}</option>
      {/each}
    </select>
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'home.signal')}</span>
    <select class="field mt-2" bind:value={signal}>
      <option value="All">{text($locale, 'home.all')}</option>
      <option value="mover">{text($locale, 'signal.mover')}</option>
      <option value="fifty_two_week_high">{text($locale, 'signal.fifty_two_week_high')}</option>
      <option value="foreign_accumulation">{text($locale, 'signal.foreign_accumulation')}</option>
      <option value="insider_buying">{text($locale, 'signal.insider_buying')}</option>
    </select>
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'home.sort')}</span>
    <select class="field mt-2" bind:value={sortKey}>
      <option value="overall_score">{text($locale, 'home.sortOverall')}</option>
      <option value="quality_score">{text($locale, 'home.sortQuality')}</option>
      <option value="value_score">{text($locale, 'home.sortValue')}</option>
      <option value="momentum_score">{text($locale, 'home.sortMomentum')}</option>
      <option value="flow_score">{text($locale, 'home.sortFlow')}</option>
    </select>
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'home.minScore')}</span>
    <input class="field mt-2" type="number" min="0" max="100" bind:value={minScore} placeholder={text($locale, 'home.any')} />
  </label>
  <label class="mt-7 flex items-center gap-2 text-sm">
    <input type="checkbox" bind:checked={anomalyOnly} />
    {text($locale, 'home.unusualOnly')}
  </label>
</div>

{#if status === 'loading'}
  <div class="mt-8">
    <Notice title={text($locale, 'home.loadingTitle')} detail={text($locale, 'home.loadingDetail')} />
  </div>
{:else if status === 'error'}
  <div class="mt-8">
    <Notice title={text($locale, 'home.errorTitle')} detail={errorDetail} />
  </div>
{:else if filtered.length === 0}
  <div class="mt-8">
    <Notice title={text($locale, 'home.emptyTitle')} detail={text($locale, 'home.emptyDetail')} />
    <button class="mt-4 text-sm font-semibold text-forest" type="button" onclick={clearFilters}>
      {text($locale, 'home.clearFilters')}
    </button>
  </div>
{:else}
  <div class="mt-8 flex items-end justify-between gap-4">
    <p class="text-sm text-muted">
      {text($locale, 'home.inScope', {
        count: filtered.length.toLocaleString($locale === 'id' ? 'id-ID' : 'en-US'),
        scope: scopeLabel()
      })}
    </p>
    <button class="text-sm text-muted hover:text-ink" type="button" onclick={clearFilters}>{text($locale, 'home.clear')}</button>
  </div>

  <div class="mt-3 overflow-x-auto rounded-2xl border border-line bg-white">
    <div
      class="hidden min-w-[62rem] grid-cols-[4.5rem_minmax(9.5rem,1.5fr)_minmax(7.5rem,0.9fr)_minmax(8.5rem,1fr)_9.25rem_minmax(9.5rem,1.1fr)_minmax(9rem,1fr)] gap-x-4 border-b border-line px-4 py-3 text-[0.7rem] font-medium uppercase leading-tight tracking-[0.04em] text-muted md:grid"
    >
      <span class="whitespace-nowrap">{text($locale, 'home.ticker')}</span>
      <span class="whitespace-nowrap">{text($locale, 'home.company')}</span>
      <span class="whitespace-nowrap">{text($locale, 'home.sector')}</span>
      <span class="whitespace-nowrap">{text($locale, 'home.subsector')}</span>
      <span class="whitespace-nowrap">{text($locale, 'home.overall')}</span>
      <span class="whitespace-nowrap">{text($locale, 'home.signalCol')}</span>
      <span class="whitespace-nowrap">{text($locale, 'home.anomaly')}</span>
    </div>
    <ul>
      {#each visibleRows as row (row.ticker_symbol)}
        {@const anomaly = primaryAnomaly(row.anomalies)}
        {@const anomalyView = anomaly ? anomalyPresentation(anomaly, $locale) : null}
        <li class="border-b border-line last:border-b-0">
          <a
            href={`/stock/${displaySymbol(row.ticker_symbol)}`}
            class="grid gap-3 px-4 py-4 transition hover:bg-sand/60 md:min-w-[62rem] md:grid-cols-[4.5rem_minmax(9.5rem,1.5fr)_minmax(7.5rem,0.9fr)_minmax(8.5rem,1fr)_9.25rem_minmax(9.5rem,1.1fr)_minmax(9rem,1fr)] md:items-center md:gap-x-4"
          >
            <span class="font-semibold tracking-tight">{displaySymbol(row.ticker_symbol)}</span>
            <span class="truncate text-sm text-ink">{row.company_name}</span>
            <span class="truncate text-sm text-muted">{row.sector ?? '—'}</span>
            <span class="truncate text-sm text-muted">{row.sub_sector ?? '—'}</span>
            <span class="numeral font-serif text-3xl leading-none text-forest">
              {formatScore(row.score.overall_score)}
            </span>
            <span class="flex flex-wrap gap-1">
              {#each row.signals.slice(0, 2) as badge}
                {@const view = signalPresentation(badge)}
                <span class="chip">{view.emoji} {signalLabel(badge.signal_kind, $locale)}</span>
              {/each}
              {#if row.signals.length > 2}
                <span class="chip">+{row.signals.length - 2}</span>
              {/if}
              {#if row.signals.length === 0}
                <span class="text-sm text-muted">—</span>
              {/if}
            </span>
            <span>
              {#if anomaly && anomalyView}
                <span class="chip chip-anomaly">{anomalyView.emoji} {anomalyView.label}</span>
              {:else}
                <span class="text-sm text-muted">—</span>
              {/if}
            </span>
          </a>
        </li>
      {/each}
    </ul>
  </div>

  {#if visibleCount < filtered.length}
    <button
      class="mt-4 rounded-full border border-line bg-white px-4 py-2 text-sm font-medium"
      type="button"
      onclick={() => (visibleCount += 20)}
    >
      {text($locale, 'home.showMore')}
    </button>
  {/if}
{/if}
