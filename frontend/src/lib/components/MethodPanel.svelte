<script lang="ts">
  import Disclosure from './Disclosure.svelte';
  import SourceTag from './SourceTag.svelte';
  import { locale, text } from '$lib/i18n';
  import {
    evidenceLines,
    methodBeginner,
    methodHeadline,
    methodMethodology,
    methodScoreText,
    methodSource,
    methodSourceDetail,
    methodTitle,
    piotroskiResultLabel,
    piotroskiTestLabel,
    piotroskiTests,
    type MethodKey
  } from '$lib/presentation';
  import type { MethodResult } from '$lib/types';

  let { methodKey, method }: { methodKey: MethodKey; method: MethodResult | undefined } = $props();

  const tests = $derived(method ? piotroskiTests(method.breakdown) : []);
  const lines = $derived(method ? evidenceLines(method.breakdown, $locale) : []);
  const headline = $derived(methodHeadline(methodKey, method, $locale));
</script>

<article class="flex h-full flex-col rounded-2xl border border-line bg-white p-4">
  <div class="flex items-start justify-between gap-3">
    <h3 class="text-sm font-medium text-ink">{methodTitle(methodKey, $locale)}</h3>
    <SourceTag label={methodSource(methodKey, method)} />
  </div>
  <p class="numeral mt-3 font-serif text-4xl leading-none text-forest">
    {methodScoreText(methodKey, method)}
  </p>
  {#if method && !method.applicable}
    <p class="mt-2 text-xs uppercase tracking-wide text-muted">{text($locale, 'stock.notApplied')}</p>
  {:else if method && method.score == null}
    <p class="mt-2 text-xs uppercase tracking-wide text-muted">{text($locale, 'stock.noScore')}</p>
  {/if}
  <p class="mt-3 text-sm leading-6 text-muted">{headline}</p>
  <p class="mt-3 text-xs font-medium uppercase tracking-[0.14em] text-forest">{text($locale, 'stock.plain')}</p>
  <p class="mt-1 text-sm leading-6 text-ink">{methodBeginner(methodKey, $locale)}</p>
  <div class="mt-auto pt-3">
    <Disclosure label={text($locale, 'stock.viewDetails')}>
      {#if method}
        {#if tests.length > 0}
          <p class="text-xs font-medium uppercase tracking-wide text-muted">{text($locale, 'stock.tests')}</p>
          <ul class="mt-2 space-y-1 text-sm">
            {#each tests as test}
              <li class="flex justify-between gap-4">
                <span>{piotroskiTestLabel(test, $locale)}</span>
                <span class={test.result === 'pass' ? 'text-forest' : 'text-muted'}>
                  {piotroskiResultLabel(test.result, $locale)}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
        {#if lines.length > 0}
          <p class="mt-4 text-xs font-medium uppercase tracking-wide text-muted">{text($locale, 'stock.evidence')}</p>
          <dl class="mt-2 space-y-1 text-sm">
            {#each lines as line}
              <div class="flex justify-between gap-4">
                <dt class="text-muted">{line.label}</dt>
                <dd class="text-right">{line.value}</dd>
              </div>
            {/each}
          </dl>
        {/if}
        {#if method.missing_fields.length > 0}
          <p class="mt-4 text-sm leading-6 text-muted">
            {text($locale, 'stock.missing', { fields: method.missing_fields.join(', ') })}
          </p>
        {/if}
      {/if}
      <p class="mt-4 text-xs font-medium uppercase tracking-wide text-muted">{text($locale, 'stock.methodology')}</p>
      <p class="mt-2 text-sm leading-6 text-ink">{methodMethodology(methodKey, $locale)}</p>
      <p class="mt-3 text-sm text-muted">
        {text($locale, 'stock.sourceLine', { source: methodSourceDetail(methodKey, method) })}
        {#if method?.version}
          · {text($locale, 'stock.version', { version: method.version })}
        {/if}
      </p>
    </Disclosure>
  </div>
</article>
