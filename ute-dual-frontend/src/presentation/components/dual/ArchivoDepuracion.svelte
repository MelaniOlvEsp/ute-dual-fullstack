<script>
  // Panel «Archivo y depuración» (C08B): por período finalizado y carrera, cuántos archivos ocupan espacio,
  // si ya existe el paquete que respalda la depuración y el estado de la misma. Tutor y coordinador (D2).
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import DepuracionDialogo from './DepuracionDialogo.svelte'
  import { formatFecha } from '../../utils/formatters.js'
  import { ETIQUETA_ESTADO, formatearBytes, purgaVencida } from '../../../domain/dual/archivo.js'

  export let periodos = []

  let periodoId = ''
  let datos = null
  let cargando = false
  let error = ''
  let dialogo = null
  let ocupado = ''

  $: if (periodos.length && !periodoId) periodoId = periodos[0].id
  $: if (periodoId) cargar(periodoId)

  async function cargar(id) {
    cargando = true
    error = ''
    try {
      datos = await api.dual.archivoPeriodo(id)
    } catch (e) {
      datos = null
      error = e.message || 'No se pudo cargar el estado del archivo.'
    } finally {
      cargando = false
    }
  }

  const programadaDe = carrera => datos?.purgas.find(p => p.alcance === 'carrera' && p.carrera === carrera.codigo && p.estado === 'programada')

  async function programar(carrera, frase) {
    await api.dual.programarPurga(periodoId, { carrera: carrera.codigo, confirmar: true, frase })
    dialogo = null
    await cargar(periodoId)
  }

  async function cancelar(purga) {
    ocupado = purga.id
    error = ''
    try {
      await api.dual.cancelarPurga(periodoId, purga.id)
      await cargar(periodoId)
    } catch (e) {
      error = e.message || 'No se pudo cancelar la depuración.'
    } finally {
      ocupado = ''
    }
  }

  async function ejecutar(purga) {
    ocupado = purga.id
    error = ''
    try {
      await api.dual.ejecutarPurga(periodoId, purga.id)
      await cargar(periodoId)
    } catch (e) {
      error = e.message || 'No se pudo ejecutar la depuración.'
    } finally {
      ocupado = ''
    }
  }
</script>

