<script>
  // Reportes Dual del alumno (C05): entrega y reenvío por obligación semanal, con versiones.
  import { onMount } from 'svelte'
  import { navigate } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated, isAlumnoDual } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import { validateReportFile, MAX_PDF_BYTES } from '../../../domain/dual/report.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'
  import LoadingSpinner from '../../components/ui/LoadingSpinner.svelte'
  import { formatFecha, formatFechaCivil } from '../../utils/formatters.js'

  const ETIQUETA_ENTREGA = { Pendiente: 'Pendiente de revisión', Rechazada: 'Rechazada', Aprobada: 'Aprobada' }

  const PLANTILLAS = [
    { label: 'Plantilla Word',  ext: 'DOCX', color: '#2B579A', url: '/plantillas/plantilla_word.docx', filename: 'Plantilla_Semanal_Dual.docx' },
    { label: 'Plantilla Excel', ext: 'XLSX', color: '#217346', url: '/plantillas/plantilla_excel.xlsx', filename: 'Plantilla_Asistencia_Dual.xlsx' },
    { label: 'Plantilla PDF',   ext: 'PDF',  color: '#DC2626', url: '/plantillas/plantilla_pdf.pdf',  filename: 'Guia_Reporte_Dual.pdf' }
  ]

  let obligaciones = []
  let loading = true
  let error = ''

  // Formulario de entrega: una obligación a la vez.
  let seleccion = null
  let calificacion = ''
  let fechaInicio = ''
  let fechaFin = ''
  let archivo = null
  let errorForm = ''
  let enviando = false
  let aviso = ''

  // Versiones cargadas por reporte.
  let versiones = {}
  let versionesAbiertas = {}
  let errorVersiones = ''

  onMount(async () => {
    if (!get(isAuthenticated)) {
      navigate('/login', { replace: true })
      return
    }
    if (!get(isAlumnoDual)) {
      navigate('/foro', { replace: true })
      return
    }
    await cargarDatos()
  })

  async function cargarDatos() {
    error = ''
    try {
      obligaciones = await api.dual.misObligaciones()
    } catch (e) {
      obligaciones = []
      error = e.message || 'No se pudieron cargar tus semanas.'
    } finally {
      loading = false
    }
  }

  function abrirForm(o) {
    seleccion = o.id
    calificacion = ''
    fechaInicio = o.inicio_efectivo
    fechaFin = o.fin_efectivo
    archivo = null
    errorForm = ''
    aviso = ''
  }

  function cerrarForm() {
    seleccion = null
    errorForm = ''
  }

  function onArchivo(e) {
    const file = e.target.files[0]
    if (!file) return
    try {
      validateReportFile(file)
    } catch (err) {
      errorForm = err.message
      archivo = null
      e.target.value = ''
      return
    }
    errorForm = ''
    archivo = file
  }

  async function enviar(o) {
    errorForm = ''
    enviando = true
    try {
      const resultado = await api.dual.submitDelivery(o.id, {
        grade: calificacion,
        startDate: fechaInicio,
        endDate: fechaFin,
        file: archivo
      })
      aviso = resultado.repetido
        ? `Semana ${o.ordinal}: la entrega ya estaba registrada.`
        : `Semana ${o.ordinal}: reporte recibido (versión ${resultado.version}).`
      seleccion = null
      archivo = null
      delete versiones[resultado.reporte_id]
      versionesAbiertas = { ...versionesAbiertas, [resultado.reporte_id]: false }
      await cargarDatos()
    } catch (e) {
      errorForm = e.message || 'No se pudo enviar el reporte.'
    } finally {
      enviando = false
    }
  }

  async function alternarVersiones(o) {
    const abierta = !versionesAbiertas[o.reporte_id]
    versionesAbiertas = { ...versionesAbiertas, [o.reporte_id]: abierta }
    errorVersiones = ''
    if (abierta && !versiones[o.reporte_id]) {
      try {
        versiones = { ...versiones, [o.reporte_id]: await api.dual.versionesReporte(o.reporte_id) }
      } catch (e) {
        errorVersiones = e.message || 'No se pudo cargar el historial.'
        versionesAbiertas = { ...versionesAbiertas, [o.reporte_id]: false }
      }
    }
  }

  async function descargar(o, v, documento = 'original') {
    errorVersiones = ''
    try {
      await api.dual.downloadVersion(o.reporte_id, v.numero, `Semana ${o.ordinal}`, documento)
    } catch (e) {
      errorVersiones = e.message || 'No se pudo descargar la versión.'
    }
  }

  const limiteMb = MAX_PDF_BYTES / (1024 * 1024)
