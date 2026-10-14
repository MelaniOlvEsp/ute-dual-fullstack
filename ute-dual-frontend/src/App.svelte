<script>
  import { Router, Route } from 'svelte-routing'
  import Login from './presentation/pages/auth/Login.svelte'
  import Register from './presentation/pages/auth/Register.svelte'
  import ChangePassword from './presentation/pages/auth/CambiarPassword.svelte'
  import Forum from './presentation/pages/foro/Foro.svelte'
  import DualReports from './presentation/pages/dual/ReportesDual.svelte'
  import DualCoordinator from './presentation/pages/dual/CoordinadorDual.svelte'
  import CareerCoordinator from './presentation/pages/dual/CoordinadorCarrera.svelte'
  import ManageUsers from './presentation/pages/dual/GestionTutores.svelte'
  import ResetStudent from './presentation/pages/dual/RecuperarAlumno.svelte'
  import NotFound from './presentation/pages/shared/NotFound.svelte'
  import ProtectedPage from './presentation/components/routing/ProtectedPage.svelte'
  import HomeRedirect from './presentation/components/routing/HomeRedirect.svelte'
</script>

<Router>
  <Route path="/" component={HomeRedirect} />
  <Route path="/login" component={Login} />
  <Route path="/register" component={Register} />
  <Route path="/cambiar-password" component={ChangePassword} />
  <Route path="/foro">
    <ProtectedPage><Forum /></ProtectedPage>
  </Route>
  <Route path="/dual/reportes">
    <ProtectedPage permission="dual-student"><DualReports /></ProtectedPage>
  </Route>
  <Route path="/dual/tutor">
    <ProtectedPage permission="tutor"><DualCoordinator /></ProtectedPage>
  </Route>
  <Route path="/dual/carrera">
    <ProtectedPage permission="files"><CareerCoordinator /></ProtectedPage>
  </Route>
  <Route path="/dual/accesos">
    <ProtectedPage permission="tutor"><ResetStudent /></ProtectedPage>
  </Route>
  <Route path="/dual/tutores">
    <ProtectedPage permission="coordinator"><ManageUsers /></ProtectedPage>
  </Route>
  <Route component={NotFound} />
</Router>
