<div class="loading-wrap">
  <div class="spinner-lg"></div>
</div>

<style>
  .loading-wrap { display: flex; justify-content: center; padding: 60px 0; }
  .spinner-lg {
    width: 32px; height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--orange);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>