</script>

<svelte:head>
  <title>Mis reportes | Portal UTE</title>
</svelte:head>

<Navbar />

<div style="padding-top: 56px;">
  <div class="page">

    {#if loading}
      <LoadingSpinner />
    {:else}

      <PageHeader title="Reportes Dual" />

      <div class="card">
        <h2 class="card-title">Plantillas Oficiales de Reporte</h2>
        <div class="plantillas-grid">
          {#each PLANTILLAS as p}
            <a href={p.url} download={p.filename} class="plantilla-btn" style="--color: {p.color}">
              <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" style="color:{p.color}; flex-shrink:0;" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <div>
                <div class="plantilla-label">{p.label}</div>
                <div class="plantilla-ext" style="color:{p.color}">{p.ext}</div>
              </div>
            </a>
          {/each}
        </div>
      </div>

      <div class="card">
        <h2 class="card-title">Mis semanas</h2>
        <p class="semanas-nota">
          Cada semana se entrega por separado: no necesitas esperar la revisión de otra para enviar la siguiente.
          Puedes entregar hasta el domingo; desde el lunes siguiente, sin entrega, aparece como atrasada.
        </p>

        <div aria-live="polite">
          {#if aviso}<p class="aviso-ok" role="status">{aviso}</p>{/if}
        </div>

        {#if error}
          <p class="semanas-error" role="alert">{error}</p>
          <button class="btn-outline" on:click={cargarDatos}>Reintentar</button>
        {:else if obligaciones.length === 0}
          <p class="semanas-nota">Aún no tienes semanas registradas. Aparecen desde la fecha de inicio de tu incorporación.</p>
        {:else}
          {#if errorVersiones}<p class="semanas-error" role="alert">{errorVersiones}</p>{/if}
          <ul class="semanas-lista">
            {#each obligaciones as o (o.id)}
              <li class="semana-item">
                <div class="semana-cabecera">
                  <div>
                    <div class="semana-titulo">
                      Semana {o.ordinal}{#if o.parcial} <span class="semana-parcial">parcial</span>{/if}
                    </div>
                    <div class="semana-fechas">
                      {formatFechaCivil(o.inicio_efectivo)} – {formatFechaCivil(o.fin_efectivo)} · {o.periodo_label || 'Sin período'}
                    </div>
                  </div>
                  <div class="semana-estados">
                    {#if o.entrega}
                      <span class="semana-estado entrega-{o.entrega.toLowerCase()}">{ETIQUETA_ENTREGA[o.entrega]}{#if o.version}&nbsp;· v{o.version}{/if}</span>
                    {:else}
                      <span class="semana-estado semana-{o.estado.toLowerCase()}">{o.estado === 'ATRASADA' ? 'Atrasada · sin entrega' : 'Pendiente · sin entrega'}</span>
                    {/if}
                  </div>
                </div>

                {#if o.entrega === 'Rechazada' && o.observacion}
                  <div class="nota-rechazo">
                    <div class="nota-rechazo-label">Observación del tutor</div>
                    <div class="nota-rechazo-texto">{o.observacion}</div>
                  </div>
                {/if}

                <div class="semana-acciones">
                  {#if o.puede_entregar}
                    <button
                      class="btn-primary"
                      aria-expanded={seleccion === o.id}
                      aria-controls="form-{o.id}"
                      on:click={() => seleccion === o.id ? cerrarForm() : abrirForm(o)}
                    >
                      {o.entrega === 'Rechazada' ? 'Reenviar reporte' : 'Entregar reporte'}
                    </button>
                  {:else if o.motivo_bloqueo}
                    <span class="semana-bloqueo">{o.motivo_bloqueo}</span>
                  {/if}
                  {#if o.reporte_id}
                    <button class="btn-outline" aria-expanded={!!versionesAbiertas[o.reporte_id]} on:click={() => alternarVersiones(o)}>
                      {versionesAbiertas[o.reporte_id] ? 'Ocultar versiones' : 'Ver versiones'}
                    </button>
                  {/if}
                </div>

                {#if seleccion === o.id}
                  <form class="form-inline" id="form-{o.id}" on:submit|preventDefault={() => enviar(o)}>
                    {#if errorForm}<div class="error-msg" role="alert">{errorForm}</div>{/if}
                    <div class="form-grid">
                      <div class="field">
                        <label for="cal-{o.id}">Calificación de la empresa (entero de 1 a 10) <span class="req">*</span></label>
                        <input id="cal-{o.id}" class="input-plain" type="number" min="1" max="10" step="1" inputmode="numeric" placeholder="Ej. 9" bind:value={calificacion} required />
                      </div>
                      <div class="field">
                        <label for="ini-{o.id}">Fecha de inicio del reporte <span class="req">*</span></label>
                        <input id="ini-{o.id}" type="date" class="input-plain" bind:value={fechaInicio} required />
                      </div>
                      <div class="field">
                        <label for="fin-{o.id}">Fecha de fin del reporte <span class="req">*</span></label>
                        <input id="fin-{o.id}" type="date" class="input-plain" bind:value={fechaFin} required />
                      </div>
                      <div class="field field-full">
                        <label for="arc-{o.id}">Reporte firmado por la empresa (PDF, máximo {limiteMb} MB) <span class="req">*</span></label>
                        <input id="arc-{o.id}" class="input-plain" type="file" accept=".pdf,application/pdf" on:change={onArchivo} required />
                        {#if archivo}<span class="doc-name">{archivo.name} · {(archivo.size / 1024).toFixed(0)} KB</span>{/if}
                      </div>
                    </div>
                    <p class="semanas-nota">El tutor revisa que las fechas y la calificación coincidan con el PDF. El archivo se conserva tal como lo envías.</p>
                    <div class="form-actions">
                      <button type="button" class="btn-outline" on:click={cerrarForm}>Cancelar</button>
                      <button type="submit" class="btn-primary" disabled={enviando}>
                        {enviando ? 'Enviando...' : o.entrega === 'Rechazada' ? 'Enviar nueva versión' : 'Enviar reporte'}
                      </button>
                    </div>
                  </form>
                {/if}

                {#if o.reporte_id && versionesAbiertas[o.reporte_id] && versiones[o.reporte_id]}
                  <div class="versiones" role="region" aria-label="Versiones de la semana {o.ordinal}">
                    <table class="tabla-versiones">
                      <thead>
                        <tr><th>Versión</th><th>Recibida</th><th>Fechas</th><th>Nota</th><th>Decisión</th><th><span class="sr-only">Descargar</span></th></tr>
                      </thead>
                      <tbody>
                        {#each versiones[o.reporte_id] as v (v.numero)}
                          <tr>
                            <td>v{v.numero}</td>
                            <td>{formatFecha(v.recibido_en)}</td>
                            <td>
                              {formatFechaCivil(v.fecha_inicio)} – {formatFechaCivil(v.fecha_fin)}
                              {#if v.validada_inicio && (v.validada_inicio !== v.fecha_inicio || v.validada_fin !== v.fecha_fin)}
                                <span class="corregido">Corregidas por el tutor: {formatFechaCivil(v.validada_inicio)} – {formatFechaCivil(v.validada_fin)}</span>
                              {/if}
                            </td>
                            <td>
                              {v.nota}
                              {#if v.validada_nota && v.validada_nota !== v.nota}
                                <span class="corregido">Corregida por el tutor: {v.validada_nota}</span>
                              {/if}
                            </td>
                            <td>
                              {#if v.decision}{v.decision}{#if v.nota_revision}&nbsp;· {v.nota_revision}{/if}{:else}Pendiente de revisión{/if}
                            </td>
                            <td class="acciones-version">
                              <button class="btn-link" on:click={() => descargar(o, v)} aria-label="Descargar el original de la versión {v.numero} de la semana {o.ordinal}">Descargar original</button>
                              {#if v.firmado}
                                <button class="btn-link" on:click={() => descargar(o, v, 'firmado')} aria-label="Descargar el firmado de la versión {v.numero} de la semana {o.ordinal}">Descargar firmado</button>
                              {/if}
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
      </div>

    {/if}
  </div>
</div>

<style>
  .page { max-width: 900px; margin: 0 auto; padding: 40px 24px 64px; display: flex; flex-direction: column; gap: 24px; }

  .card { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); padding: 28px; display: flex; flex-direction: column; gap: 16px; }
  .card-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }

  .plantillas-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .plantilla-btn { display: flex; align-items: center; gap: 14px; padding: 14px 16px; border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--bg-page); cursor: pointer; text-decoration: none; transition: all 0.2s ease; }
  .plantilla-btn:hover { border-color: var(--color); background: var(--bg-card); box-shadow: var(--shadow-card); }
  .plantilla-label { font-size: 13px; font-weight: 700; color: var(--text-primary); }
  .plantilla-ext { font-size: 11px; font-weight: 700; text-transform: uppercase; margin-top: 1px; }

  .semanas-lista { list-style: none; display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; }
  .semana-item { display: flex; flex-direction: column; gap: 12px; padding: 14px; border: 1px solid var(--border); border-radius: var(--radius-input); }
  .semana-cabecera { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
  .semana-titulo { font-weight: 700; color: var(--text-primary); }
  .semana-fechas { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
  .semana-parcial { font-size: 11px; font-weight: 600; color: var(--text-secondary); border: 1px solid var(--border-input); border-radius: 999px; padding: 1px 8px; margin-left: 6px; }
  .semana-estado { font-size: 12px; font-weight: 700; color: var(--text-primary); border: 1px solid; border-radius: 999px; padding: 3px 10px; white-space: nowrap; }
  .semana-pendiente { border-color: var(--blue); background: color-mix(in srgb, var(--blue) 14%, transparent); }
  .semana-atrasada { border-color: var(--error); background: color-mix(in srgb, var(--error) 14%, transparent); }
  .entrega-pendiente { border-color: var(--blue); background: color-mix(in srgb, var(--blue) 14%, transparent); }
  .entrega-rechazada { border-color: var(--error); background: color-mix(in srgb, var(--error) 14%, transparent); }
  .entrega-aprobada { border-color: var(--success); background: color-mix(in srgb, var(--success) 14%, transparent); }
  .semanas-nota { font-size: 13px; color: var(--text-secondary); }
  .semanas-error { color: var(--error); font-size: 14px; }
  .aviso-ok { color: var(--text-primary); border-left: 3px solid var(--success); padding-left: 10px; font-size: 14px; }
  .semana-acciones { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .semana-bloqueo { font-size: 13px; color: var(--text-secondary); }

  .nota-rechazo { padding: 12px 14px; background: color-mix(in srgb, var(--error) 8%, transparent); border: 1px solid color-mix(in srgb, var(--error) 30%, transparent); border-radius: var(--radius-input); }
  .nota-rechazo-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-primary); margin-bottom: 6px; }
  .nota-rechazo-texto { font-size: 13px; color: var(--text-secondary); line-height: 1.5; overflow-wrap: anywhere; }

  .form-inline { padding: 16px; background: var(--bg-page); border: 1px solid var(--border); border-radius: var(--radius-input); display: flex; flex-direction: column; gap: 14px; }
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .field label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
  .field-full { grid-column: 1 / -1; }
  .req { color: var(--orange); }
  .form-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
  .doc-name { font-size: 12px; color: var(--text-secondary); overflow-wrap: anywhere; }
  .error-msg { color: var(--error); font-size: 14px; }

  /* position: relative contiene el texto solo para lectores de pantalla (sr-only) dentro del scroll. */
  .versiones { position: relative; overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-input); }
  .tabla-versiones { width: 100%; min-width: 560px; border-collapse: collapse; font-size: 13px; }
  .tabla-versiones th { text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase; color: var(--text-disabled); border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabla-versiones td { padding: 8px 10px; color: var(--text-secondary); border-bottom: 1px solid var(--border); vertical-align: top; }
  .tabla-versiones tbody tr:last-child td { border-bottom: none; }
  .corregido { display: block; margin-top: 2px; font-size: 11px; color: var(--orange); }
  .acciones-version { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
  .btn-link { background: none; border: none; padding: 0; color: var(--orange); font: inherit; font-weight: 600; cursor: pointer; text-decoration: underline; white-space: nowrap; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

  @media (max-width: 768px) {
    .card { padding: 20px 16px; }
    .plantillas-grid { grid-template-columns: 1fr; }
    .form-grid { grid-template-columns: 1fr; }
  }
</style>
