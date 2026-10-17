<script>
  import { onMount } from 'svelte'
  import { navigate } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated, isCoordinadorDual } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'

  let nombre = ''
  let email = ''
  let tutores = []
  let temporal = null
  let loading = false
  let saving = false
  let error = ''
  let message = ''

  onMount(async () => {
    if (!get(isAuthenticated) || !get(isCoordinadorDual)) {
      navigate('/login', { replace: true })
      return
    }
    await cargar()
  })

  async function cargar() {
    loading = true
    try { tutores = await api.auth.listarTutores() }
    catch (e) { error = e.message }
    finally { loading = false }
  }

  async function crear() {
    error = ''
    message = ''
    temporal = null
    saving = true
    try {
      temporal = await api.auth.crearTutor({ nombre, email })
      message = 'Tutor académico registrado. Entrega la clave provisional de forma segura.'
      nombre = ''
      email = ''
      await cargar()
    } catch (e) { error = e.message }
    finally { saving = false }
  }

  async function eliminar(id) {
    if (!confirm('¿Revocar acceso de este tutor académico?')) return
    temporal = null
    try {
      await api.auth.eliminarTutor(id)
      await cargar()
    } catch (e) { error = e.message }
  }
</script>

<svelte:head><title>Tutores académicos | Portal Dual</title></svelte:head>
<Navbar />
<main class="main-container">
  <div class="content-wrapper">
    <PageHeader title="Cuentas de tutores académicos" subtitle="Solo Coordinación Dual puede crear y revocar cuentas de tutores" />
    {#if error}<p class="error-msg">{error}</p>{/if}
    {#if message}<p class="success-msg">{message}</p>{/if}
    <div class="split-layout">
      <section class="panel-card">
        <h2>Agregar tutor académico</h2>
        <label for="nombre">Nombre completo</label>
        <input id="nombre" class="input-plain" bind:value={nombre} />
        <label for="email">Correo institucional</label>
        <input id="email" class="input-plain" type="email" bind:value={email} placeholder="tutor@ute.edu.mx" />
        <button class="btn-primary" disabled={saving || !nombre.trim() || !email.trim()} on:click={crear}>
          {saving ? 'Creando...' : 'Crear cuenta de tutor'}
        </button>
        {#if temporal}
          <div class="success-box">
            <strong>Contraseña provisional — visible una sola vez</strong>
            <p>Usuario: {temporal.email}</p>
            <code>{temporal.password_temporal}</code>
            <p>El tutor deberá cambiarla al iniciar sesión. Guárdala por un medio seguro.</p>
            <button class="btn-primary" on:click={() => temporal = null}>Ya la entregué</button>
          </div>
        {/if}
      </section>
      <section class="panel-card">
        <h2>Directorio de tutores</h2>
        {#if loading}<p>Cargando...</p>
        {:else if tutores.length === 0}<p>No hay tutores registrados.</p>
        {:else}
          <div class="table-scroll-area" role="region" tabindex="0" aria-label="Directorio de tutores">
            <table class="data-table">
              <thead><tr><th>Nombre</th><th>Correo</th><th class="col-accion">Acción</th></tr></thead>
              <tbody>
                {#each tutores as tutor}
                  <tr>
                    <td>{tutor.nombre}</td><td>{tutor.email}</td>
                    <td class="col-accion"><button class="btn-outline" on:click={() => eliminar(tutor.id)}>Dar de baja</button></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>
    </div>
  </div>
</main>
<style>
  .main-container { padding-top: 56px; min-height: 100vh; background: var(--bg-page); }
  .content-wrapper { max-width: 1100px; margin: 0 auto; padding: 32px 24px; display: flex; flex-direction: column; gap: 20px; }
  .split-layout { display: grid; grid-template-columns: 380px 1fr; gap: 24px; align-items: start; }
  .panel-card { min-width: 0; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 24px; display: flex; flex-direction: column; gap: 14px; }
  .table-scroll-area { overflow-x: auto; }
  .data-table { border-collapse: collapse; width: 100%; }
  .data-table td,.data-table th { padding: 12px; border-bottom: 1px solid var(--border); text-align: left; }
  .success-box { background: var(--bg-page); border: 1px solid var(--border); border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 8px; overflow-wrap: anywhere; }
  .success-msg { padding: 12px; color: var(--success-text); }
  .error-msg { color: var(--error-text); }
  @media(max-width: 860px) { .split-layout { grid-template-columns: minmax(0, 1fr); } }
  @media(max-width: 480px) { .content-wrapper { padding: 24px 16px; } .panel-card { padding: 18px; } }
</style>
