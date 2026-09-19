<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();

  const navigation_links = [
    { path: '/', label: 'Screener' },
    { path: '/unusual', label: 'Unusual Activity' },
    { path: '/compare', label: 'Compare' }
  ];
</script>

<div class="min-h-screen bg-white text-neutral-900">
  <header class="border-b border-neutral-200">
    <nav class="flex items-center gap-4 px-3 py-2 text-sm">
      <span class="font-semibold tracking-tight">IDX Screener</span>
      {#each navigation_links as navigation_link}
        <a
          href={navigation_link.path}
          class={$page.url.pathname === navigation_link.path
            ? 'font-medium underline'
            : 'text-neutral-600 hover:text-neutral-900'}
        >
          {navigation_link.label}
        </a>
      {/each}
    </nav>
  </header>
  <main>
    {@render children()}
  </main>
  <footer class="border-t border-neutral-200 px-3 py-2 text-xs text-neutral-500">
    Information and analysis only. Not investment advice.
  </footer>
</div>
