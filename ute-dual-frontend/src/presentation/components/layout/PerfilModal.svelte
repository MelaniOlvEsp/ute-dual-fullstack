<script>
  import { link } from 'svelte-routing'
  import Icon from '../ui/Icon.svelte'
  import { modalFocus } from '../ui/modalFocus.js'
  export let alumno = null
  export let account = null
  export let roleLabel = ''
  export let show = false
  export let loading = false
  export let error = ''
  export let onNavigate = () => {}
  function cerrar() { show = false }
  $: esDualActivo = Boolean(alumno?.dual_activo)
</script>
{#if show}
  <dialog class="modal-card" use:modalFocus={cerrar} aria-labelledby="profile-title">
    <div class="modal-header">
      <div class="avatar"><Icon name="user" size={28} /></div>
      <div><h2 id="profile-title">Mi perfil</h2><p class="subtitle">{roleLabel || 'Información académica'}</p></div>
    </div>
    <div class="modal-fields">
      <div class="field-card"><span class="field-label">Nombre</span><span class="field-value">{account?.nombre || alumno?.nombre || '—'}</span></div>
      <div class="field-card"><span class="field-label">Correo institucional</span><span class="field-value">{account?.email || alumno?.email || '—'}</span></div>
      {#if loading}<p class="status" role="status">Cargando perfil…</p>
      {:else if error}<p class="status" role="alert">{error}</p>
      {:else if alumno && account?.roles?.alumno}
        <div class="field-card"><span class="field-label">Carrera</span><span class="field-value">{alumno.carrera || '—'}</span></div>
        <div class="field-card two-col">
          <div><span class="field-label">Matrícula</span><span class="field-value font-mono">{alumno.matricula || '—'}</span></div>
          <div><span class="field-label">Grupo</span><span class="field-value font-mono">{alumno.nomenclatura || '—'}</span></div>
        </div>
        <div class="field-card" class:dual-activo={esDualActivo}>
          <span class="field-label">Modalidad Dual</span><span class="field-value">{esDualActivo ? 'Activo' : 'No inscrito'}</span>
          {#if esDualActivo && alumno.empresa}<span class="field-label company-label">Empresa adscrita</span><span class="field-value">{alumno.empresa}</span>{/if}
        </div>
      {/if}
    </div>
    <a class="password-link" href="/cambiar-password" use:link on:click={() => { cerrar(); onNavigate() }}><Icon name="key" size={18} />Cambiar contraseña</a>
    <button class="modal-close" on:click={cerrar} aria-label="Cerrar perfil"><Icon name="close" size={18} /></button>
  </dialog>
{/if}
<style>
  .modal-card { margin: auto; background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); border-radius: var(--radius-card); box-shadow: 0 8px 40px #00000026; padding: 28px; width: calc(100% - 32px); max-width: 420px; max-height: calc(100dvh - 32px); overflow-y: auto; }
  .modal-card::backdrop { background: #00000059; backdrop-filter: blur(2px); }
  .modal-header { display: flex; align-items: center; gap: 16px; padding-right: 24px; margin-bottom: 20px; }
  .avatar { width: 52px; height: 52px; background: var(--orange-action); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  h2 { font-size: 17px; font-weight: 700; }
  .subtitle { font-size: 13px; color: var(--text-secondary); margin-top: 3px; }
  .modal-fields { display: flex; flex-direction: column; gap: 10px; }
  .field-card { background: var(--bg-page); border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 3px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .two-col > div { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .field-label { font-size: 11px; color: var(--text-secondary); font-weight: 500; text-transform: uppercase; letter-spacing: .04em; }
  .field-value { font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
  .font-mono { font-family: monospace; }
  .dual-activo { background: var(--orange-light); }
  .company-label { margin-top: 8px; }
  .status { font-size: 13px; color: var(--text-secondary); }
  .password-link { display: flex; align-items: center; gap: 10px; margin-top: 20px; padding: 12px 0 0; border-top: 1px solid var(--border); text-decoration: none; color: var(--text-secondary); font-size: 13px; font-weight: 500; }
  .password-link:hover { color: var(--orange); }
  .modal-close { position: absolute; top: 16px; right: 16px; background: var(--bg-page); border: none; border-radius: 8px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--text-secondary); }
  button:focus-visible, a:focus-visible { outline: 2px solid var(--orange); outline-offset: 3px; }
</style>
