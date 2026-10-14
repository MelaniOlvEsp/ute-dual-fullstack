<script>
  export let alumno
  export let show = false

  function cerrar() { show = false }
  function handleOverlayKeydown(e) { if (e.key === 'Escape') cerrar() }

  $: esDualActivo = Boolean(
    alumno?.es_alumno_dual || 
    alumno?.activo || 
    alumno?.empresa_id || 
    alumno?.empresa
  )
</script>

{#if show && alumno}
  <button class="modal-overlay" on:click={cerrar} on:keydown={handleOverlayKeydown} aria-label="Cerrar modal">
    <div class="modal-card" on:click|stopPropagation role="dialog" aria-modal="true" aria-label="Perfil del alumno">
      
      <div class="modal-header">
        <div class="avatar">
          <svg width="28" height="28" fill="none" stroke="white" stroke-width="1.8" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
          </svg>
        </div>
        <div>
          <div class="modal-title">Perfil del Alumno</div>
          <div class="modal-subtitle">Información académica</div>
        </div>
      </div>

      <div class="modal-fields">
        <div class="field-card">
          <span class="field-label">Nombre</span>
          <span class="field-value">{alumno.nombre}</span>
        </div>
        
        <div class="field-card">
          <span class="field-label">Carrera</span>
          <span class="field-value">{alumno.carrera || '—'}</span>
        </div>
        
        <div class="field-card two-col">
          <div>
            <span class="field-label">Matrícula</span>
            <span class="field-value font-mono">{alumno.matricula}</span>
          </div>
          <div>
            <span class="field-label">Grupo</span>
            <span class="field-value font-mono">{alumno.nomenclatura || '—'}</span>
          </div>
        </div>
        
        <div class="field-card dual-card" class:dual-activo={esDualActivo}>
          <div class="dual-row">
            <div>
              <span class="field-label">Modalidad Dual</span>
              <span class="field-value">
                {#if esDualActivo}
                  <span class="dual-badge">✦ Activo</span>
                {:else}
                  <span class="nodual-badge">No inscrito</span>
                {/if}
              </span>
            </div>
            {#if esDualActivo && alumno.empresa}
              <div>
                <span class="field-label">Empresa adscrita</span>
                <span class="field-value empresa-val">{alumno.empresa}</span>
              </div>
            {/if}
          </div>
        </div>
      </div>

      <button class="modal-close" on:click={cerrar} aria-label="Cerrar">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
      
    </div>
  </button>
{/if}

<style>
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; backdrop-filter: blur(2px); border: none; cursor: default; width: 100%; text-align: left; }
  .modal-card { background: var(--bg-card); border-radius: var(--radius-card); box-shadow: 0 8px 40px rgba(0,0,0,0.15); padding: 28px; width: 100%; max-width: 420px; position: relative; display: flex; flex-direction: column; gap: 20px; }
  
  .modal-header { display: flex; align-items: center; gap: 16px; }
  .avatar { width: 52px; height: 52px; background: var(--orange); border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .modal-title { font-size: 17px; font-weight: 700; color: var(--text-primary); }
  .modal-subtitle { font-size: 13px; color: var(--text-secondary); }
  
  .modal-fields { display: flex; flex-direction: column; gap: 10px; }
  .field-card { background: var(--bg-page); border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 3px; color: var(--text-primary); }
  .field-card.two-col { display: grid; grid-template-columns: 1fr 1fr; }
  .field-card.two-col > div { display: flex; flex-direction: column; gap: 3px; }
  .field-label { font-size: 11px; color: var(--text-secondary); font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }
  .field-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .font-mono { font-family: monospace; letter-spacing: 0.02em; }
  
  .dual-card { background: var(--bg-page); }
  .dual-activo { background: #FFF7ED; border: 1px solid #FED7AA; }
  .dual-row { display: flex; gap: 24px; }
  .dual-row > div { display: flex; flex-direction: column; gap: 3px; }
  .dual-badge { display: inline-block; font-size: 12px; font-weight: 700; color: var(--orange); background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 6px; padding: 2px 8px; margin-top: 2px; }
  .nodual-badge { display: inline-block; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
  .empresa-val { color: var(--text-primary); }

  :global([data-theme="dark"]) .dual-activo { background: var(--bg-page) !important; border: none !important; }
  :global([data-theme="dark"]) .empresa-val { color: var(--text-primary) !important; }
  :global([data-theme="dark"]) .dual-badge { background: rgba(249, 115, 22, 0.2) !important; border-color: var(--orange) !important; }

  .modal-close { position: absolute; top: 16px; right: 16px; background: var(--bg-page); border: none; border-radius: 8px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--text-secondary); transition: background 0.15s; }
  .modal-close:hover { background: var(--border); }
</style>