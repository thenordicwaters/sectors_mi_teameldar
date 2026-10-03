<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import Disclosure from '$lib/components/Disclosure.svelte';
  import MethodPanel from '$lib/components/MethodPanel.svelte';
  import Notice from '$lib/components/Notice.svelte';
  import SessionChart from '$lib/components/SessionChart.svelte';
  import SourceTag from '$lib/components/SourceTag.svelte';
  import { fetchQuote, fetchScore, fetchStock } from '$lib/api';
  import { displaySymbol, formatPercent, formatPrice, formatRupiah, formatScore, formatSessionDate, formatZScore } from '$lib/format';
  import { locale, text } from '$lib/i18n';
  import {
    METHOD_ORDER,
    anomalyPresentation,
    signalLabel,
    signalMethodology,
    signalPresentation
  } from '$lib/presentation';
  import type { CompositeResult, StockDetail, StockQuote } from '$lib/types';

  let stock = $state<StockDetail | null>(null);
  let score = $state<CompositeResult | null>(null);
  let quote = $state<StockQuote | null>(null);
  let stockStatus = $state<'loading' | 'ready' | 'error'>('loading');
  let scoreStatus = $state<'loading' | 'ready' | 'error'>('loading');
  let quoteStatus = $state<'loading' | 'ready' | 'error'>('loading');
  let stockError = $state('');
  let scoreError = $state('');
  let loadedSymbol = '';

  const overall = $derived(score?.score ?? stock?.score.overall_score ?? null);
  const rank = $derived(score ? score.rank : (stock?.score.universe_rank ?? null));
  const liveClose = $derived(quote?.close ?? null);
  const shownClose = $derived(liveClose ?? stock?.overview.last_close_price ?? null);
  const shownChange = $derived(quote?.change ?? (liveClose == null ? stock?.overview.daily_close_change ?? null : null));

  onMount(() => {
    return page.subscribe((current) => {
      const nextSymbol = current.params.symbol ?? '';
      if (!nextSymbol || nextSymbol === loadedSymbol) return;
      loadedSymbol = nextSymbol;
      void load(nextSymbol);
    });
  });

  async function load(nextSymbol: string) {
    stock = null;
    score = null;
    quote = null;
    stockStatus = 'loading';
    scoreStatus = 'loading';
    quoteStatus = 'loading';
    stockError = '';
    scoreError = '';

    const stockRequest = fetchStock(nextSymbol)
      .then((loaded) => {
        if (loadedSymbol !== nextSymbol) return;
        stock = loaded;
        stockStatus = 'ready';
      })
      .catch((error: unknown) => {
        if (loadedSymbol !== nextSymbol) return;
        stockError = error instanceof Error ? error.message : 'This stock could not be loaded.';
        stockStatus = 'error';
      });

    const scoreRequest = fetchScore(nextSymbol)
      .then((loaded) => {
        if (loadedSymbol !== nextSymbol) return;
        score = loaded;
        scoreStatus = 'ready';
      })
      .catch((error: unknown) => {
        if (loadedSymbol !== nextSymbol) return;
        scoreError = error instanceof Error ? error.message : 'The score detail could not be loaded.';
        scoreStatus = 'error';
      });

    const quoteRequest = fetchQuote(nextSymbol)
      .then((loaded) => {
        if (loadedSymbol !== nextSymbol) return;
        quote = loaded;
        quoteStatus = 'ready';
      })
      .catch(() => {
        if (loadedSymbol !== nextSymbol) return;
        quoteStatus = 'error';
      });

    await Promise.all([stockRequest, scoreRequest, quoteRequest]);
  }

  function quoteSentence(): string {
    if (!quote || quote.session_status === 'unavailable' || quote.close == null) {
      return text($locale, 'quote.unavailable');
    }
    if (quote.session_status === 'today') return text($locale, 'quote.today');
    if (quote.session_status === 'weekend') return text($locale, 'quote.weekend');
    return text($locale, 'quote.earlier');
  }

  function levelSentence(): string {
    if (quote?.close == null || quote.prior_high == null) return '';
    if (quote.close > quote.prior_high) return text($locale, 'chart.above');
    if (quote.close < quote.prior_high) return text($locale, 'chart.below');
    return text($locale, 'chart.same');
  }
