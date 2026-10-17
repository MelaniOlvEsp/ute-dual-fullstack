<script>
  // «Plantilla del reporte» (C09): el personal descarga la vigente; el coordinador publica una pareja
  // Word + PDF nueva (todo o nada) y consulta el historial de versiones.
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import { isCoordinadorDual } from '../../stores/auth.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'
  import PlantillaDescargas from '../../components/dual/PlantillaDescargas.svelte'
  import { formatFecha } from '../../utils/formatters.js'
  import { formatearBytes } from '../../../domain/dual/archivo.js'

  let historial = []
  let word = null
  let pdf = null
  let nota = ''
  let publicando = false
  let error = ''
  let exito = ''
  let recargar = 0
  let entradaWord
  let entradaPdf

  onMount(cargarHistorial)

  async function cargarHistorial() {
    if (!$isCoordinadorDual) return
    try {
      historial = await api.dual.plantillas()
    } catch (e) {
      error = e.message || 'No se pudo cargar el historial.'
    }
  }

  async function publicar() {
    error = ''
    exito = ''
    if (!word || !pdf) {
      error = 'Selecciona el archivo Word (.docx) y el PDF: la plantilla se publica como pareja.'
      return
    }
    const form = new FormData()
    form.append('word', word)
    form.append('pdf', pdf)
    if (nota.trim()) form.append('nota', nota.trim())
    publicando = true
    try {
      const nueva = await api.dual.publicarPlantilla(form)
      exito = `Versión ${nueva.numero} publicada: todos descargan ahora esta pareja.`
      word = pdf = null
      nota = ''
      if (entradaWord) entradaWord.value = ''
      if (entradaPdf) entradaPdf.value = ''
      recargar += 1
      await cargarHistorial()
    } catch (e) {
      error = e.message || 'No se pudo publicar la plantilla. No se publicó ningún archivo.'
    } finally {
      publicando = false
    }
  }
</script>

<svelte:head><title>Plantilla del reporte | Portal UTE</title></svelte:head>
<Navbar />
<main class="pagina">
  <div class="contenido">
    <PageHeader title="Plantilla del reporte" subtitle="Plantilla común Word y PDF para las tres carreras." />

    <section class="tarjeta" aria-labelledby="vigente-titulo">
      <h2 id="vigente-titulo" class="tarjeta-titulo">Versión vigente</h2>
      <PlantillaDescargas {recargar} />
    </section>

    {#if $isCoordinadorDual}
      <section class="tarjeta" aria-labelledby="publicar-titulo">
        <h2 id="publicar-titulo" class="tarjeta-titulo">Publicar una versión nueva</h2>
        <p class="texto">Se publican los dos archivos juntos. Si alguno no es válido no se publica nada y la versión vigente sigue igual. Los reportes ya entregados no cambian.</p>
        <div class="campo">
          <label for="plantilla-word">Word (.docx, sin macros)</label>
          <input id="plantilla-word" type="file" accept=".docx" bind:this={entradaWord} on:change={e => word = e.currentTarget.files[0] || null} />
        </div>
        <div class="campo">
          <label for="plantilla-pdf">PDF</label>
          <input id="plantilla-pdf" type="file" accept=".pdf,application/pdf" bind:this={entradaPdf} on:change={e => pdf = e.currentTarget.files[0] || null} />
        </div>
        <div class="campo">
          <label for="plantilla-nota">Nota de la versión (opcional)</label>
          <input id="plantilla-nota" class="input-plain" maxlength="200" bind:value={nota} placeholder="Qué cambió" />
        </div>
        {#if error}<p class="error-msg" role="alert">{error}</p>{/if}
        {#if exito}<p class="exito-msg" role="status">{exito}</p>{/if}
        <button class="btn-primary" disabled={publicando} on:click={publicar}>
          {publicando ? 'Publicando…' : 'Publicar pareja'}
        </button>
      </section>

      <section class="tarjeta" aria-labelledby="historial-titulo">
        <h2 id="historial-titulo" class="tarjeta-titulo">Historial de versiones</h2>
        {#if historial.length === 0}
          <p class="texto">Aún no se ha publicado ninguna versión.</p>
        {:else}
          <div class="tabla-wrap" role="region" aria-label="Historial de versiones" tabindex="0">
            <table class="tabla">
              <thead><tr><th>Versión</th><th>Publicada</th><th>Por</th><th>Word</th><th>PDF</th><th>Nota</th></tr></thead>
              <tbody>
                {#each historial as v (v.numero)}
                  <tr>
                    <td><strong>v{v.numero}</strong>{#if v.vigente} <span class="vigente">vigente</span>{/if}</td>
                    <td>{formatFecha(v.publicada_en)}</td>
                    <td>{v.publicada_por}</td>
                    <td>{formatearBytes(v.word.tamano)}</td>
                    <td>{formatearBytes(v.pdf.tamano)} · {v.pdf.paginas} pág.</td>
                    <td>{v.nota || '—'}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>
    {/if}
  </div>
</main>

<style>
  .pagina { padding-top: 56px; min-height: 100vh; background: var(--bg-page); }
  .contenido { max-width: 900px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
  .tarjeta { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 20px; display: flex; flex-direction: column; gap: 12px; }
  .tarjeta-titulo { margin: 0; font-size: 16px; color: var(--text-primary); }
  .texto { margin: 0; font-size: 13px; color: var(--text-secondary); }
  .campo { display: flex; flex-direction: column; gap: 4px; }
  .campo label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); }
  .tabla-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
  .tabla { width: 100%; border-collapse: collapse; font-size: 13px; }
  .tabla th { text-align: left; padding: 10px 12px; font-size: 11px; text-transform: uppercase; color: var(--text-disabled); border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabla td { padding: 10px 12px; border-bottom: 1px solid var(--border); color: var(--text-secondary); }
  .tabla tbody tr:last-child td { border-bottom: none; }
  .vigente { font-size: 11px; font-weight: 700; color: var(--orange); text-transform: uppercase; }
  .error-msg { color: var(--error); margin: 0; font-size: 13px; }
  .exito-msg { color: var(--success); margin: 0; font-size: 13px; }
  .btn-primary { align-self: flex-start; background: var(--orange); color: white; border: none; border-radius: var(--radius-btn); padding: 12px 20px; font-size: 14px; font-weight: 700; cursor: pointer; font-family: var(--font); }
  .btn-primary:disabled { opacity: 0.6; cursor: wait; }
</style>
