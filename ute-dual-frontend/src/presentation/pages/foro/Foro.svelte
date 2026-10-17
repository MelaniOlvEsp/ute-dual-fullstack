<script>
  // src/routes/Foro.svelte
  import { onMount } from 'svelte'
  import { navigate } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated, user } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import LoadingSpinner from '../../components/ui/LoadingSpinner.svelte'
  import EmptyState from '../../components/ui/EmptyState.svelte'
  import BuzonDetalleModal from '../../components/foro/BuzonDetalleModal.svelte'

  import { REACTIONS as REACCIONES, MAILBOX_AREA } from '../../../domain/foro/messages.js'

  const MAX_CONTENIDO = 2000
  const MAX_MENSAJE_BUZON = 500

  let loading = true
  let loadError = false
  let tab = 'anuncios'

  // Permisos derivados del rol en sesión
  $: roles = $user?.roles || {}
  $: esAlumno = Boolean(roles.alumno)
  $: puedePublicar = Boolean(roles.tutor_academico || roles.coordinador_dual)
  $: puedeLeerDual = Boolean(roles.tutor_academico || roles.coordinador_dual)
  $: puedeLeerBuzon = puedeLeerDual
  $: mostrarTabBuzon = esAlumno || puedeLeerBuzon

  // Anuncios
  let publicaciones = []
  let nuevoContenido = ''
  let publicando = false
  let errorPublicar = ''

  // Buzón: enviar (alumno)
  let buzonAsunto = ''
  let buzonMensaje = ''
  let enviandoBuzon = false
  // C09 (D1): hilo cerrado que el alumno continúa en un hilo nuevo enlazado.
  let hiloAnterior = null
  let errorBuzon = ''
  let exitoBuzon = ''

  // Buzón: bandeja recibida (coordinadores / admin)
  const areaBandeja = MAILBOX_AREA
  let mensajesBandeja = []
  let cargandoBandeja = false
  let errorBandeja = ''
  let bandejaCargada = false

  // Buzón: mis mensajes del alumno
  let mensajesMios = []
  let cargandoMios = false
  let errorMios = ''
  let miosCargados = false

  // Buzón: modal de detalle e hilo (alumno y coordinadores)
  let mensajeSeleccionadoId = null
  let showDetalleBuzon = false

  onMount(async () => {
    if (!get(isAuthenticated)) {
      navigate('/login', { replace: true })
      return
    }


    try {
      publicaciones = await api.foro.listar()
    } catch (e) {
      loadError = true
    } finally {
      loading = false
    }
  })

  async function publicar() {
    const contenido = nuevoContenido.trim()
    if (!contenido) return
    publicando = true
    errorPublicar = ''
    try {
      const nueva = await api.foro.crear(contenido)
      publicaciones = [nueva, ...publicaciones]
      nuevoContenido = ''
    } catch (e) {
      errorPublicar = e.message || 'No se pudo publicar el aviso'
    } finally {
      publicando = false
    }
  }

  async function eliminarPublicacion(pub) {
    if (!confirm('¿Eliminar este anuncio? Dejará de mostrarse a todos; el registro se conserva.')) return
    try {
      await api.foro.eliminar(pub.id)
      publicaciones = publicaciones.filter(p => p.id !== pub.id)
    } catch (e) {
      alert(e.message || 'No se pudo eliminar la publicación')
    }
  }

  // Reacción con actualización optimista: toca el mismo emoji → se quita,
  // toca otro → lo reemplaza. Si el servidor falla, se revierte.
  async function reaccionar(pub, tipo) {
    if (!esAlumno) return
    const anterior = pub.mi_reaccion
    const reaccionesPrev = { ...pub.reacciones }

    const nuevasReacciones = { ...pub.reacciones }
    if (anterior) nuevasReacciones[anterior] = Math.max(0, (nuevasReacciones[anterior] || 1) - 1)
    const nuevaMia = anterior === tipo ? null : tipo
    if (nuevaMia) nuevasReacciones[tipo] = (nuevasReacciones[tipo] || 0) + 1

    const totalNuevo = Object.values(nuevasReacciones).reduce((a, b) => a + b, 0)
    publicaciones = publicaciones.map(p => p.id === pub.id
      ? { ...p, reacciones: nuevasReacciones, mi_reaccion: nuevaMia, total_reacciones: totalNuevo }
      : p)

    try {
      await api.foro.reaccionar(pub.id, tipo)
    } catch (e) {
      const totalPrev = Object.values(reaccionesPrev).reduce((a, b) => a + b, 0)
      publicaciones = publicaciones.map(p => p.id === pub.id
        ? { ...p, reacciones: reaccionesPrev, mi_reaccion: anterior, total_reacciones: totalPrev }
        : p)
    }
  }

  async function enviarBuzon() {
    errorBuzon = ''
    exitoBuzon = ''
    if (buzonAsunto.trim().length < 3) { errorBuzon = 'Escribe un asunto un poco más descriptivo'; return }
    if (!buzonMensaje.trim()) { errorBuzon = 'Escribe tu mensaje'; return }

    enviandoBuzon = true
    try {
      await api.buzon.enviar({
        area: MAILBOX_AREA,
        asunto: buzonAsunto.trim(),
        mensaje: buzonMensaje.trim(),
        ...(hiloAnterior ? { hilo_anterior_id: hiloAnterior.id } : {})
      })
      hiloAnterior = null
      exitoBuzon = 'Tu mensaje fue enviado a Formación Dual.'
      buzonAsunto = ''
      buzonMensaje = ''
    } catch (e) {
      errorBuzon = e.message || 'No se pudo enviar tu mensaje'
    } finally {
      enviandoBuzon = false
    }
  }

  async function cargarBandeja() {
    cargandoBandeja = true
    errorBandeja = ''
    try {
      mensajesBandeja = await api.buzon.listar(areaBandeja)
      bandejaCargada = true
    } catch (e) {
      errorBandeja = e.message || 'No se pudo cargar el buzón'
    } finally {
      cargandoBandeja = false
    }
  }

  async function cargarMios() {
    cargandoMios = true
    errorMios = ''
    try {
      mensajesMios = await api.buzon.mios()
      miosCargados = true
    } catch (e) {
      errorMios = e.message || 'No se pudieron cargar tus mensajes'
    } finally {
      cargandoMios = false
    }
  }

  function iniciarHiloNuevo(evento) {
    hiloAnterior = evento.detail
    buzonAsunto = `Seguimiento: ${evento.detail.asunto}`.slice(0, 150)
    cambiarTab('buzon')
  }

  function abrirDetalle(msg) {
    mensajeSeleccionadoId = msg.id
    showDetalleBuzon = true
  }

  // Se dispara desde el modal cuando responden, marcan leído o cierran;
  // recarga la(s) lista(s) visibles para que el estado quede al día
  function refrescarBuzon() {
    if (esAlumno) cargarMios()
    if (puedeLeerBuzon) cargarBandeja()
  }

  function cambiarTab(nuevo) {
    tab = nuevo
    if (nuevo === 'buzon' && puedeLeerBuzon && !bandejaCargada) {
      cargarBandeja()
    }
    if (nuevo === 'buzon' && esAlumno && !miosCargados) {
      cargarMios()
    }
  }

  function formatFecha(iso) {
    const fecha = new Date(iso)
    const diffMin = Math.floor((Date.now() - fecha.getTime()) / 60000)
    if (diffMin < 1) return 'justo ahora'
    if (diffMin < 60) return `hace ${diffMin} min`
    const diffHrs = Math.floor(diffMin / 60)
    if (diffHrs < 24) return `hace ${diffHrs} h`
    const diffDias = Math.floor(diffHrs / 24)
    if (diffDias < 7) return `hace ${diffDias} d`
    return fecha.toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' })
  }

  function iniciales(nombre) {
    if (!nombre) return 'UT'
    const partes = nombre.trim().split(/\s+/)
    return ((partes[0]?.[0] || '') + (partes[1]?.[0] || '')).toUpperCase()
  }

  function reaccionesActivas(pub) {
    return REACCIONES.filter(r => (pub.reacciones?.[r.tipo] || 0) > 0)
  }

  // Texto corto para el badge de estado en las listas (el detalle
  // completo ya se ve al abrir el modal)
  function labelEstado(estado) {
    if (estado === 'Enviado') return 'Nuevo'
    if (estado === 'Leido') return 'Visto'
    return 'Resuelto'
  }
