<script>
  // Descarga de la plantilla común vigente (C09, RN-26, MP-13): Word y PDF con la sesión; el servidor
  // decide la versión vigente y no existe ninguna URL pública.
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import { formatFecha } from '../../utils/formatters.js'

  export let recargar = 0

  let vigente = null
  let cargando = true
  let error = ''
  let ocupado = ''

  const TIPOS = [
    { tipo: 'word', etiqueta: 'Plantilla Word', ext: 'DOCX', color: '#2B579A' },
    { tipo: 'pdf', etiqueta: 'Plantilla PDF', ext: 'PDF', color: '#DC2626' }
  ]

  $: recargar, cargar()

  onMount(cargar)

  async function cargar() {
    cargando = true
    error = ''
    try {
      vigente = (await api.dual.plantillaVigente()).vigente
    } catch (e) {
      vigente = null
      error = e.message || 'No se pudo consultar la plantilla.'
    } finally {
      cargando = false
    }
  }

  async function descargar(tipo) {
    error = ''
    ocupado = tipo
    try {
      await api.dual.downloadTemplate(vigente.numero, tipo)
    } catch (e) {
      error = e.message || 'No se pudo descargar la plantilla.'
    } finally {
      ocupado = ''
    }
  }
</script>

{#if cargando}
  <p class="nota">Consultando la plantilla…</p>
{:else if error && !vigente}
  <p class="error-msg" role="alert">{error}</p>
{:else if !vigente}
  <p class="nota">El coordinador aún no ha publicado la plantilla del reporte.</p>
{:else}
  <div class="plantillas-grid">
    {#each TIPOS as t}
      <button class="plantilla-btn" style="--color: {t.color}" disabled={ocupado === t.tipo} on:click={() => descargar(t.tipo)}
        aria-label="Descargar {t.etiqueta} versión {vigente.numero}">
        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" style="color:{t.color}; flex-shrink:0;" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
        <div>
          <div class="plantilla-label">{t.etiqueta}</div>
          <div class="plantilla-ext" style="color:{t.color}">{t.ext} · versión {vigente.numero}</div>
        </div>
      </button>
    {/each}
  </div>
  <p class="nota">Versión {vigente.numero} publicada el {formatFecha(vigente.publicada_en)}. Los reportes ya entregados no cambian con una versión nueva.</p>
  {#if error}<p class="error-msg" role="alert">{error}</p>{/if}
{/if}

<style>
  .plantillas-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .plantilla-btn { display: flex; align-items: center; gap: 14px; padding: 14px 16px; border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--bg-page); cursor: pointer; font-family: var(--font); text-align: left; color: inherit; }
  .plantilla-btn:hover:not(:disabled) { border-color: var(--color); background: var(--bg-card); box-shadow: var(--shadow-card); }
  .plantilla-btn:disabled { opacity: 0.6; cursor: wait; }
  .plantilla-btn:focus-visible { outline: 2px solid var(--orange); outline-offset: 2px; }
  .plantilla-label { font-size: 13px; font-weight: 700; color: var(--text-primary); }
  .plantilla-ext { font-size: 11px; font-weight: 700; text-transform: uppercase; margin-top: 1px; }
  .nota { margin: 8px 0 0; font-size: 13px; color: var(--text-secondary); }
  .error-msg { color: var(--error); margin: 8px 0 0; font-size: 13px; }
  @media (max-width: 767px) { .plantillas-grid { grid-template-columns: 1fr; } }
</style>
