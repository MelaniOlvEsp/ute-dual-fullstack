<script>
  // src/routes/CambiarPassword.svelte
  import { navigate, link } from 'svelte-routing'
  import { fade } from 'svelte/transition'
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import { isAuthenticated, logout, user } from '../../stores/auth.js'
  import { get } from 'svelte/store'

  import { validatePassword } from '../../../domain/auth/credentials.js'
  import Icon from '../../components/ui/Icon.svelte'
  import { homeFor } from '../../../domain/auth/permissions.js'
  $: obligatorio = Boolean($user?.must_change_password)
  let success = false
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
    if (loading) return
    error = ''

    if (!passwordActual) {
      error = 'Ingresa tu contraseña actual'
      return
    }
    try { validatePassword(passwordNueva) }
    catch (e) { error = e.message; return }
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
      passwordActual = passwordNueva = confirmar = ''
      success = true
    } catch (e) {
      error = e.message || 'Error al cambiar la contraseña'
    } finally {
      loading = false
    }
  }

</script>

<svelte:head>
  <title>Cambiar contraseña | Portal UTE</title>
</svelte:head>

<main class="page">
  <div class="card" in:fade>
    <div class="header">
      <div class="logo-row">
        <img src="/UTEG-01.png" alt="UTE" class="logo-ute" />
        <img src="/ours.png" alt="OURS" class="logo-ours" />
      </div>
      <h1 class="title">Cambiar Contraseña</h1>
      <p class="subtitle">
        {success ? 'Tu contraseña se actualizó correctamente.' : obligatorio ? 'Debes cambiar tu contraseña temporal antes de continuar' : 'Actualiza la contraseña de tu cuenta cuando lo necesites.'}
      </p>
    </div>

    {#if error}
      <div class="error-msg">{error}</div>
    {/if}

    {#if success}
      <p role="status">Inicia sesión con tu nueva contraseña.</p>
      <a class="btn-primary" href="/login" use:link>Iniciar sesión</a>
    {:else}
    <form class="form" on:submit|preventDefault={handleSubmit}>
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
            placeholder={obligatorio ? "Contraseña temporal" : "Contraseña actual"}
          />
          <button type="button" class="eye-btn" on:click={() => showActual = !showActual} aria-label={showActual ? 'Ocultar contraseña actual' : 'Mostrar contraseña actual'}>
            <Icon name={showActual ? 'eyeOff' : 'eye'} size={18} />
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
          />
          <button type="button" class="eye-btn" on:click={() => showNueva = !showNueva} aria-label={showNueva ? 'Ocultar contraseña nueva' : 'Mostrar contraseña nueva'}>
            <Icon name={showNueva ? 'eyeOff' : 'eye'} size={18} />
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
          />
          <button type="button" class="eye-btn" on:click={() => showConfirmar = !showConfirmar} aria-label={showConfirmar ? 'Ocultar contraseña confirmación' : 'Mostrar contraseña confirmación'}>
            <Icon name={showConfirmar ? 'eyeOff' : 'eye'} size={18} />
          </button>
        </div>
      </div>

      <button type="submit" class="btn-primary" disabled={loading}>
        {#if loading}
          <span class="spinner"></span> Cambiando...
        {:else}
          Cambiar Contraseña
        {/if}
      </button>
      {#if !obligatorio}<a class="cancel-link" href={homeFor($user)} use:link>Cancelar y volver</a>{/if}
    </form>
    {/if}
  </div>
</main>

<style>
  .cancel-link { text-align: center; font-size: 14px; color: var(--text-secondary); padding: 8px; }
  a.btn-primary { text-decoration: none; }
  button:focus-visible, a:focus-visible { outline: 2px solid var(--orange); outline-offset: 3px; }
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