</script>

<svelte:head>
  <title>Foro | Portal UTE</title>
</svelte:head>

<Navbar />

<main class="main">
  {#if loading}
    <div class="loading-wrap">
      <LoadingSpinner />
      <p class="loading-text">Cargando foro...</p>
    </div>
  {:else if loadError}
    <div class="content">
      <h1 class="page-title">Foro</h1>
      <div class="placeholder-card">
        <img src="/ours.png" alt="OURS" class="logo-ours" />
        <p class="placeholder-text">No se pudo cargar el foro</p>
      </div>
    </div>
  {:else}
    <div class="content">
      <div class="forum-hero">
        <h1 class="page-title">Foro</h1>
        <p class="hero-sub">Avisos de la comunidad UTE y tu buzón de mensajes</p>
      </div>

      {#if mostrarTabBuzon}
        <div class="tabs">
          <button class="tab-btn" class:active={tab === 'anuncios'} on:click={() => cambiarTab('anuncios')}>
            Anuncios
          </button>
          <button class="tab-btn" class:active={tab === 'buzon'} on:click={() => cambiarTab('buzon')}>
            Buzón
          </button>
        </div>
      {/if}

      {#if tab === 'anuncios'}
        {#if puedePublicar}
          <div class="composer-card">
            <textarea
              class="input-plain composer-textarea"
              placeholder="Escribe un aviso para la comunidad… 📢"
              maxlength={MAX_CONTENIDO}
              bind:value={nuevoContenido}
              disabled={publicando}
            ></textarea>
            <div class="composer-footer">
              <span class="char-counter">{nuevoContenido.length}/{MAX_CONTENIDO}</span>
              <button
                class="btn-primary composer-btn"
                on:click={publicar}
                disabled={publicando || !nuevoContenido.trim()}
              >
                {publicando ? 'Publicando…' : 'Publicar aviso'}
              </button>
            </div>
            {#if errorPublicar}<div class="error-msg">{errorPublicar}</div>{/if}
          </div>
        {/if}

        {#if publicaciones.length === 0}
          <EmptyState message="Todavía no hay avisos en el foro." />
        {:else}
          <div class="feed">
            {#each publicaciones as pub (pub.id)}
              <article class="post-card">
                <div class="post-header">
                  <div class="post-avatar">{iniciales(pub.autor_nombre)}</div>
                  <div class="post-meta">
                    <span class="post-autor">{pub.autor_nombre}</span>
                    <span class="post-rol">{pub.autor_rol} · {formatFecha(pub.created_at)}</span>
                  </div>
                  {#if puedePublicar && (pub.autor_id === $user?.id || roles.coordinador_dual)}
                    <button class="post-delete" title={pub.autor_id === $user?.id ? 'Eliminar publicación' : 'Eliminar publicación (moderación)'} aria-label="Eliminar publicación" on:click={() => eliminarPublicacion(pub)}>
                      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"/>
                      </svg>
                    </button>
                  {/if}
                </div>

                <p class="post-content">{pub.contenido}</p>

                <div class="post-reactions">
                  {#if esAlumno}
                    <div class="reaction-picker">
                      {#each REACCIONES as r}
                        <button
                          class="reaction-btn"
                          class:active={pub.mi_reaccion === r.tipo}
                          title={r.label}
                          on:click={() => reaccionar(pub, r.tipo)}
                        >
                          <span class="reaction-emoji">{r.emoji}</span>
                          {#if pub.reacciones?.[r.tipo]}
                            <span class="reaction-count">{pub.reacciones[r.tipo]}</span>
                          {/if}
                        </button>
                      {/each}
                    </div>
                  {:else if pub.total_reacciones > 0}
                    <div class="reaction-summary">
                      {#each reaccionesActivas(pub) as r}
                        <span class="reaction-chip">{r.emoji} {pub.reacciones[r.tipo]}</span>
                      {/each}
                    </div>
                  {:else}
                    <span class="reaction-empty">Sin reacciones todavía</span>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        {/if}
      {:else if tab === 'buzon'}
        <div class="buzon-grid">
          {#if esAlumno}
            <div class="buzon-card">
              <h2 class="section-title">Enviar un mensaje</h2>
              <p class="buzon-hint">Escribe tu duda o comentario al equipo de Formación Dual.</p>

              <div class="input-group">
                <label for="correo-buzon">Tu correo</label>
                <input id="correo-buzon" class="input-plain" type="email" value={$user?.email || ''} disabled />
              </div>

              {#if hiloAnterior}
                <p class="hilo-enlazado" role="status">Continúas el hilo cerrado «{hiloAnterior.asunto}».
                  <button type="button" class="link-quitar" on:click={() => { hiloAnterior = null }}>Quitar enlace</button></p>
              {/if}

              <div class="input-group">
                <label for="asunto-buzon">Asunto</label>
                <input
                  id="asunto-buzon"
                  class="input-plain"
                  type="text"
                  maxlength="150"
                  placeholder="Ej. Duda sobre mi reporte semanal"
                  bind:value={buzonAsunto}
                />
              </div>

              <div class="input-group">
                <label for="mensaje-buzon">Mensaje</label>
                <textarea
                  id="mensaje-buzon"
                  class="input-plain buzon-textarea"
                  maxlength={MAX_MENSAJE_BUZON}
                  placeholder="Cuéntanos qué necesitas…"
                  bind:value={buzonMensaje}
                ></textarea>
                <span class="char-counter">{buzonMensaje.length}/{MAX_MENSAJE_BUZON}</span>
              </div>

              {#if errorBuzon}<div class="error-msg">{errorBuzon}</div>{/if}
              {#if exitoBuzon}<div class="success-msg">{exitoBuzon}</div>{/if}

              <button class="btn-primary" on:click={enviarBuzon} disabled={enviandoBuzon}>
                {enviandoBuzon ? 'Enviando…' : 'Enviar mensaje'}
              </button>
            </div>
          {/if}

          {#if puedeLeerBuzon}
            <div class="buzon-card">
              <h2 class="section-title">Bandeja recibida</h2>

              {#if cargandoBandeja}
                <LoadingSpinner />
              {:else if errorBandeja}
                <div class="error-msg">{errorBandeja}</div>
              {:else if mensajesBandeja.length === 0}
                <EmptyState message="No hay mensajes en esta bandeja." />
              {:else}
                <div class="mensajes-list">
                  {#each mensajesBandeja as msg (msg.id)}
                    <button class="mensaje-card" class:no-leido={msg.estado === 'Enviado'} on:click={() => abrirDetalle(msg)}>
                      <div class="mensaje-header">
                        <span class="mensaje-asunto">{msg.asunto}</span>
                        {#if msg.estado !== 'Cerrado'}<span class="mensaje-badge">{labelEstado(msg.estado)}</span>{/if}
                      </div>
                      <span class="mensaje-correo">{msg.correo} · {formatFecha(msg.created_at)}</span>
                      <p class="mensaje-texto">{msg.mensaje}</p>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          {#if esAlumno}
            <div class="buzon-card">
              <h2 class="section-title">Mis mensajes</h2>

              {#if cargandoMios}
                <LoadingSpinner />
              {:else if errorMios}
                <div class="error-msg">{errorMios}</div>
              {:else if mensajesMios.length === 0}
                <EmptyState message="Todavía no has enviado mensajes al buzón." />
              {:else}
                <div class="mensajes-list">
                  {#each mensajesMios as msg (msg.id)}
                    <button class="mensaje-card" on:click={() => abrirDetalle(msg)}>
                      <div class="mensaje-header">
                        <span class="mensaje-asunto">{msg.asunto}</span>
                        <span class="mensaje-badge">{labelEstado(msg.estado)}</span>
                      </div>
                      <span class="mensaje-correo">{formatFecha(msg.created_at)}</span>
                      <p class="mensaje-texto">{msg.mensaje}</p>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</main>

<BuzonDetalleModal
  bind:show={showDetalleBuzon}
  mensajeId={mensajeSeleccionadoId}
  puedeMarcarLeido={puedeLeerBuzon}
  on:cambio={refrescarBuzon}
  on:nuevohilo={iniciarHiloNuevo}
/>

<style>
  .main {
    padding-top: 56px;
    min-height: 100vh;
    background: var(--bg-page);
  }

  .loading-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: calc(100vh - 56px);
    gap: 16px;
  }
  .loading-text {
    font-size: 14px;
    color: var(--text-secondary);
  }

  .content {
    max-width: 900px;
    margin: 0 auto;
    padding: 36px 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .forum-hero {
    background: var(--bg-card);
    border-radius: var(--radius-card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card);
    padding: 24px 28px;
  }
  .page-title {
    font-size: 26px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }
  .hero-sub {
    font-size: 14px;
    color: var(--text-secondary);
    margin-top: 4px;
  }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 6px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 5px;
    width: fit-content;
  }
  .tabs-small {
    margin-bottom: 14px;
  }
  .tab-btn {
    padding: 9px 18px;
    border: none;
    background: transparent;
    border-radius: 8px;
    font-family: var(--font);
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .tab-btn:hover { color: var(--text-primary); }
  .tab-btn.active { background: var(--orange); color: #fff; }

  /* Composer */
  .composer-card {
    background: var(--bg-card);
    border-radius: var(--radius-card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .composer-textarea {
    resize: vertical;
    min-height: 90px;
    font-family: var(--font);
    line-height: 1.5;
  }
  .composer-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .composer-btn { width: auto; padding: 10px 22px; }
  .char-counter {
    font-size: 12px;
    color: var(--text-disabled);
    font-weight: 600;
  }

  /* Feed */
  .feed {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .post-card {
    background: var(--bg-card);
    border-radius: var(--radius-card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card);
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .post-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .post-avatar {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--orange-light);
    color: var(--orange);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
  }
  .post-meta {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
  }
  .post-autor {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
  }
  .post-rol {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .post-delete {
    flex-shrink: 0;
    background: none;
    border: none;
    color: var(--text-disabled);
    cursor: pointer;
    padding: 6px;
    border-radius: 8px;
    transition: background 0.15s, color 0.15s;
  }
  .post-delete:hover { background: #FEF2F2; color: var(--error); }
  .post-content {
    font-size: 14.5px;
    line-height: 1.6;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-word;
  }

  /* Reacciones */
  .post-reactions {
    border-top: 1px solid var(--border);
    padding-top: 10px;
  }
  .reaction-picker {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .reaction-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 6px 10px;
    border-radius: 20px;
    border: 1.5px solid var(--border);
    background: var(--bg-page);
    cursor: pointer;
    font-family: var(--font);
    transition: all 0.15s ease;
  }
  .reaction-btn:hover {
    border-color: var(--orange-mid);
    transform: translateY(-1px);
  }
  .reaction-btn.active {
    background: var(--orange-light);
    border-color: var(--orange);
  }
  .reaction-emoji { font-size: 16px; line-height: 1; }
  .reaction-count {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-secondary);
  }
  .reaction-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .reaction-chip {
    font-size: 13px;
    background: var(--bg-page);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 10px;
    color: var(--text-secondary);
  }
  .reaction-empty {
    font-size: 12px;
    color: var(--text-disabled);
  }

  /* Buzón */
  .buzon-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
    align-items: start;
  }
  .buzon-card {
    background: var(--bg-card);
    border-radius: var(--radius-card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card);
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .section-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
  }
  .hilo-enlazado { margin: 0 0 8px; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-left: 3px solid var(--orange); border-radius: 8px; background: var(--bg-page); color: var(--text-primary); }
  .link-quitar { background: none; border: none; padding: 0; margin-left: 6px; color: var(--orange); font: inherit; font-weight: 600; cursor: pointer; text-decoration: underline; }
  .buzon-hint {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: -8px;
  }
  .buzon-textarea {
    resize: vertical;
    min-height: 110px;
    font-family: var(--font);
    line-height: 1.5;
  }
  .success-msg {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    color: var(--success);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
  }
  :global([data-theme="dark"]) .success-msg {
    background: #0F2A1A;
    border-color: #1C4A2E;
  }

  /* Bandeja */
  .mensajes-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 520px;
    overflow-y: auto;
  }
  .mensaje-card {
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: var(--bg-page);
    width: 100%;
    text-align: left;
    cursor: pointer;
    font-family: var(--font);
    transition: border-color 0.15s;
  }
  .mensaje-card:hover { border-color: var(--orange-mid); }
  .mensaje-card.no-leido {
    border-color: var(--orange-mid);
    background: var(--orange-light);
  }
  .mensaje-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .mensaje-asunto {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
  }
  .mensaje-badge {
    flex-shrink: 0;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: var(--orange);
    color: #fff;
    padding: 3px 8px;
    border-radius: 20px;
  }
  .mensaje-correo {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .mensaje-texto {
    font-size: 13.5px;
    color: var(--text-primary);
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }
  /* Placeholder (error) */
  .placeholder-card {
    background: var(--bg-card);
    border-radius: var(--radius-card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card);
    padding: 80px 28px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 20px;
  }
  .logo-ours { height: 100px; width: auto; object-fit: contain; }
  .placeholder-text {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-disabled);
    letter-spacing: 0.02em;
  }

  @media (max-width: 768px) {
    .content { padding: 24px 16px; }
    .forum-hero { padding: 20px; }
    .page-title { font-size: 22px; }
    .buzon-grid { grid-template-columns: 1fr; }
    .placeholder-card { padding: 60px 20px; }
    .logo-ours { height: 80px; }
    .placeholder-text { font-size: 18px; }
  }
</style>
