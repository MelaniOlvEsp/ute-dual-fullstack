<script>
  // Confirmación de una depuración de archivos (C08B): advertencia, consecuencia irreversible, confirmación
  // de que la copia ya se guardó y frase escrita. «Conservar todo» es la acción segura y la predeterminada.
  import { modalFocus } from '../ui/modalFocus.js'
  import { formatearBytes, puedeConfirmar } from '../../../domain/dual/archivo.js'

  export let titulo = 'Depurar archivos'
  export let sujeto = ''
  export let archivos = 0
  export let bytes = 0
  export let gracia = 7
  export let frase = ''
  export let onProgramar
  export let onCerrar

  let escrita = ''
  let guardada = false
  let ocupado = false
  let error = ''

  $: habilitado = puedeConfirmar({ frase: escrita, esperada: frase, guardada, ocupado })

  async function programar() {
    if (!habilitado) return
    ocupado = true
    error = ''
    try {
      await onProgramar(escrita.trim())
    } catch (e) {
      error = e.message || 'No se pudo programar la depuración.'
      ocupado = false
    }
  }
</script>

<dialog class="dialogo" use:modalFocus={onCerrar} aria-labelledby="depurar-titulo" aria-describedby="depurar-texto">
  <h3 id="depurar-titulo">{titulo}</h3>
  <p class="sujeto">{sujeto}</p>
  <div id="depurar-texto" class="advertencia" role="alert">
    <p><strong>Se eliminarán {archivos} archivo{archivos === 1 ? '' : 's'} PDF{bytes > 0 ? ` (${formatearBytes(bytes)})` : ''}, originales y firmados.</strong></p>
    <p>Pasados {gracia} días la eliminación es definitiva en el sistema y no se puede deshacer. Durante ese tiempo puedes cancelarla.</p>
    <p>Se conservan las notas, los promedios, las versiones, las decisiones y el historial. Los alumnos verán el aviso con la fecha de eliminación.</p>
  </div>

  <label class="confirmacion">
    <input type="checkbox" bind:checked={guardada} />
    <span>Ya descargué el paquete ZIP y lo guardé fuera del sistema.</span>
  </label>

  <label class="campo" for="depurar-frase">Escribe exactamente: <code>{frase}</code></label>
  <input id="depurar-frase" class="input-plain" autocomplete="off" spellcheck="false" bind:value={escrita} />

  {#if error}<p class="error-msg" role="alert">{error}</p>{/if}

  <div class="acciones">
    <button class="btn-primary" on:click={onCerrar} disabled={ocupado}>Conservar todo</button>
    <button class="btn-danger" on:click={programar} disabled={!habilitado}>
      {ocupado ? 'Programando…' : `Programar depuración (${gracia} días)`}
    </button>
  </div>
</dialog>

<style>
  .dialogo { margin: auto; max-height: 90vh; overflow-y: auto; border: 1px solid var(--border); border-radius: var(--radius-card); padding: 24px; width: min(560px, 92vw); background: var(--bg-card); color: var(--text-primary); display: flex; flex-direction: column; gap: 14px; }
  .dialogo::backdrop { background: #0000004d; }
  h3 { margin: 0; font-size: 18px; }
  .sujeto { margin: 0; font-size: 13px; color: var(--text-secondary); overflow-wrap: anywhere; }
  .advertencia { border: 1px solid var(--error); border-left-width: 4px; border-radius: 10px; padding: 12px 14px; background: var(--bg-page); font-size: 13px; display: flex; flex-direction: column; gap: 6px; }
  .advertencia p { margin: 0; }
  .confirmacion { display: flex; gap: 10px; align-items: flex-start; font-size: 14px; }
  .confirmacion input { margin-top: 3px; width: 18px; height: 18px; }
  .campo { font-size: 13px; color: var(--text-secondary); }
  code { font-family: monospace; font-weight: 700; color: var(--text-primary); overflow-wrap: anywhere; }
  .acciones { display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; margin-top: 4px; }
  .btn-primary, .btn-danger { border: none; border-radius: var(--radius-btn); padding: 12px 20px; font-size: 14px; font-weight: 700; cursor: pointer; font-family: var(--font); }
  .btn-primary { background: var(--orange-action); color: white; }
  .btn-danger { background: var(--error); color: white; }
  .btn-primary:disabled, .btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
  .error-msg { color: var(--error-text); margin: 0; font-size: 13px; }
  button:focus-visible, input:focus-visible { outline: 2px solid var(--orange); outline-offset: 2px; }
</style>
