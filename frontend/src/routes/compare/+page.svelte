<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import Notice from '$lib/components/Notice.svelte';
  import { fetchScore, fetchStock } from '$lib/api';
  import { displaySymbol, formatScore } from '$lib/format';
  import { locale, text } from '$lib/i18n';
  import {
    METHOD_ORDER,
    anomalyPresentation,
    methodScoreText,
    methodTitle,
    primaryAnomaly,
    signalLabel,
    signalPresentation
  } from '$lib/presentation';
  import type { CompositeResult, StockDetail } from '$lib/types';

  type ComparedStock = {
    symbol: string;
    stock: StockDetail | null;
    score: CompositeResult | null;
    error: string;
  };

  let first = $state('');
  let second = $state('');
  let third = $state('');
  let columns = $state<ComparedStock[]>([]);
  let status = $state<'idle' | 'loading' | 'ready' | 'error'>('idle');
  let loadedKey = '';

  onMount(() => {
    return page.subscribe((current) => {
      const raw = current.url.searchParams.get('symbols') ?? '';
      const symbols = parseSymbols(raw);
      const key = symbols.join(',');
      if (key === loadedKey) return;
      loadedKey = key;
      first = symbols[0] ?? '';
      second = symbols[1] ?? '';
      third = symbols[2] ?? '';
      if (symbols.length >= 2) {
        void load(symbols);
        return;
      }
      columns = [];
      status = 'idle';
    });
  });

  function parseSymbols(raw: string): string[] {
    return raw
      .split(',')
      .map((symbol) => displaySymbol(symbol))
      .filter((symbol) => /^[A-Z]{4}$/.test(symbol))
      .slice(0, 3);
  }

  function submitCompare(event: SubmitEvent) {
    event.preventDefault();
    const symbols = parseSymbols([first, second, third].join(','));
    const next = symbols.join(',');
    if (next === loadedKey && symbols.length >= 2) {
      void load(symbols);
      return;
    }
    void goto(next ? `/compare?symbols=${next}` : '/compare');
  }

  async function load(symbols: string[]) {
    status = 'loading';
    const loaded = await Promise.all(
      symbols.map(async (symbol) => {
        try {
          const [stock, score] = await Promise.all([fetchStock(symbol), fetchScore(symbol)]);
          return { symbol, stock, score, error: '' };
        } catch (error: unknown) {
          return {
            symbol,
            stock: null,
            score: null,
            error: error instanceof Error ? error.message : 'Unavailable'
          };
        }
      })
    );
    if (loadedKey !== symbols.join(',')) return;
    columns = loaded;
    status = loaded.some((column) => column.stock && column.score) ? 'ready' : 'error';
  }
</script>

<svelte:head>
  <title>{text($locale, 'compare.title')}</title>
</svelte:head>

<section class="max-w-3xl">
  <p class="text-sm font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'compare.kicker')}</p>
  <h1 class="mt-2 font-serif text-4xl leading-tight sm:text-5xl">{text($locale, 'compare.title')}</h1>
  <p class="mt-4 text-base leading-7 text-muted">{text($locale, 'compare.intro')}</p>
</section>

<form class="mt-8 grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end" onsubmit={submitCompare}>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'compare.first')}</span>
    <input class="field mt-2 uppercase" bind:value={first} maxlength="4" placeholder="BBCA" />
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'compare.second')}</span>
    <input class="field mt-2 uppercase" bind:value={second} maxlength="4" placeholder="BBRI" />
  </label>
  <label class="block text-sm">
    <span class="font-medium">{text($locale, 'compare.third')}</span>
    <input class="field mt-2 uppercase" bind:value={third} maxlength="4" placeholder="BMRI" />
  </label>
  <button class="rounded-xl bg-ink px-4 py-3 text-sm font-medium text-paper" type="submit">{text($locale, 'compare.submit')}</button>
</form>

