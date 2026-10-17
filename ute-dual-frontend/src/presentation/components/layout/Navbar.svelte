<script>
  import { onMount } from 'svelte'
  import { navigate, link, useLocation } from 'svelte-routing'
  import { logout, user } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import Icon from '../ui/Icon.svelte'
  import { modalFocus } from '../ui/modalFocus.js'
  import PerfilModal from './PerfilModal.svelte'
  const location = useLocation()
  let sidebarOpen = false
  let showPerfil = false
  let alumno = null
  let accountProfile = null
  $: account = { ...$user, nombre: accountProfile?.nombre || $user?.nombre }
  let profileLoading = false
  let profileError = ''
  let dark = document.documentElement.getAttribute('data-theme') === 'dark'
  $: roles = $user?.roles || {}
  $: roleLabel = [roles.coordinador_dual && 'Coordinador Dual', roles.tutor_academico && 'Tutor académico', roles.alumno && 'Alumno'].filter(Boolean).join(' · ')
  $: items = [
    ...(roles.alumno ? [
      { href: '/dual/reportes', label: 'Mis reportes', icon: 'report' },
      { href: '/dual/expediente', label: 'Mi expediente', icon: 'folder' }
    ] : []),
    ...(roles.tutor_academico ? [
      { href: '/dual/tutor', label: 'Revisar y firmar reportes', icon: 'report' },
      { href: '/dual/tutor?vista=empresas', label: 'Empresas y asignaciones', icon: 'building' },
      { href: '/dual/carrera', label: 'Expedientes', icon: 'folder' },
      { href: '/dual/carrera?vista=grupos', label: 'Alumnos y grupos', icon: 'group' },
      { href: '/dual/accesos', label: 'Recuperar acceso de alumno', icon: 'key' }
    ] : []),
    ...(roles.coordinador_dual ? [
      ...(!roles.tutor_academico ? [{ href: '/dual/carrera', label: 'Consulta de expedientes', icon: 'folder' }] : []),
      { href: '/dual/periodos', label: 'Períodos', icon: 'calendar' },
      { href: '/dual/tutores', label: 'Cuentas de tutores', icon: 'people' }
    ] : [])
  ]
  function isActive(href, current) {
    const target = new URL(href, window.location.origin)
    return current.pathname === target.pathname && new URLSearchParams(current.search).get('vista') === target.searchParams.get('vista')
  }
  function closeSidebar() { sidebarOpen = false }
  function handleLogout() { logout(); navigate('/login', { replace: true }) }
  function toggleDark() {
    dark = !dark
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  }
  onMount(loadProfile)
  async function loadProfile() {
    if (profileLoading) return
    profileError = ''
    profileLoading = true
    try {
      const profile = await api.auth.me()
      accountProfile = profile
      if (roles.alumno) alumno = profile
    } catch { profileError = 'No se pudo cargar el perfil. Cierra la tarjeta y vuelve a intentarlo.' }
    finally { profileLoading = false }
  }
  function openProfile() {
    showPerfil = true
    loadProfile()
  }
</script>
<header class="navbar">
  <button class="icon-btn" on:click={() => sidebarOpen = true} aria-label="Abrir menú" aria-expanded={sidebarOpen}><Icon name="menu" /></button>
  <img src="/ours.png" alt="Portal Dual" class="logo-ours" />
  <button class="icon-btn" on:click={toggleDark} aria-label={dark ? 'Activar tema claro' : 'Activar tema oscuro'}><Icon name={dark ? 'sun' : 'moon'} /></button>
