<script>
  // src/routes/CambiarPassword.svelte
  import { navigate, link } from 'svelte-routing'
  import { fade } from 'svelte/transition'
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import { isAuthenticated, logout } from '../../stores/auth.js'
  import { get } from 'svelte/store'

  let passwordActual = ''
  let passwordNueva = ''
  let confirmar = ''
  let loading = false
  let error = ''
  let showActual = false
  let showNueva = false
  let showConfirmar = false

  onMount(() => {
    if (!get(isAuthenticated)) {
      navigate('/login', { replace: true })
    }
  })

  async function handleSubmit(e) {
    if (e) e.preventDefault()
    error = ''

    if (!passwordActual) {
      error = 'Ingresa tu contraseña actual'
      return
    }
    if (passwordNueva.length < 12) {
      error = 'La nueva contraseña debe tener al menos 12 caracteres'
      return
    }
    if (passwordNueva !== confirmar) {
      error = 'Las contraseñas no coinciden'
      return
    }
    if (passwordNueva === passwordActual) {
      error = 'La nueva contraseña debe ser diferente a la actual'
      return
    }

    loading = true
    try {
      await api.auth.cambiarPassword({
        password_actual: passwordActual,
        password_nueva: passwordNueva
      })
      logout()
      navigate('/login', { replace: true })
      alert('Contraseña actualizada con éxito. Inicia sesión con tu nueva contraseña.')
    } catch (e) {
      error = e.message || 'Error al cambiar la contraseña'
    } finally {
      loading = false
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') handleSubmit(e)
  }
</script>

<svelte:head>
  <title>Cambiar contraseña | Portal UTE</title>
</svelte:head>

<div class="page">
  <div class="card" in:fade>
    <div class="header">
      <div class="logo-row">
        <img src="/UTEG-01.png" alt="UTE" class="logo-ute" />
        <img src="/ours.png" alt="OURS" class="logo-ours" />
      </div>
      <h1 class="title">Cambiar Contraseña</h1>
      <p class="subtitle">
        Debes cambiar tu contraseña temporal antes de continuar
      </p>
    </div>

    {#if error}
      <div class="error-msg">{error}</div>
    {/if}

    <div class="form">
      <div class="input-group">
        <label for="actual">Contraseña actual</label>
        <div class="input-wrap">
          <span class="icon">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
            </svg>
          </span>
          <input
            id="actual"
            type={showActual ? 'text' : 'password'}
            value={passwordActual}
            on:input={(e) => { passwordActual = e.target.value; error = '' }}
            placeholder="Contraseña temporal"
            on:keydown={handleKeydown}
          />
          <button type="button" class="eye-btn" on:click={() => showActual = !showActual}>
            {#if showActual}🙈{:else}👁{/if}
          </button>
        </div>
      </div>

      <div class="input-group">
        <label for="nueva">Nueva contraseña</label>
        <div class="input-wrap">
          <span class="icon">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
            </svg>
          </span>
          <input
            id="nueva"
            type={showNueva ? 'text' : 'password'}
            value={passwordNueva}
            on:input={(e) => { passwordNueva = e.target.value; error = '' }}
            placeholder="Mínimo 12 caracteres"
            on:keydown={handleKeydown}
          />
          <button type="button" class="eye-btn" on:click={() => showNueva = !showNueva}>
            {#if showNueva}🙈{:else}👁{/if}
          </button>
        </div>
      </div>

      <div class="input-group">
        <label for="confirmar">Confirmar nueva contraseña</label>
        <div class="input-wrap">
          <span class="icon">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </span>
          <input
            id="confirmar"
            type={showConfirmar ? 'text' : 'password'}
            value={confirmar}
            on:input={(e) => { confirmar = e.target.value; error = '' }}
            placeholder="Repite tu nueva contraseña"
            on:keydown={handleKeydown}
          />
          <button type="button" class="eye-btn" on:click={() => showConfirmar = !showConfirmar}>
            {#if showConfirmar}🙈{:else}👁{/if}
          </button>
        </div>
      </div>

      <button class="btn-primary" on:click={handleSubmit} disabled={loading}>
        {#if loading}
          <span class="spinner"></span> Cambiando...
        {:else}
          Cambiar Contraseña
        {/if}
      </button>
    </div>
  </div>
</div>

<style>
  .page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px 16px; background: var(--bg-page); }
  .card { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); padding: 36px 32px; width: 100%; max-width: 400px; display: flex; flex-direction: column; gap: 20px; }
  .header { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 6px; }
  .logo-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; width: 100%; padding: 0 8px; }
  .logo-ute { height: 76px; width: auto; object-fit: contain; }
  .logo-ours { height: 76px; width: auto; object-fit: contain; }
  .title { font-size: 22px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
  .subtitle { font-size: 13px; color: var(--text-secondary); }
  .form { display: flex; flex-direction: column; gap: 16px; }

  :global(.input-wrap input) { padding-right: 42px !important; }

  .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .eye-btn { position: absolute; right: 14px; background: none; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; font-size: 14px; opacity: 0.6; transition: opacity 0.15s ease; }
  .eye-btn:hover { opacity: 1; }
</style>