{#if status === 'loading'}
  <div class="mt-8">
    <Notice title={text($locale, 'compare.loading')} />
  </div>
{:else if status === 'error'}
  <div class="mt-8">
    <Notice
      title={text($locale, 'compare.errorTitle')}
      detail={columns.map((column) => `${column.symbol}: ${column.error || text($locale, 'compare.loaded')}`).join(' ')}
    />
  </div>
{:else if status === 'idle'}
  <div class="mt-8">
    <Notice title={text($locale, 'compare.idleTitle')} detail={text($locale, 'compare.idleDetail')} />
  </div>
{:else}
  <div class="mt-8 overflow-x-auto rounded-2xl border border-line bg-white">
    <table class="w-full min-w-[40rem] border-collapse text-left">
      <thead>
        <tr class="border-b border-line">
          <th class="px-4 py-4"></th>
          {#each columns as column}
            <th class="px-4 py-4 align-bottom font-normal">
              {#if column.stock}
                <a class="font-serif text-3xl tracking-tight hover:text-forest" href={`/stock/${column.symbol}`}>
                  {column.symbol}
                </a>
                <p class="mt-1 text-sm font-normal text-muted">{column.stock.company_name}</p>
                <p class="mt-1 text-xs text-muted">
                  {column.stock.overview.sector ?? '—'}
                  {#if column.stock.overview.sub_sector}
                    · {column.stock.overview.sub_sector}
                  {/if}
                </p>
              {:else}
                <p class="font-serif text-3xl">{column.symbol}</p>
                <p class="mt-1 text-sm text-muted">{column.error}</p>
              {/if}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-line">
          <th class="px-4 py-4 text-sm font-medium">{text($locale, 'compare.overall')}</th>
          {#each columns as column}
            <td class="px-4 py-4">
              <span class="numeral font-serif text-4xl text-forest">
                {formatScore(column.score?.score)}
              </span>
              {#if column.score?.excluded_reason}
                <p class="mt-1 max-w-[12rem] text-xs leading-5 text-muted">{column.score.excluded_reason}</p>
              {/if}
            </td>
          {/each}
        </tr>
        {#each METHOD_ORDER as methodKey}
          <tr class="border-b border-line">
            <th class="px-4 py-3 text-sm font-medium">{methodTitle(methodKey, $locale)}</th>
            {#each columns as column}
              {@const method = column.score?.methods[methodKey]}
              <td class="px-4 py-3">
                <span class="numeral font-serif text-2xl">{methodScoreText(methodKey, method)}</span>
                {#if method && !method.applicable}
                  <p class="text-xs text-muted">{text($locale, 'stock.notApplied')}</p>
                {:else if method && method.applicable && method.score == null}
                  <p class="text-xs text-muted">{text($locale, 'stock.noScore')}</p>
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
        <tr class="border-b border-line">
          <th class="px-4 py-4 text-sm font-medium align-top">{text($locale, 'compare.signals')}</th>
          {#each columns as column}
            <td class="px-4 py-4 align-top">
              <div class="flex flex-col items-start gap-1">
                {#each column.stock?.signals ?? [] as badge}
                  {@const view = signalPresentation(badge)}
                  <span class="chip">{view.emoji} {signalLabel(badge.signal_kind, $locale)}</span>
                {/each}
                {#if (column.stock?.signals.length ?? 0) === 0}
                  <span class="text-sm text-muted">—</span>
                {/if}
              </div>
            </td>
          {/each}
        </tr>
        <tr>
          <th class="px-4 py-4 text-sm font-medium align-top">{text($locale, 'compare.anomaly')}</th>
          {#each columns as column}
            {@const anomaly = primaryAnomaly(column.stock?.anomalies ?? [])}
            <td class="px-4 py-4 align-top">
              {#if anomaly}
                {@const view = anomalyPresentation(anomaly, $locale)}
                <span class="chip chip-anomaly">{view.emoji} {view.label}</span>
                <p class="mt-2 text-sm text-muted">{view.zLabel} {anomaly.standard_score.toFixed(1)}</p>
              {:else}
                <span class="text-sm text-muted">—</span>
              {/if}
            </td>
          {/each}
        </tr>
      </tbody>
    </table>
  </div>
  <p class="mt-4 text-xs leading-5 text-muted">
    {text($locale, 'compare.footnote')}
  </p>
{/if}
