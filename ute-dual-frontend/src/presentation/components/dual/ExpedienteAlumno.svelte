<script>
  // Expediente por período (C08): el mismo componente para el alumno («Mi expediente») y para el
  // personal. Muestra grupo y carrera históricos del período, los reportes aprobados con su nota
  // validada, el promedio provisional o final, las descargas (firmado y original) y el visor.
  import { api } from '../../../composition/api.js'
  import VisorPDF from '../shared/VisorPDF.svelte'
  import EmptyState from '../ui/EmptyState.svelte'
  import { formatFechaCivil, formatFecha } from '../../utils/formatters.js'
  import { createEventDispatcher } from 'svelte'
  import DepuracionDialogo from './DepuracionDialogo.svelte'
  import { etiquetaPromedio, tipoPromedio, situacionAlumno, mensajeVentana } from '../../../domain/dual/expediente.js'
  import { mensajeArchivo } from '../../../domain/dual/archivo.js'

  const dispatch = createEventDispatcher()

  export let datos
  export let modo = 'personal'
  export let puedeExportar = false

  let indice = 0
  let seleccionado = null
  let error = ''
  let ocupado = ''
  let depurando = false

  $: alumno = datos?.alumno
  $: periodos = datos?.periodos || []
  $: if (indice >= periodos.length) indice = 0
  $: actual = periodos[indice] || null
  $: aprobados = actual?.aprobados || []
  $: if (actual && seleccionado && !aprobados.some(a => a.reporte_id === seleccionado.reporte_id)) seleccionado = null
  $: documentoVisor = seleccionado?.firmado ? 'firmado' : 'original'
  $: urlVisor = seleccionado
    ? (modo === 'alumno'
      ? api.dual.versionPdfUrlAlumno(seleccionado.reporte_id, seleccionado.version, documentoVisor)
      : api.dual.versionPdfUrlCarrera(seleccionado.reporte_id, seleccionado.version, documentoVisor))
    : ''
  $: etiquetaPeriodo = actual?.periodo.periodo_label || ''

  async function descargarReporte(a, documento) {
    error = ''
    ocupado = `${a.reporte_id}-${documento}`
    try {
      const etiqueta = `${etiquetaPeriodo} semana ${a.semana}`
      if (modo === 'alumno') await api.dual.downloadVersion(a.reporte_id, a.version, etiqueta, documento)
      else await api.dual.downloadApproved(a.reporte_id, a.version, documento, etiqueta)
    } catch (e) {
      error = e.message || 'No se pudo descargar el archivo.'
    } finally {
      ocupado = ''
    }
  }

  // C08B: depuración de los archivos de este alumno en el período (tutor y coordinador).
  async function programarPurga(frase) {
    await api.dual.programarPurga(actual.periodo.id, { matricula: alumno.matricula, confirmar: true, frase })
    depurando = false
    dispatch('actualizar')
  }

  async function cancelarPurga() {
    error = ''
    ocupado = 'purga'
    try {
      await api.dual.cancelarPurga(actual.periodo.id, actual.archivo.purga_id)
      dispatch('actualizar')
    } catch (e) {
      error = e.message || 'No se pudo cancelar la depuración.'
    } finally {
      ocupado = ''
    }
  }

  $: avisoArchivo = mensajeArchivo(actual?.archivo, formatFechaCivil)
  $: puedeDepurar = modo === 'personal' && actual?.periodo.evaluacion === 'finalizada' && actual?.archivo?.estado === 'normal'
    && aprobados.some(a => !a.archivado_en)

  async function descargarPaquete() {
    error = ''
    ocupado = 'paquete'
    try {
      if (modo === 'alumno') await api.dual.downloadMyPackage(actual.periodo.id, etiquetaPeriodo)
      else await api.dual.downloadStudentPackage(alumno.matricula, actual.periodo.id, etiquetaPeriodo)
    } catch (e) {
      error = e.message || 'No se pudo generar el paquete.'
    } finally {
      ocupado = ''
    }
  }
</script>

