<script>
  export let id = '';
  export let label = '';
  export let value = '';
  export let type = 'text';
  export let placeholder = '';
  export let disabled = false;
  export let min = null;
  export let max = null;
  export let isSmall = false;
  export let required = true;
  // Mensaje de error para borde rojo
  export let error = '';
  // Bloquea decimales, negativos y no-dígitos (celular, edad, gastos)
  export let integerOnly = false;

  function onKeyDown(e) {
    if (!integerOnly) return
    // Bloquear: -, +, e, E, .
    if (['-', '+', 'e', 'E', '.'].includes(e.key)) {
      e.preventDefault()
    }
  }

  function onInput(e) {
    if (!integerOnly) return
    const raw = e.target.value
    // Eliminar cualquier carácter no-dígito
    const clean = raw.replace(/\D/g, '')
    if (clean !== raw) {
      // Reasignar forzando reactividad Svelte
      value = clean
    }
  }
</script>

<div class="field" class:field-sm={isSmall}>
  <label for={id}>{label}</label>

  {#if type === 'number'}
    <input
      {id} class="input-plain" class:input-error={error} type="number" {placeholder} {disabled} {min} {max}
      inputmode={integerOnly ? 'numeric' : 'decimal'}
      bind:value
      on:keydown={onKeyDown}
      on:input={onInput}
    />
  {:else if type === 'email'}
    <input
      {id} class="input-plain" class:input-error={error} type="email" {placeholder} {disabled} {min} {max} bind:value
    />
  {:else}
    <input
      {id} class="input-plain" class:input-error={error} type="text" {placeholder} {disabled} {min} {max} bind:value
    />
  {/if}

  {#if error}
    <span class="field-error">{error}</span>
  {/if}
</div>

<style>
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
  .field-sm { max-width: 120px; }
  .req { color: var(--orange); }
  .input-error { border-color: var(--error) !important; box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15) !important; }
  .field-error { font-size: 11px; color: var(--error); font-weight: 500; }
</style>
