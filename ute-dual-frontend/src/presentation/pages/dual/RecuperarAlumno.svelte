<script>
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'

  let matricula = ''
  let provisional = null
  let error = ''
  let working = false

  async function recuperar() {
    error = ''
    provisional = null
    if (!/^\d{9}$/.test(matricula)) {
      error = 'Ingresa una matrícula válida de 9 dígitos.'
      return
    }
    if (!confirm('Esto invalidará la contraseña y sesiones anteriores del alumno. ¿Continuar?')) return
    working = true
    try { provisional = await api.auth.passwordProvisional(matricula) }
    catch (e) { error = e.message }
    finally { working = false }
  }
</script>
<Navbar />
<main style="padding:90px 24px;max-width:620px;margin:auto">
  <h1>Recuperación de acceso de alumnos</h1>
  <p>Solo genera una contraseña provisional para alumnos autorizados y registrados. Entrega la clave personalmente o por un canal seguro.</p>
  <label for="matricula">Matrícula</label>
  <input id="matricula" class="input-plain" bind:value={matricula} maxlength="9" placeholder="123456789" />
  <button class="btn-primary" on:click={recuperar} disabled={working || matricula.length !== 9}>
    {working ? 'Generando...' : 'Generar contraseña provisional'}
  </button>
  {#if error}<p style="color: var(--error-text)">{error}</p>{/if}
  {#if provisional}
    <section style="padding:18px;margin-top:18px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px">
      <strong>Contraseña provisional — visible una sola vez</strong>
      <p>Matrícula: {provisional.matricula}</p>
      <code style="font-size:18px">{provisional.password_temporal}</code>
      <p>El alumno deberá establecer una contraseña nueva al iniciar sesión.</p>
      <button class="btn-primary" on:click={() => provisional = null}>Ya la entregué</button>
    </section>
  {/if}
</main>
