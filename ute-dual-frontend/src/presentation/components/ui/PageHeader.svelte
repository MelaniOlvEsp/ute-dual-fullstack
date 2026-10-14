<script>
  export let title = '';
  export let subtitle = '';
</script>

<div class="page-header">
  <h1 class="page-title">{title}</h1>
  {#if subtitle}
    <p class="page-sub">{subtitle}</p>
  {/if}
</div>

<style>
  .page-header { display: flex; flex-direction: column; gap: 4px; }
  .page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
  .page-sub { font-size: 14px; color: var(--text-secondary); }
</style>