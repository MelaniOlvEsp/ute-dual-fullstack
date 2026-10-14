<script>
  import { onMount } from 'svelte'
  import { navigate } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { token, user } from '../../stores/auth.js'
  import { homeFor } from '../../../domain/auth/permissions.js'

  // Resuelve la navegación inicial sin depender de un módulo específico.
  onMount(() => {
    const path = get(token) ? homeFor(get(user)) : '/login'
    navigate(path, { replace: true })
  })
</script>
