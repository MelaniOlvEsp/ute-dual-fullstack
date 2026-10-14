<script>
  import { onMount } from 'svelte'
  import { navigate } from 'svelte-routing'
  import { isAuthenticated, user } from '../../stores/auth.js'
  import { hasAccess, homeFor } from '../../../domain/auth/permissions.js'

  export let permission = 'authenticated'
  $: allowed = $isAuthenticated && hasAccess($user, permission)

  // Bloquea la vista mientras se resuelven los permisos de la sesión.
  onMount(() => {
    if ($user?.must_change_password) navigate('/cambiar-password', { replace: true })
    else if (!$isAuthenticated) navigate('/login', { replace: true })
    else if (!allowed) navigate(homeFor($user), { replace: true })
  })
</script>

{#if allowed}
  <slot />
{/if}
