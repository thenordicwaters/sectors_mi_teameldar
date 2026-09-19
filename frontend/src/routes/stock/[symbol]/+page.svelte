<script lang="ts">
  let { params }: { params: { symbol: string } } = $props();
</script>

<p class="p-3 text-sm text-neutral-600">
  Stock detail for <code>{params.symbol}</code>. API: <code>GET /api/stocks/{params.symbol}</code>.
</p>
