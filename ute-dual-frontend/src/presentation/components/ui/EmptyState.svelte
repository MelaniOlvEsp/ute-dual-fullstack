<script>
  export let message = 'No hay datos para mostrar.';
</script>

<div class="empty">
  <svg width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h12A2.25 2.25 0 0120.25 6v3.776" />
  </svg>
  <p>{message}</p>
</div>

<style>
  .empty {
    text-align: center; padding: 64px 16px; color: var(--text-disabled);
    font-size: 14px; display: flex; flex-direction: column; align-items: center; gap: 12px;
  }
</style>