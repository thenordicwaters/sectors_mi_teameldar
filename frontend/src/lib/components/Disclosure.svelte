<script lang="ts">
  import type { Snippet } from 'svelte';

  let { label, children }: { label: string; children: Snippet } = $props();
</script>

<details class="disclosure">
  <summary>
    <span>{label}</span>
    <span class="disclosure-chevron" aria-hidden="true">↓</span>
  </summary>
  <div class="disclosure-body">
    {@render children()}
  </div>
</details>
