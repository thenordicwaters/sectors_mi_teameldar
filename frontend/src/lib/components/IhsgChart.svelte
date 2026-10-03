<script lang="ts">
  import { onMount } from 'svelte';
  import Notice from './Notice.svelte';
  import SessionChart from './SessionChart.svelte';
  import SourceTag from './SourceTag.svelte';
  import { fetchIhsg } from '$lib/api';
  import { formatIndex, formatPercent, formatSessionDate } from '$lib/format';
  import { locale, text } from '$lib/i18n';
  import type { IndexSession, SessionStatus } from '$lib/types';

  let session = $state<IndexSession | null>(null);
  let status = $state<'loading' | 'ready' | 'error'>('loading');

  const up = $derived((session?.change ?? 0) >= 0);

  onMount(() => {
    fetchIhsg()
      .then((loaded) => {
        session = loaded;
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  function sessionSentence(current: IndexSession): string {
    const date = formatSessionDate(current.session_date, $locale);
    const key = statusKey(current.session_status);
    if (!key) return text($locale, 'ihsg.unavailable');
    return text($locale, key, { date });
  }

  function statusKey(sessionStatus: SessionStatus): 'ihsg.today' | 'ihsg.weekend' | 'ihsg.earlier' | null {
    if (sessionStatus === 'today') return 'ihsg.today';
    if (sessionStatus === 'weekend') return 'ihsg.weekend';
    if (sessionStatus === 'earlier') return 'ihsg.earlier';
    return null;
  }

  function levelSentence(current: IndexSession): string {
    if (current.last_price == null || current.prior_high == null) return '';
    if (current.last_price > current.prior_high) return text($locale, 'chart.above');
    if (current.last_price < current.prior_high) return text($locale, 'chart.below');
    return text($locale, 'chart.same');
  }
</script>

<section class="mt-8 rounded-2xl border border-line bg-white p-4 sm:p-5">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-xs font-medium uppercase tracking-[0.16em] text-forest">{text($locale, 'ihsg.kicker')}</p>
      <h2 class="mt-1 font-serif text-3xl">{text($locale, 'ihsg.title')}</h2>
    </div>
    <SourceTag label={text($locale, 'chart.source')} />
  </div>

  {#if status === 'loading'}
    <p class="mt-4 text-sm text-muted">{text($locale, 'ihsg.loading')}</p>
  {:else if status === 'error' || !session}
    <div class="mt-4">
      <Notice title={text($locale, 'ihsg.error')} />
    </div>
  {:else if session.last_price == null}
    <p class="mt-4 text-sm text-muted">{text($locale, 'ihsg.unavailable')}</p>
  {:else}
    <p class="numeral mt-3 font-serif text-5xl leading-none {up ? 'text-forest' : 'text-clay'}">
      {formatIndex(session.last_price, $locale)}
    </p>
    <p class="mt-2 text-sm {up ? 'text-forest' : 'text-clay'}">{formatPercent(session.change)}</p>
    <p class="mt-2 text-sm font-medium text-ink">{sessionSentence(session)}</p>
    {#if session.prior_high != null}
      <p class="mt-2 text-sm text-ink">
        {text($locale, 'ihsg.priorHigh', { price: formatIndex(session.prior_high, $locale) })}
        {#if session.prior_session_date}
          · {text($locale, 'ihsg.priorDate', { date: formatSessionDate(session.prior_session_date, $locale) })}
        {/if}
      </p>
      <p class="mt-1 text-sm text-muted">{levelSentence(session)}</p>
    {/if}
    <div class="mt-3">
      <SessionChart points={session.points} referencePrice={session.prior_high} priceKind="index" />
    </div>
    {#if session.points.length < 2}
      <p class="mt-2 text-sm text-muted">{text($locale, 'chart.empty')}</p>
    {/if}
    <p class="mt-2 text-sm leading-6 text-muted">{text($locale, 'chart.explain')}</p>
  {/if}
</section>