</header>
{#if sidebarOpen}
  <dialog class="sidebar" use:modalFocus={closeSidebar} aria-label="Menú principal">
    <div class="sidebar-content">
      <div class="sidebar-header"><img src="/ours.png" alt="Portal Dual" class="logo-ours" /><button class="icon-btn" aria-label="Cerrar menú" on:click={closeSidebar}><Icon name="close" /></button></div>
      <button class="account" on:click={openProfile} aria-haspopup="dialog">
        <span class="avatar"><Icon name="user" size={22} /></span>
        <span class="account-text"><strong>{account.nombre || 'Mi perfil'}</strong><span>{roleLabel}</span><span class="profile-link">Ver mi perfil</span></span>
      </button>
      <nav class="sidebar-nav" aria-label="Navegación">
        <span class="nav-section-title">Comunidad</span>
        <a href="/foro" use:link class="nav-item" class:active={isActive('/foro', $location)} aria-current={isActive('/foro', $location) ? 'page' : undefined} on:click={closeSidebar}><Icon name="chat" size={18} />Anuncios y buzón</a>
        <span class="nav-section-title">Formación Dual</span>
        {#each items as item}
          <a href={item.href} use:link class="nav-item" class:active={isActive(item.href, $location)} aria-current={isActive(item.href, $location) ? 'page' : undefined} on:click={closeSidebar}><Icon name={item.icon} size={18} /><span>{item.label}</span></a>
        {/each}
      </nav>
      <div class="sidebar-footer"><button class="logout-btn" on:click={handleLogout}><Icon name="logout" size={18} />Cerrar sesión</button></div>
    </div>
  </dialog>
{/if}
<PerfilModal bind:show={showPerfil} {alumno} {account} {roleLabel} loading={profileLoading} error={profileError} onNavigate={closeSidebar} />
<style>
  .navbar { position: fixed; inset: 0 0 auto; height: 56px; background: var(--bg-card); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; z-index: 100; box-shadow: 0 1px 4px #0000000f; }
  .icon-btn { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; background: none; border: none; border-radius: 8px; color: var(--text-primary); cursor: pointer; }
  .icon-btn:hover { background: var(--orange-light); color: var(--orange); }
  .logo-ours { height: 44px; max-width: 140px; object-fit: contain; }
  .sidebar { position: fixed; inset: 0 auto 0 0; margin: 0; padding: 0; width: min(300px, 90vw); height: 100dvh; max-height: 100dvh; max-width: 100vw; background: var(--bg-card); color: var(--text-primary); border: none; box-shadow: 4px 0 20px #0000001a; }
  .sidebar::backdrop { background: #0000004d; }
  .sidebar-content { min-height: 100%; display: flex; flex-direction: column; }
  .sidebar-header { padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
  .account { margin: 16px 12px 4px; padding: 12px; display: flex; align-items: center; gap: 12px; text-align: left; background: var(--bg-page); border: 1px solid var(--border); border-radius: 12px; font-family: var(--font); color: var(--text-primary); cursor: pointer; }
  .avatar { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 42px; height: 42px; border-radius: 50%; background: var(--orange-light); color: var(--orange); }
  .account-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; overflow-wrap: anywhere; }
  .account-text strong { font-size: 14px; font-weight: 600; }
  .account-text span { font-size: 12px; color: var(--text-secondary); }
  .account-text .profile-link { color: var(--orange); font-weight: 600; margin-top: 3px; }
  .sidebar-nav { flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; }
  .nav-section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; padding: 12px 14px 6px; color: var(--text-secondary); }
  .nav-item, .logout-btn { display: flex; align-items: center; gap: 12px; padding: 11px 14px; border-radius: 10px; font-family: var(--font); font-size: 14px; font-weight: 500; line-height: 1.4; color: var(--text-primary); background: none; border: none; cursor: pointer; text-decoration: none; text-align: left; width: 100%; transition: background .15s, color .15s; }
  .nav-item :global(svg) { flex-shrink: 0; }
  .nav-item:hover, .nav-item.active { background: var(--orange-light); color: var(--orange); }
  .nav-item.active { font-weight: 600; }
  .sidebar-footer { padding: 16px 8px 24px; border-top: 1px solid var(--border); }
  .logout-btn { color: var(--text-secondary); }
  .logout-btn:hover { background: var(--orange-light); color: var(--error); }
  button:focus-visible, a:focus-visible { outline: 2px solid var(--orange); outline-offset: 2px; }
</style>
