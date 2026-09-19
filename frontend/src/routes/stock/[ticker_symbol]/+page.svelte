<script lang="ts">
  let { params: route_parameters }: { params: { ticker_symbol: string } } = $props();
  const ticker_symbol = route_parameters.ticker_symbol;
</script>

<p class="p-3 text-sm text-neutral-600">
  Stock detail for <code>{ticker_symbol}</code>. API: <code>GET /api/stocks/{ticker_symbol}</code>.
</p>
