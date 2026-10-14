<script>
  // Visor PDF embebido — fetch con Authorization header,
  // blob URL local para evitar 401 del navegador
  import { onDestroy } from 'svelte'
  import { get } from 'svelte/store'
  import { token, logout as authLogout } from '../../stores/auth.js'

  export let url = ''
  export let titulo = 'Documento PDF'

  let blobUrl = ''
  let loading = false
  let error = ''
  let _abort = null

  async function cargarPDF() {
    // Abort fetch previo para evitar race condition
    // (cambio rápido de documento → PDF correcto, no stale)
    if (_abort) _abort.abort()
    if (blobUrl) {
      URL.revokeObjectURL(blobUrl)
      blobUrl = ''
    }
    if (!url) return

    loading = true
    error = ''

    const controller = new AbortController()
    _abort = controller

    try {
      const jwt = get(token)
      const headers = {}
      if (jwt) headers['Authorization'] = `Bearer ${jwt}`

      const res = await fetch(url, { headers, signal: controller.signal })

      if (res.status === 401) {
        authLogout()
        window.location.href = '/login'
        return
      }

      if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`)
      }
      const blob = await res.blob()
      if (controller.signal.aborted) return
      blobUrl = URL.createObjectURL(blob)
    } catch (e) {
      if (e.name === 'AbortError') return
      error = 'No se pudo cargar el PDF. Verifica tu sesión.'
    } finally {
      loading = false
    }
  }

  // Reactivo: recargar cuando cambia la URL
  $: if (url) cargarPDF()

  onDestroy(() => {
    if (_abort) _abort.abort()
    if (blobUrl) URL.revokeObjectURL(blobUrl)
  })
</script>

{#if url}
  <div class="visor-wrap">
    <div class="visor-header">
      <span class="visor-title">{titulo}</span>
      {#if blobUrl}
        <a href={blobUrl} target="_blank" rel="noopener noreferrer" class="visor-external">Abrir en pestaña nueva ↗</a>
      {/if}
    </div>

    {#if loading}
      <div class="visor-status">Cargando PDF…</div>
    {:else if error}
      <div class="visor-status visor-error">{error}</div>
    {:else if blobUrl}
      <embed src={blobUrl} type="application/pdf" class="visor-embed" />
    {:else}
      <div class="visor-status">No se pudo cargar el documento.</div>
    {/if}
  </div>
{:else}
  <div class="visor-wrap visor-empty">
    <p class="visor-empty-text">No hay PDF disponible</p>
  </div>
{/if}

<style>
  .visor-wrap {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border);
    border-radius: var(--radius-card);
    overflow: hidden;
    background: #1e293b;
    width: 100%;
    height: 100%;
    min-height: 80vh;
  }
  @media (min-width: 768px) {
    .visor-wrap {
      min-height: 90vh;
    }
  }
  .visor-empty {
    background: var(--bg-page);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .visor-empty-text {
    color: var(--text-disabled);
    font-size: 14px;
    font-style: italic;
  }
  .visor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: var(--bg-page);
    border-bottom: 1px solid var(--border);
  }
  .visor-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-disabled);
  }
  .visor-external {
    font-size: 12px;
    font-weight: 500;
    color: var(--orange);
    text-decoration: none;
    transition: color 0.15s;
  }
  .visor-external:hover {
    color: var(--orange-hover);
    text-decoration: underline;
  }
  .visor-embed {
    flex: 1;
    width: 100%;
    border: none;
    background: #fff;
  }
  .visor-status {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 14px;
    padding: 40px;
    text-align: center;
  }
  .visor-error {
    color: var(--error, #dc2626);
  }
</style>