{#if !alumno}
  <EmptyState message="No se pudo cargar el expediente." />
{:else}
  <div class="expediente">
    <section class="ficha" aria-label="Datos del alumno">
      <h2 class="ficha-titulo">{alumno.nombre}</h2>
      <p class="ficha-linea"><span class="mono">{alumno.matricula}</span></p>
      {#if modo === 'personal'}
        <p class="ficha-linea">{situacionAlumno(alumno)}{#if !alumno.activo && alumno.fecha_baja}&nbsp;· baja el {formatFechaCivil(alumno.fecha_baja)}{/if}</p>
      {/if}

      {#if periodos.length}
        <label class="campo-etiqueta" for="expediente-periodo">Período</label>
        <select id="expediente-periodo" class="input-plain" bind:value={indice}>
          {#each periodos as p, i}
            <option value={i}>{p.periodo.periodo_label} · {p.periodo.evaluacion === 'finalizada' ? 'evaluación finalizada' : 'evaluación en curso'}</option>
          {/each}
        </select>
      {/if}
    </section>

    {#if !periodos.length}
      <EmptyState message="Aún no hay períodos con semanas en este expediente." />
    {:else if actual}
      <section class="periodo" aria-label="Período {etiquetaPeriodo}">
        <div class="resumen">
          <div class="dato">
            <span class="dato-etiqueta">Grupo del período</span>
            <span class="dato-valor mono">{actual.grupo.nomenclatura || '—'}</span>
            <span class="dato-sub">{actual.grupo.carrera || 'Sin carrera registrada'}{#if actual.grupo.grado}&nbsp;· grado {actual.grupo.grado}{/if}</span>
          </div>
          <div class="dato">
            <span class="dato-etiqueta">Promedio</span>
            <span class="dato-valor grande">{etiquetaPromedio(actual.resumen)}</span>
            <span class="dato-sub">{tipoPromedio(actual.resumen)} · {actual.resumen.aprobados} aprobado{actual.resumen.aprobados === 1 ? '' : 's'} · suma {actual.resumen.suma}</span>
          </div>
          <div class="dato">
            <span class="dato-etiqueta">Fechas del período</span>
            <span class="dato-valor">{formatFechaCivil(actual.periodo.fecha_inicio)} – {formatFechaCivil(actual.periodo.fecha_fin)}</span>
            {#if actual.periodo.cierre_efectivo}
              <span class="dato-sub">Recepción cerrada el {formatFechaCivil(actual.periodo.cierre_efectivo)}</span>
            {/if}
          </div>
        </div>

        <div class="paquete" role="group" aria-label="Paquete de archivo">
          {#if modo === 'alumno'}
            <p class="paquete-texto" class:vencido={!actual.paquete.disponible}>{mensajeVentana(actual.paquete, formatFechaCivil)}</p>
            {#if actual.paquete.disponible}
              <button class="btn-primary" disabled={ocupado === 'paquete'} on:click={descargarPaquete}>
                {ocupado === 'paquete' ? 'Preparando…' : 'Descargar mi paquete (ZIP)'}
              </button>
            {/if}
          {:else if puedeExportar}
            <p class="paquete-texto" class:vencido={!actual.paquete.disponible}>
              {actual.paquete.disponible
                ? 'Paquete de archivo del alumno para este período: PDF firmados y originales con manifiesto y hashes.'
                : actual.paquete.motivo}
            </p>
            {#if actual.paquete.disponible}
              <button class="btn-outline" disabled={ocupado === 'paquete'} on:click={descargarPaquete}>
                {ocupado === 'paquete' ? 'Preparando…' : 'Descargar paquete del alumno (ZIP)'}
              </button>
            {/if}
          {/if}
        </div>

        {#if avisoArchivo}
          <p class="aviso-archivo" role="status">{avisoArchivo}</p>
        {/if}
        {#if modo === 'personal' && actual.archivo?.estado === 'programada' && actual.archivo.purga_id}
          <p class="paquete-texto">Depuración programada: se eliminan el {formatFechaCivil(actual.archivo.eliminacion_en)}.
            <button class="btn-link" disabled={ocupado === 'purga'} on:click={cancelarPurga}>Cancelar depuración</button></p>
        {:else if puedeDepurar}
          <p class="paquete-texto"><button class="btn-link" on:click={() => depurando = true}>Depurar archivos de este alumno…</button></p>
        {/if}

        {#if error}<p class="error-msg" role="alert">{error}</p>{/if}

        <h3 class="subtitulo">Reportes aprobados</h3>
        {#if aprobados.length === 0}
          <EmptyState message="No hay reportes aprobados en este período." />
        {:else}
          <div class="tabla-wrap" role="region" aria-label="Reportes aprobados" tabindex="0">
            <table class="tabla">
              <thead>
                <tr>
                  <th>Semana</th><th>Fechas del reporte</th><th class="num">Nota</th><th>Versión</th><th>Documentos</th>
                </tr>
              </thead>
              <tbody>
                {#each aprobados as a (a.reporte_id)}
                  <tr class:seleccionada={seleccionado?.reporte_id === a.reporte_id}>
                    <td><strong>Semana {a.semana}</strong></td>
                    <td>{formatFechaCivil(a.fecha_inicio)} – {formatFechaCivil(a.fecha_fin)}</td>
                    <td class="num">
                      <strong>{a.nota}</strong>
                      {#if a.corregida}<span class="corregida">Corregida por el tutor (declaró {a.declarada_nota})</span>{/if}
                    </td>
                    <td>v{a.version}</td>
                    <td class="acciones">
                      {#if a.archivado_en}
                        <span class="archivado">Archivado el {formatFechaCivil(a.archivado_en)}</span>
                      {:else}
                      <button class="btn-link" aria-pressed={seleccionado?.reporte_id === a.reporte_id}
                        on:click={() => seleccionado = a}>Ver</button>
                      {#if a.firmado}
                        <button class="btn-link" disabled={ocupado === `${a.reporte_id}-firmado`}
                          aria-label="Descargar el firmado de la semana {a.semana}"
                          on:click={() => descargarReporte(a, 'firmado')}>Firmado</button>
                      {/if}
                      <button class="btn-link" disabled={ocupado === `${a.reporte_id}-original`}
                        aria-label="Descargar el original de la semana {a.semana}"
                        on:click={() => descargarReporte(a, 'original')}>Original</button>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          <div class="visor">
            {#if seleccionado}
              <VisorPDF url={urlVisor} titulo={`${etiquetaPeriodo} · semana ${seleccionado.semana}${documentoVisor === 'firmado' ? ' · firmado' : ' · original'}`}
                nombreDescarga={`semana-${seleccionado.semana}-v${seleccionado.version}-${documentoVisor}.pdf`} />
            {:else}
              <p class="nota-visor">Elige «Ver» en un reporte para mostrarlo aquí.</p>
            {/if}
          </div>
        {/if}
      </section>
    {/if}
  </div>
{#if depurando}
  <DepuracionDialogo
    titulo="Depurar archivos del alumno"
    sujeto={`${alumno.nombre} (${alumno.matricula}) · ${etiquetaPeriodo}`}
    archivos={aprobados.filter(a => !a.archivado_en).reduce((n, a) => n + (a.firmado ? 2 : 1), 0)}
    bytes={0}
    frase={actual.archivo.frase_esperada}
    onProgramar={programarPurga}
    onCerrar={() => depurando = false} />
{/if}
{/if}

<style>
  .expediente { display: flex; flex-direction: column; gap: 20px; }
  .ficha, .periodo { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 20px; display: flex; flex-direction: column; gap: 12px; }
  .ficha-titulo { font-size: 20px; color: var(--text-primary); margin: 0; }
  .ficha-linea { margin: 0; font-size: 13px; color: var(--text-secondary); }
  .mono { font-family: monospace; font-weight: 600; color: var(--text-primary); }
  .campo-etiqueta { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); }
  .resumen { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .dato { display: flex; flex-direction: column; gap: 4px; border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; background: var(--bg-page); min-width: 0; }
  .dato-etiqueta { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-disabled); }
  .dato-valor { font-size: 15px; font-weight: 700; color: var(--text-primary); overflow-wrap: anywhere; }
  .dato-valor.grande { font-size: 26px; font-weight: 800; color: var(--orange); }
  .dato-sub { font-size: 12px; color: var(--text-secondary); }
  .paquete { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; border: 1px dashed var(--border-input); border-radius: 10px; padding: 12px 14px; }
  .paquete-texto { margin: 0; flex: 1 1 260px; font-size: 13px; color: var(--text-secondary); }
  .paquete-texto.vencido { color: var(--text-disabled); }
  .aviso-archivo { margin: 0; padding: 10px 14px; font-size: 13px; border: 1px solid var(--border); border-left: 3px solid var(--orange); border-radius: 8px; background: var(--bg-page); color: var(--text-primary); }
  .archivado { font-size: 12px; color: var(--text-disabled); }
  .subtitulo { font-size: 14px; margin: 4px 0 0; color: var(--text-primary); }
  .tabla-wrap { position: relative; overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
  .tabla { width: 100%; min-width: 560px; border-collapse: collapse; font-size: 13px; }
  .tabla th { text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase; color: var(--text-disabled); border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabla td { padding: 8px 10px; color: var(--text-secondary); border-bottom: 1px solid var(--border); vertical-align: top; }
  .tabla tbody tr:last-child td { border-bottom: none; }
  .tabla tr.seleccionada { background: var(--orange-light); }
  .num { text-align: right; white-space: nowrap; }
  .corregida { display: block; font-size: 11px; color: var(--orange); white-space: normal; text-align: right; }
  .acciones { display: flex; gap: 12px; flex-wrap: wrap; }
  .btn-link { background: none; border: none; padding: 0; color: var(--orange); font: inherit; font-weight: 600; cursor: pointer; text-decoration: underline; }
  .btn-link:disabled { opacity: 0.5; cursor: wait; }
  .btn-link:focus-visible { outline: 2px solid var(--orange); outline-offset: 2px; }
  .visor { min-height: 60vh; display: flex; }
  .nota-visor { margin: 0; font-size: 13px; color: var(--text-disabled); font-style: italic; }
  .error-msg { color: var(--error); margin: 0; }
</style>