</script>

<svelte:head>
  <title>{stock ? `${displaySymbol(stock.ticker_symbol)} · ${stock.company_name}` : 'Stock'}</title>
</svelte:head>

{#if stockStatus === 'loading'}
  <Notice title={text($locale, 'stock.loading')} />
{:else if stockStatus === 'error' || !stock}
  <Notice title={text($locale, 'stock.errorTitle')} detail={stockError} />
{:else}
  <a class="text-sm text-muted hover:text-ink" href="/">{text($locale, 'stock.back')}</a>

  <header class="mt-4 grid gap-6 border-b border-line pb-8 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
    <div>
      <p class="font-serif text-5xl tracking-tight">{displaySymbol(stock.ticker_symbol)}</p>
      <h1 class="mt-1 text-xl text-ink">{stock.company_name}</h1>
      <p class="mt-2 text-sm text-muted">
        {stock.overview.sector ?? text($locale, 'stock.sectorMissing')}
        {#if stock.overview.sub_sector}
          · {stock.overview.sub_sector}
        {/if}
      </p>
      {#if quoteStatus === 'loading'}
        <p class="mt-4 text-sm text-muted">{text($locale, 'quote.checking')}</p>
      {:else}
        <p class="mt-4 flex flex-wrap items-end gap-3">
          <span class="numeral font-serif text-5xl leading-none">{formatPrice(shownClose, $locale)}</span>
          <span class={shownChange != null && shownChange < 0 ? 'text-clay' : 'text-forest'}>
            {formatPercent(shownChange)}
          </span>
          <SourceTag label={quote?.close != null ? 'Yahoo Finance' : 'Sectors'} />
        </p>
        <p class="mt-3 text-xs font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'quote.asOf')}</p>
        <p class="font-serif text-3xl">
          {formatSessionDate(quote?.session_date ?? quote?.snapshot_fetched_at, $locale)}
        </p>
        <p class="mt-1 max-w-xl text-sm leading-6 text-ink">{quoteSentence()}</p>
        {#if quote?.snapshot_close != null && quote.snapshot_fetched_at}
          <p class="mt-2 max-w-xl text-sm leading-6 text-muted">
            {text($locale, 'quote.snapshot', {
              date: formatSessionDate(quote.snapshot_fetched_at, $locale),
              price: formatPrice(quote.snapshot_close, $locale)
            })}
          </p>
        {/if}
      {/if}
    </div>
    <div class="md:text-right">
      <p class="text-xs font-medium uppercase tracking-[0.16em] text-muted">{text($locale, 'stock.overall')}</p>
      <p class="numeral font-serif text-7xl leading-none text-forest">{formatScore(overall)}</p>
      {#if rank != null}
        <p class="mt-2 text-sm text-muted">{text($locale, 'stock.rank', { rank })}</p>
      {:else if score?.excluded_reason}
        <p class="mt-2 max-w-xs text-sm text-muted md:ml-auto">{score.excluded_reason}</p>
      {/if}
    </div>
  </header>

  <section class="mt-8 rounded-2xl border border-line bg-white p-4 sm:p-5">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="font-serif text-2xl">{text($locale, 'stock.chartTitle')}</h2>
        {#if quote?.prior_high != null}
          <p class="mt-2 text-sm font-medium text-ink">
            {text($locale, 'chart.h1')}
            {formatPrice(quote.prior_high, $locale)}
            {#if quote.prior_session_date}
              · {formatSessionDate(quote.prior_session_date, $locale)}
            {/if}
          </p>
          <p class="mt-1 text-sm text-muted">{levelSentence()}</p>
        {/if}
      </div>
      <SourceTag label="Yahoo Finance" />
    </div>
    {#if quote && quote.points.length >= 2}
      <div class="mt-3">
        <SessionChart points={quote.points} referencePrice={quote.prior_high} />
      </div>
    {:else if quoteStatus !== 'loading'}
      <p class="mt-3 text-sm text-muted">{text($locale, 'chart.empty')}</p>
    {/if}
    <p class="mt-3 text-sm leading-6 text-muted">{text($locale, 'chart.explain')}</p>
    <Disclosure label={text($locale, 'quote.whyTitle')}>
      <p class="text-sm leading-6">{text($locale, 'quote.whyBody')}</p>
    </Disclosure>
  </section>

  <section class="mt-8">
    <div class="flex items-end justify-between gap-4">
      <h2 class="font-serif text-2xl">{text($locale, 'stock.scores')}</h2>
      <a class="text-sm font-medium text-forest" href={`/compare?symbols=${displaySymbol(stock.ticker_symbol)}`}>
        {text($locale, 'stock.compare')}
      </a>
    </div>
    {#if scoreStatus === 'loading'}
      <div class="mt-4">
        <Notice title={text($locale, 'stock.scoring')} />
      </div>
    {:else if scoreStatus === 'error' || !score}
      <div class="mt-4">
        <Notice title={text($locale, 'stock.scoreError')} detail={scoreError} />
      </div>
    {:else}
      <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {#each METHOD_ORDER as methodKey (methodKey)}
          <MethodPanel {methodKey} method={score.methods[methodKey]} />
        {/each}
      </div>
      <Disclosure label={text($locale, 'stock.howOverall')}>
        <dl class="grid gap-2 text-sm sm:grid-cols-2">
          <div class="flex justify-between gap-4">
            <dt class="text-muted">{text($locale, 'stock.quality')}</dt>
            <dd>{formatScore(score.components.quality)}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">{text($locale, 'stock.value')}</dt>
            <dd>{formatScore(score.components.value)}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">{text($locale, 'stock.momentum')}</dt>
            <dd>{formatScore(score.components.momentum)}</dd>
          </div>
          <div class="flex justify-between gap-4">
            <dt class="text-muted">{text($locale, 'stock.flow')}</dt>
            <dd>{formatScore(score.components.flow)}</dd>
          </div>
        </dl>
        {#if Object.keys(score.weights_used).length > 0}
          <p class="mt-4 text-sm leading-6 text-ink">
            {text($locale, 'stock.weights')}
            {Object.entries(score.weights_used)
              .map(([name, weight]) => `${name} ${Math.round(weight)}`)
              .join(' · ')}
          </p>
        {/if}
        <p class="mt-3 text-sm leading-6 text-muted">{text($locale, 'stock.pillars')}</p>
        <p class="mt-3 text-sm text-muted">{text($locale, 'stock.calculated')}</p>
      </Disclosure>
    {/if}
  </section>

  <section class="mt-10">
    <h2 class="font-serif text-2xl">{text($locale, 'stock.whyInteresting')}</h2>
    {#if stock.signals.length === 0 && stock.anomalies.length === 0}
      <p class="mt-3 text-sm leading-6 text-muted">{text($locale, 'stock.noneInteresting')}</p>
    {:else}
      <div class="mt-4 grid gap-3">
        {#each stock.signals as badge (badge.signal_kind)}
          {@const view = signalPresentation(badge)}
          <article class="rounded-2xl border border-line bg-white p-4">
            <div class="flex items-start justify-between gap-3">
              <h3 class="text-base font-medium">{view.emoji} {signalLabel(badge.signal_kind, $locale)}</h3>
              <SourceTag label={view.source} />
            </div>
            <Disclosure label={text($locale, 'stock.viewDetails')}>
              <p class="text-sm leading-6">{signalMethodology(badge.signal_kind, $locale)}</p>
            </Disclosure>
          </article>
        {/each}
        {#each stock.anomalies as anomaly (`${anomaly.anomaly_kind}-${anomaly.as_of_date}`)}
          {@const view = anomalyPresentation(anomaly, $locale)}
          <article class="rounded-2xl border border-line bg-white p-4">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h3 class="text-base font-medium">{view.emoji} {view.label}</h3>
                <p class="mt-3 text-xs font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'quote.asOf')}</p>
                <p class="font-serif text-2xl">{formatSessionDate(anomaly.as_of_date, $locale)}</p>
                <p class="mt-2 text-sm leading-6 text-ink">{view.reference}</p>
              </div>
              <div class="text-right">
                <p class="numeral font-serif text-4xl leading-none text-forest">
                  {formatZScore(anomaly.standard_score)}
                </p>
                <p class="mt-1 text-xs uppercase tracking-wide text-muted">{view.zLabel}</p>
                <div class="mt-2"><SourceTag label={view.source} /></div>
              </div>
            </div>
            <Disclosure label={text($locale, 'stock.whyUnusual')}>
              <p class="text-sm leading-6">{view.reason}</p>
              <p class="mt-3 text-sm text-muted">
                {text($locale, 'stock.flaggedFrom')}
                {text($locale, 'stock.deviations', { count: anomaly.threshold.toFixed(1) })}
              </p>
              <p class="mt-4 text-xs font-medium uppercase tracking-wide text-muted">{text($locale, 'stock.methodology')}</p>
              <p class="mt-2 text-sm leading-6">{view.methodology}</p>
            </Disclosure>
          </article>
        {/each}
      </div>
    {/if}
  </section>

  <section class="mt-10">
    <h2 class="font-serif text-2xl">{text($locale, 'stock.figures')}</h2>
    <p class="mt-2 text-sm text-muted">{text($locale, 'stock.figuresHelp')}</p>
    <dl class="mt-4 grid gap-3 sm:grid-cols-2">
      <div class="rounded-2xl border border-line bg-white p-4">
        <dt class="text-sm text-muted">{text($locale, 'stock.marketCap')}</dt>
        <dd class="mt-1 flex items-center justify-between gap-3">
          <span class="font-medium">{formatRupiah(stock.overview.market_capitalization)}</span>
          <SourceTag label="Sectors" />
        </dd>
      </div>
      <div class="rounded-2xl border border-line bg-white p-4">
        <dt class="text-sm text-muted">{text($locale, 'stock.pe')}</dt>
        <dd class="mt-1 flex items-center justify-between gap-3">
          <span class="font-medium">
            {stock.valuation.price_to_earnings_trailing_twelve_months?.toFixed(1) ?? '—'}
          </span>
          <SourceTag label="Sectors" />
        </dd>
      </div>
      <div class="rounded-2xl border border-line bg-white p-4">
        <dt class="text-sm text-muted">{text($locale, 'stock.pb')}</dt>
        <dd class="mt-1 flex items-center justify-between gap-3">
          <span class="font-medium">
            {stock.valuation.price_to_book_most_recent_quarter?.toFixed(2) ?? '—'}
          </span>
          <SourceTag label="Sectors" />
        </dd>
      </div>
      <div class="rounded-2xl border border-line bg-white p-4">
        <dt class="text-sm text-muted">{text($locale, 'stock.foreign')}</dt>
        <dd class="mt-1 flex items-center justify-between gap-3">
          <span class="font-medium">{formatRupiah(stock.flow.net_foreign_inflow)}</span>
          <SourceTag label="Sectors" />
        </dd>
      </div>
    </dl>
    <p class="mt-4 text-xs leading-5 text-muted">{stock.disclaimer}</p>
    <p class="mt-2 text-xs text-muted">{text($locale, 'stock.momentumNote')}</p>
  </section>
{/if}
