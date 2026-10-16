<script>
  import { createEventDispatcher } from 'svelte'
  import { api } from '../../../composition/api.js'
  import LoadingSpinner from '../ui/LoadingSpinner.svelte'

  export let show = false
  export let mensajeId = null
  export let puedeMarcarLeido = false // true solo para coordinadores

  const dispatch = createEventDispatcher()

  let detalle = null
  let cargando = false
  let error = ''
  let respuestaTexto = ''
  let enviando = false
  let procesando = false

  const ETIQUETAS_AREA = { dual: 'Formación Dual' }

  // Cada vez que cambia el id (o se abre el modal), recarga el hilo
  $: if (show && mensajeId) cargarDetalle(mensajeId)

  async function cargarDetalle(id) {
    cargando = true
    error = ''
    try {
      detalle = await api.buzon.detalle(id)
    } catch (e) {
      error = e.message || 'No se pudo cargar el mensaje'
    } finally {
      cargando = false
    }
  }

  function cerrarModal() {
    show = false
    detalle = null
    respuestaTexto = ''
  }

  function handleOverlayKeydown(e) { if (e.key === 'Escape') cerrarModal() }

  async function enviarRespuesta() {
    const texto = respuestaTexto.trim()
    if (!texto) return
    enviando = true
    try {
      const nueva = await api.buzon.responder(mensajeId, texto)
      detalle = { ...detalle, respuestas: [...detalle.respuestas, nueva] }
      respuestaTexto = ''
      dispatch('cambio')
    } catch (e) {
      error = e.message || 'No se pudo enviar tu respuesta'
    } finally {
      enviando = false
    }
  }

  async function marcarLeido() {
    procesando = true
    try {
      await api.buzon.marcarLeido(mensajeId)
      detalle = { ...detalle, estado: 'Leido' }
      dispatch('cambio')
    } catch (e) {
      error = e.message || 'No se pudo marcar como leído'
    } finally {
      procesando = false
    }
  }

  async function cerrarMensaje() {
    procesando = true
    try {
      await api.buzon.cerrar(mensajeId)
      detalle = { ...detalle, estado: 'Cerrado' }
      dispatch('cambio')
    } catch (e) {
      error = e.message || 'No se pudo cerrar el mensaje'
    } finally {
      procesando = false
    }
  }

  function formatFecha(iso) {
    return new Date(iso).toLocaleString('es-MX', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    })
  }
</script>

{#if show}
  <button class="modal-overlay" on:click={cerrarModal} on:keydown={handleOverlayKeydown} aria-label="Cerrar modal">
    <div class="modal-card" on:click|stopPropagation role="dialog" aria-modal="true" aria-label="Detalle del mensaje">

      {#if cargando}
        <LoadingSpinner />
      {:else if error && !detalle}
        <div class="error-msg">{error}</div>
      {:else if detalle}
        <div class="modal-header">
          <div>
            <div class="modal-title">{detalle.asunto}</div>
            <div class="modal-subtitle">{ETIQUETAS_AREA[detalle.area] || detalle.area} · {formatFecha(detalle.created_at)}</div>
          </div>
          <span class="estado-badge estado-{detalle.estado.toLowerCase()}">{detalle.estado}</span>
        </div>

        <div class="hilo">
          <div class="hilo-item hilo-original">
            <p class="hilo-texto">{detalle.mensaje}</p>
          </div>
          {#each detalle.respuestas as r (r.id)}
            <div class="hilo-item">
              <div class="hilo-meta">
                <span class="hilo-autor">{r.autor_rol}</span>
                <span class="hilo-fecha">{formatFecha(r.created_at)}</span>
              </div>
              <p class="hilo-texto">{r.texto}</p>
            </div>
          {/each}
        </div>

        {#if error}<div class="error-msg">{error}</div>{/if}

        {#if detalle.estado !== 'Cerrado'}
          <div class="respuesta-box">
            <textarea
              class="input-plain respuesta-textarea"
              placeholder="Escribe tu respuesta…"
              maxlength="1000"
              bind:value={respuestaTexto}
              disabled={enviando}
            ></textarea>
            <button class="btn-primary" on:click={enviarRespuesta} disabled={enviando || !respuestaTexto.trim()}>
              {enviando ? 'Enviando…' : 'Responder'}
            </button>
          </div>
        {/if}

        <div class="modal-actions">
          {#if puedeMarcarLeido && detalle.estado === 'Enviado'}
            <button class="link-orange" on:click={marcarLeido} disabled={procesando}>Marcar como leído</button>
          {/if}
          {#if puedeMarcarLeido && detalle.estado !== 'Cerrado'}
            <button class="link-orange" on:click={cerrarMensaje} disabled={procesando}>Dar por resuelto</button>
          {/if}
        </div>
      {/if}

      <button class="modal-close" on:click={cerrarModal} aria-label="Cerrar">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>

    </div>
  </button>
{/if}

<style>
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; backdrop-filter: blur(2px); border: none; cursor: default; width: 100%; text-align: left; }
  .modal-card { background: var(--bg-card); border-radius: var(--radius-card); box-shadow: 0 8px 40px rgba(0,0,0,0.15); padding: 28px; width: 100%; max-width: 480px; max-height: 85vh; overflow-y: auto; position: relative; display: flex; flex-direction: column; gap: 18px; }

  .modal-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .modal-title { font-size: 16px; font-weight: 700; color: var(--text-primary); }
  .modal-subtitle { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

  .estado-badge { flex-shrink: 0; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; padding: 4px 10px; border-radius: 20px; }
  .estado-enviado { background: var(--orange-light); color: var(--orange); }
  .estado-leido { background: #EFF6FF; color: #2563EB; }
  .estado-cerrado { background: var(--bg-page); color: var(--text-secondary); }

  .hilo { display: flex; flex-direction: column; gap: 10px; }
  .hilo-item { background: var(--bg-page); border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; }
  .hilo-original { border: 1px solid var(--border); }
  .hilo-meta { display: flex; justify-content: space-between; gap: 8px; }
  .hilo-autor { font-size: 12px; font-weight: 700; color: var(--text-primary); }
  .hilo-fecha { font-size: 11px; color: var(--text-disabled); }
  .hilo-texto { font-size: 13.5px; line-height: 1.5; color: var(--text-primary); white-space: pre-wrap; word-break: break-word; }

  .respuesta-box { display: flex; flex-direction: column; gap: 10px; }
  .respuesta-textarea { resize: vertical; min-height: 70px; font-family: var(--font); line-height: 1.5; }

  .modal-actions { display: flex; justify-content: flex-end; gap: 16px; }

  .modal-close { position: absolute; top: 16px; right: 16px; background: var(--bg-page); border: none; border-radius: 8px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--text-secondary); transition: background 0.15s; }
  .modal-close:hover { background: var(--border); }
</style>