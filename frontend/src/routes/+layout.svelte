<script lang="ts">
  import '../app.css';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { initLocale, locale, setLocale, text, type Locale } from '$lib/i18n';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();

  const navigationLinks = [
    { path: '/', label: 'nav.discover' },
    { path: '/unusual', label: 'nav.unusual' },
    { path: '/compare', label: 'nav.compare' }
  ] as const;

  function isCurrent(path: string, pathname: string): boolean {
    if (path === '/') return pathname === '/';
    return pathname === path || pathname.startsWith(`${path}/`);
  }

  function chooseLocale(next: Locale) {
    setLocale(next);
  }

  onMount(() => {
    initLocale();
  });

  $effect(() => {
    if (browser) document.documentElement.lang = $locale === 'id' ? 'id' : 'en';
  });
</script>

<svelte:head>
  <title>Eldar Market Intelligence</title>
</svelte:head>

<div class="min-h-screen bg-paper text-ink">
  <header class="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
    <nav class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
      <a href="/" class="shrink-0 font-serif text-lg tracking-tight">IDX</a>
      <div class="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        {#each navigationLinks as navigationLink}
          <a
            href={navigationLink.path}
            class={isCurrent(navigationLink.path, $page.url.pathname)
              ? 'font-semibold text-ink'
              : 'text-muted hover:text-ink'}
            aria-current={isCurrent(navigationLink.path, $page.url.pathname) ? 'page' : undefined}
          >
            {text($locale, navigationLink.label)}
          </a>
        {/each}
      </div>
      <div class="ml-auto flex rounded-full border border-line bg-white p-0.5 text-xs font-semibold" role="group" aria-label={text($locale, 'lang.switch')}>
        <button
          class={$locale === 'en' ? 'rounded-full bg-ink px-2.5 py-1 text-paper' : 'px-2.5 py-1 text-muted'}
          type="button"
          aria-pressed={$locale === 'en'}
          onclick={() => chooseLocale('en')}
        >
          EN
        </button>
        <button
          class={$locale === 'id' ? 'rounded-full bg-ink px-2.5 py-1 text-paper' : 'px-2.5 py-1 text-muted'}
          type="button"
          aria-pressed={$locale === 'id'}
          onclick={() => chooseLocale('id')}
        >
          ID
        </button>
      </div>
    </nav>
  </header>
  <main class="mx-auto max-w-6xl px-4 py-8">
    {@render children()}
  </main>
  <footer class="mx-auto max-w-6xl space-y-1 px-4 pb-10 text-xs leading-5 text-muted">
    <p>{text($locale, 'footer.sources')}</p>
    <p>{text($locale, 'footer.disclaimer')}</p>
  </footer>
</div>
