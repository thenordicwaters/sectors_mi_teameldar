<script lang="ts">
  let { title, detail = '' }: { title: string; detail?: string } = $props();
</script>

<div class="rounded-2xl border border-dashed border-line bg-white px-5 py-10 text-center">
  <p class="text-base font-medium text-ink">{title}</p>
  {#if detail}
    <p class="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{detail}</p>
  {/if}
</div>
