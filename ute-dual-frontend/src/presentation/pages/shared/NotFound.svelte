<script>
  import { navigate } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated } from '../../stores/auth.js'
  import Navbar from '../../components/layout/Navbar.svelte'

  function irInicio() {
    if (get(isAuthenticated)) {
      navigate('/foro', { replace: true })
    } else {
      navigate('/login', { replace: true })
    }
  }
</script>

<svelte:head>
  <title>Página no encontrada | Portal UTE</title>
</svelte:head>

<Navbar />

<main class="main">
  <div class="notfound">
    <h1 class="code">404</h1>
    <p class="msg">Esta página no existe o fue movida.</p>
    <button class="btn-primary" on:click={irInicio}>
      Volver al inicio
    </button>
  </div>
</main>

<style>
  .main {
    padding-top: 56px;
    min-height: 100vh;
    background: var(--bg-page);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .notfound {
    text-align: center;
    padding: 40px;
  }
  .code {
    font-size: 72px;
    font-weight: 800;
    color: var(--orange);
    margin: 0 0 8px;
    line-height: 1;
  }
  .msg {
    font-size: 16px;
    color: var(--text-secondary);
    margin: 0 0 24px;
  }
  .btn-primary {
    font-family: var(--font);
    font-size: 14px;
    font-weight: 600;
    padding: 12px 24px;
    background: var(--orange);
    color: #fff;
    border: none;
    border-radius: var(--radius-input);
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-primary:hover {
    background: var(--orange-hover);
  }
</style>
