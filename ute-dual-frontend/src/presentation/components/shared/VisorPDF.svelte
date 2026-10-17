<script>
  // Visor de PDF (C08, AC-20): carga autenticada con el encabezado Authorization y URL temporal de
  // objeto (nunca el token en la URL), liberada al cambiar o cerrar. Visor nativo del navegador sin
  // dependencias; «Abrir en pestaña nueva» y «Descargar» siempre visibles; si falla, el error es
  // visible con «Reintentar»; en pantallas táctiles estrechas (donde el visor nativo es poco fiable)
  // el PDF se ofrece primero como acción de abrir o descargar y se puede mostrar aquí a demanda.
  import { onDestroy } from 'svelte'
  import { get } from 'svelte/store'
  import { token, logout as authLogout } from '../../stores/auth.js'

  export let url = ''
  export let titulo = 'Documento PDF'
  export let nombreDescarga = 'documento.pdf'

  const esMovil = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    && window.matchMedia('(max-width: 767px) and (pointer: coarse)').matches

  let blobUrl = ''
  let loading = false
  let error = ''
  let mostrarAqui = !esMovil
  let _abort = null
  let _url = ''

  async function cargarPDF() {
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
        const detalle = await res.json().then(d => d?.detail).catch(() => null)
        error = typeof detalle === 'string' ? detalle : `No se pudo cargar el PDF (error ${res.status}).`
        return
      }
      const blob = await res.blob()
      if (controller.signal.aborted) return
      blobUrl = URL.createObjectURL(blob)
    } catch (e) {
      if (e.name === 'AbortError') return
      error = 'No se pudo cargar el PDF. Revisa tu conexión y tu sesión.'
    } finally {
      if (_abort === controller) loading = false
    }
  }

  // Recarga solo cuando cambia la URL (documento distinto), no en cada refresco de la página.
  $: if (url !== _url) {
    _url = url
    cargarPDF()
  }

  onDestroy(() => {
    if (_abort) _abort.abort()
    if (blobUrl) URL.revokeObjectURL(blobUrl)
  })
</script>

{#if url}
  <div class="visor-wrap">
    <div class="visor-header">
      <span class="visor-title">{titulo}</span>
      <span class="visor-acciones">
        {#if blobUrl}
          <a href={blobUrl} target="_blank" rel="noopener noreferrer" class="visor-accion">Abrir en pestaña nueva ↗</a>
          <a href={blobUrl} download={nombreDescarga} class="visor-accion">Descargar</a>
        {/if}
      </span>
    </div>

    {#if loading}
      <div class="visor-status" role="status">Cargando PDF…</div>
    {:else if error}
      <div class="visor-status visor-error" role="alert">
        <p>{error}</p>
        <button type="button" class="visor-reintentar" on:click={cargarPDF}>Reintentar</button>
      </div>
    {:else if blobUrl && mostrarAqui}
      <embed src={blobUrl} type="application/pdf" class="visor-embed" title={titulo} />
    {:else if blobUrl}
      <div class="visor-status" role="status">
        <p>Tu navegador puede no mostrar el PDF en esta pantalla. Ábrelo en una pestaña nueva o descárgalo.</p>
        <button type="button" class="visor-reintentar" on:click={() => mostrarAqui = true}>Intentar mostrarlo aquí</button>
      </div>
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
    min-height: 60vh;
  }
  @media (min-width: 768px) {
    .visor-wrap { min-height: 80vh; }
  }
  .visor-empty {
    background: var(--bg-page);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .visor-empty-text { color: var(--text-disabled); font-size: 14px; font-style: italic; }
  .visor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
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
  .visor-acciones { display: flex; gap: 14px; flex-wrap: wrap; }
  .visor-accion {
    font-size: 12px;
    font-weight: 600;
    color: var(--orange);
    text-decoration: none;
  }
  .visor-accion:hover { color: var(--orange-hover); text-decoration: underline; }
  .visor-accion:focus-visible, .visor-reintentar:focus-visible { outline: 2px solid var(--orange); outline-offset: 2px; }
  .visor-embed { flex: 1; width: 100%; border: none; background: #fff; }
  .visor-status {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    align-items: center;
    justify-content: center;
    color: #cbd5e1;
    font-size: 14px;
    padding: 40px 24px;
    text-align: center;
  }
  .visor-status p { margin: 0; max-width: 42ch; }
  .visor-error { color: #fca5a5; }
  .visor-reintentar {
    background: transparent;
    border: 1.5px solid currentColor;
    color: inherit;
    border-radius: 8px;
    padding: 8px 16px;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
</style>