<section class="archivo" aria-labelledby="archivo-titulo">
  <h2 id="archivo-titulo" class="titulo">Archivo y depuración de archivos</h2>
  <p class="texto">Después de guardar el paquete ZIP fuera del sistema puedes liberar el espacio de los PDF de un período. Se eliminan solo los archivos PDF; las notas, los promedios y el historial se conservan. Hay {datos?.gracia_dias ?? 7} días para cancelar antes de que se eliminen.</p>

  {#if periodos.length === 0}
    <p class="texto">Aún no hay períodos con la evaluación finalizada.</p>
  {:else}
    <div class="campo">
      <label for="archivo-periodo">Período finalizado</label>
      <select id="archivo-periodo" class="input-plain input-sm" bind:value={periodoId}>
        {#each periodos as p}<option value={p.id}>{p.periodo_label}</option>{/each}
      </select>
    </div>

    {#if error}<p class="error-msg" role="alert">{error}</p>{/if}

    {#if cargando && !datos}
      <p class="texto">Cargando…</p>
    {:else if datos && datos.carreras.length === 0}
      <p class="texto">Este período no tiene reportes aprobados con archivos.</p>
    {:else if datos}
      <div class="tabla-wrap" role="region" aria-label="Archivos por carrera" tabindex="0">
        <table class="tabla">
          <thead>
            <tr><th>Carrera</th><th class="num">Alumnos</th><th class="num">Archivos</th><th class="num">Tamaño</th><th>Paquete</th><th>Estado</th><th>Acción</th></tr>
          </thead>
          <tbody>
            {#each datos.carreras as c (c.codigo)}
              {@const programada = programadaDe(c)}
              <tr>
                <td><strong>{c.nombre}</strong></td>
                <td class="num">{c.alumnos}</td>
                <td class="num">{c.archivos_vigentes} de {c.archivos_total}</td>
                <td class="num">{formatearBytes(c.bytes_vigentes)}</td>
                <td>{c.paquete ? `Generado el ${formatFecha(c.paquete.generado_en)}` : 'Aún no generado'}</td>
                <td>
                  <span class="estado estado-{c.estado}">{ETIQUETA_ESTADO[c.estado] || c.estado}</span>
                  {#if programada}<div class="sub">Se eliminan el {formatFecha(programada.ejecutar_en)}</div>{/if}
                </td>
                <td class="acciones">
                  {#if programada}
                    <button class="btn-link" disabled={ocupado === programada.id} on:click={() => cancelar(programada)}>Cancelar depuración</button>
                    {#if purgaVencida(programada)}
                      <button class="btn-link" disabled={ocupado === programada.id} on:click={() => ejecutar(programada)}>Ejecutar ahora</button>
                    {/if}
                  {:else if c.puede_depurar}
                    <button class="btn-link" on:click={() => dialogo = c}>Depurar archivos…</button>
                  {:else if c.estado === 'sin_depurar' && c.archivos_vigentes > 0}
                    <span class="sub">Genera primero el paquete de la carrera.</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if datos.purgas.length}
        <details class="historial">
          <summary>Historial de depuraciones ({datos.purgas.length})</summary>
          <ul>
            {#each datos.purgas as p (p.id)}
              <li>
                {p.alcance === 'carrera' ? `Carrera ${p.carrera}` : `Alumno ${p.matricula}`} · {p.estado}
                · solicitada el {formatFecha(p.solicitada_en)} por {p.solicitada_por_nombre}
                · {p.archivos} archivos ({formatearBytes(p.bytes)})
                {#if p.estado === 'completada'}· eliminados el {formatFecha(p.completada_en)}{/if}
                {#if p.estado === 'cancelada'}· cancelada el {formatFecha(p.cancelada_en)}{/if}
                {#if p.estado === 'programada' && p.ultimo_error}· último error: {p.ultimo_error}{/if}
              </li>
            {/each}
          </ul>
        </details>
      {/if}
    {/if}
  {/if}
</section>

{#if dialogo}
  <DepuracionDialogo
    titulo="Depurar archivos de la carrera"
    sujeto={`${dialogo.nombre} · ${datos.periodo.periodo_label}`}
    archivos={dialogo.archivos_vigentes}
    bytes={dialogo.bytes_vigentes}
    gracia={datos.gracia_dias}
    frase={dialogo.frase_esperada}
    onProgramar={frase => programar(dialogo, frase)}
    onCerrar={() => dialogo = null} />
{/if}

<style>
  .archivo { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 20px; display: flex; flex-direction: column; gap: 12px; }
  .titulo { margin: 0; font-size: 16px; color: var(--text-primary); }
  .texto { margin: 0; font-size: 13px; color: var(--text-secondary); }
  .campo { display: flex; flex-direction: column; gap: 4px; max-width: 320px; }
  .campo label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); }
  .tabla-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
  .tabla { width: 100%; border-collapse: collapse; font-size: 13px; }
  .tabla th { text-align: left; padding: 10px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-disabled); border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabla td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; color: var(--text-secondary); }
  .tabla tbody tr:last-child td { border-bottom: none; }
  .num { text-align: right; white-space: nowrap; }
  .sub { font-size: 12px; color: var(--text-secondary); }
  .estado { font-weight: 700; color: var(--text-primary); }
  .estado-programada { color: var(--orange); }
  .estado-depurado { color: var(--text-disabled); }
  .acciones { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
  .btn-link { background: none; border: none; padding: 0; color: var(--orange); font: inherit; font-weight: 600; cursor: pointer; text-decoration: underline; text-align: left; }
  .btn-link:disabled { opacity: 0.5; cursor: wait; }
  .btn-link:focus-visible { outline: 2px solid var(--orange); outline-offset: 2px; }
  .historial { font-size: 13px; color: var(--text-secondary); }
  .historial ul { margin: 8px 0 0; padding-left: 18px; display: flex; flex-direction: column; gap: 4px; }
  .error-msg { color: var(--error); margin: 0; font-size: 13px; }
</style>
