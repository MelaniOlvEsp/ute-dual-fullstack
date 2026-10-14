<script>
  // src/routes/Login.svelte
  import { navigate, link } from 'svelte-routing'
  import { fade } from 'svelte/transition'
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import { login, isAuthenticated, user } from '../../stores/auth.js'
  import { homeFor } from '../../../domain/auth/permissions.js'
  import { get } from 'svelte/store'

  let email = ''
  let password = ''
  let loading = false
  let error = ''
  let showPassword = false

  onMount(() => {
    if (get(isAuthenticated)) {
      navigate(homeFor(get(user)), { replace: true })
    }
  })

  async function handleSubmit(e) {
    if (e) e.preventDefault()
    if (!email) {
      error = 'Ingresa tu correo institucional'
      return
    }
    loading = true
    try {
      const session = await api.auth.loginSession({ email, password })
      login(session.accessToken, session.userData)

      if (session.mustChangePassword) {
        navigate('/cambiar-password', { replace: true })
        return
      }

      navigate(homeFor(session.userData), { replace: true })

    } catch (e) {
      const msg = e.message || 'Error al conectar con el servidor.'
      error = msg
    } finally {
      loading = false
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') handleSubmit(e) 
  }
</script>

<svelte:head>
  <title>Iniciar sesión | Portal UTE</title>
</svelte:head>

<div class="page">
  <div class="card" in:fade>
    <div class="header">
      <div class="logo-row">
        <img src="/UTEG-01.png" alt="UTE" class="logo-ute" />
        <img src="/ours.png" alt="OURS" class="logo-ours" />
      </div>
      <h1 class="title">Iniciar Sesión</h1>
      <p class="subtitle">Ingresa a tu cuenta institucional del sistema</p>
    </div>

    {#if error}
      <div class="error-msg">
        <span>{error}</span>

      </div>
    {/if}

    <div class="form">
      <div class="input-group">
        <label for="email">Correo Institucional</label>
        <div class="input-wrap">
          <span class="icon">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"/>
            </svg>
          </span>
          <input
            id="email" type="email" bind:value={email} placeholder="usuario@ute.edu.mx"
            on:keydown={handleKeydown} on:input={() => error = ''} autocomplete="email"
          />
        </div>
      </div>

      <div class="input-group">
        <label for="password">Contraseña</label>
        <div class="input-wrap">
          <span class="icon">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
            </svg>
          </span>
          
          {#if showPassword}
            <input
              id="password" type="text" bind:value={password}
              placeholder="••••••••" on:keydown={handleKeydown} on:input={() => error = ''} autocomplete="current-password"
            />
          {:else}
            <input
              id="password" type="password" bind:value={password}
              placeholder="••••••••" on:keydown={handleKeydown} on:input={() => error = ''} autocomplete="current-password"
            />
          {/if}

          <button type="button" class="eye-btn" on:click={() => showPassword = !showPassword} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
            {#if showPassword}
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"/></svg>
            {:else}
              <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            {/if}
          </button>
        </div>
      </div>

      <div class="forgot-row">
        <button class="link-orange forgot-link" on:click={() => alert('Solicita una contraseña provisional a tu tutor académico. La recibirás directamente del tutor.')}>
          ¿Olvidaste tu contraseña? Contacta a tu tutor
        </button>
      </div>

      <button class="btn-primary" on:click={handleSubmit} disabled={loading || !email || !password}>
        {#if loading}
          <span class="spinner"></span> Ingresando...
        {:else}
          Iniciar Sesión
        {/if}
      </button>

      <p class="bottom-text">
        ¿No tienes cuenta? <a href="/register" class="link-orange" use:link>Registrarme</a>
      </p>
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
  .forgot-row { display: flex; justify-content: flex-end; margin-top: -4px; }
  .forgot-row .forgot-link { font-size: 13px; background: none; border: none; cursor: pointer; padding: 0; font-family: var(--font); }
  .bottom-text { text-align: center; font-size: 13px; color: var(--text-secondary); margin-top: 8px; }
  
  .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
  
  .eye-btn { position: absolute; right: 14px; background: none; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; color: var(--text-disabled); transition: color 0.15s ease; }
  .eye-btn:hover { color: var(--text-secondary); }

  @media (max-width: 480px) {
    .card { padding: 24px 20px; }
    .logo-ute, .logo-ours { height: 56px; }
    .title { font-size: 20px; }
  }
</style>