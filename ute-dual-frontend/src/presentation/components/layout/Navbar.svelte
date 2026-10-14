<script>
  import { navigate, link } from 'svelte-routing'
  import { logout, user } from '../../stores/auth.js'

  export let onAlumnoClick = () => {}

  let sidebarOpen = false
  let dark = false
  $: roles = $user?.roles || {}
  $: tutor = Boolean(roles.tutor_academico)
  $: coordinator = Boolean(roles.coordinador_dual)
  $: student = Boolean(roles.alumno)

  function closeSidebar() { sidebarOpen = false }
  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }
  function toggleDark() {
    dark = !dark
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  }
</script>

<header class="navbar">
  <button class="hamburger" on:click={() => sidebarOpen = !sidebarOpen} aria-label="Abrir menú">☰</button>
  <div class="brand"><img src="/ours.png" alt="Portal Dual" class="logo-ours" /></div>
  <button class="theme-btn" on:click={toggleDark} aria-label="Cambiar tema">{dark ? '☀' : '☾'}</button>
</header>

{#if sidebarOpen}
  <button class="overlay" aria-label="Cerrar menú" on:click={closeSidebar}></button>
{/if}

<aside class="sidebar" class:open={sidebarOpen}>
  <div class="sidebar-header"><img src="/ours.png" alt="Portal Dual" class="logo-ours" /></div>
  <nav class="sidebar-nav">
    <span class="nav-section-title">Formación Dual</span>
    {#if student}
      <a href="/dual/reportes" use:link class="nav-item" on:click={closeSidebar}>Mis reportes</a>
      <button class="nav-item" on:click={() => { onAlumnoClick(); closeSidebar() }}>Mi perfil</button>
    {/if}
    {#if tutor}
      <a href="/dual/tutor" use:link class="nav-item" on:click={closeSidebar}>Revisar y firmar reportes</a>
      <a href="/dual/tutor?vista=empresas" use:link class="nav-item" on:click={closeSidebar}>Empresas y asignaciones</a>
      <a href="/dual/carrera" use:link class="nav-item" on:click={closeSidebar}>Expedientes</a>
      <a href="/dual/carrera?vista=grupos" use:link class="nav-item" on:click={closeSidebar}>Alumnos y grupos</a>
      <a href="/dual/accesos" use:link class="nav-item" on:click={closeSidebar}>Recuperar contraseña alumno</a>
    {/if}
    {#if coordinator}
      <a href="/dual/carrera" use:link class="nav-item" on:click={closeSidebar}>Consulta de expedientes</a>
      <a href="/dual/tutores" use:link class="nav-item" on:click={closeSidebar}>Cuentas de tutores</a>
    {/if}
    <a href="/foro" use:link class="nav-item" on:click={closeSidebar}>Anuncios y buzón</a>
    <a href="/cambiar-password" use:link class="nav-item" on:click={closeSidebar}>Cambiar contraseña</a>
  </nav>
  <div class="sidebar-footer">
    <button class="logout-btn" on:click={handleLogout}>Cerrar sesión</button>
  </div>
</aside>

<style>
  .navbar { position: fixed; top: 0; left: 0; right: 0; height: 56px; background: var(--bg-card); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; z-index: 100; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
  .hamburger { background: none; border: none; cursor: pointer; padding: 6px; border-radius: 8px; color: var(--text-primary); font-size: 22px; }
  .brand { display: flex; align-items: center; justify-content: center; gap: 10px; }
  .theme-btn { background: none; border: none; cursor: pointer; padding: 6px; border-radius: 8px; color: var(--text-primary); font-size: 22px; }
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 200; cursor: pointer; border: 0; width: 100%; }
  .sidebar { position: fixed; top: 0; left: 0; bottom: 0; width: 260px; background: var(--bg-card); z-index: 300; display: flex; flex-direction: column; transform: translateX(-100%); transition: transform 0.25s; box-shadow: 4px 0 20px rgba(0,0,0,0.1); }
  .sidebar.open { transform: translateX(0); }
  .sidebar-header { padding: 16px 20px; border-bottom: 1px solid var(--border); }
  .sidebar-nav { flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
  .sidebar-footer { padding: 16px; border-top: 1px solid var(--border); }
  .nav-section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 8px 12px; color: var(--text-secondary); }
  .nav-item { display: block; color: var(--text-primary); padding: 12px; text-decoration: none; border-radius: 8px; }
  .nav-item:hover { background: var(--bg-page); }
  .logout-btn { width: 100%; background: none; border: 1px solid var(--border); border-radius: 8px; padding: 12px; color: var(--text-primary); cursor: pointer; }
  .logo-ours { height: 36px; max-width: 135px; object-fit: contain; }
</style>
