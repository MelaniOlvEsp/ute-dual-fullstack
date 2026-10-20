<script>
  import { Router } from 'svelte-routing'
  import PeriodosDual from '../../../src/presentation/pages/dual/PeriodosDual.svelte'
  import { api } from '../../../src/composition/api.js'
  import { user } from '../../../src/presentation/stores/auth.js'

  let retenerA = false, pendienteA = null, pendienteAccion = null, resultado = 'Sin acciones'
  const periodos = [
    { id: 'A', periodo_label: 'Enero-Abril 2027', recepcion: 'abierta', evaluacion: 'en_curso', fecha_inicio: '2027-01-01', fecha_fin: '2027-04-30' },
    { id: 'B', periodo_label: 'Mayo-Agosto 2027', recepcion: 'cerrada', evaluacion: 'en_curso', fecha_inicio: '2027-05-01', fecha_fin: '2027-08-31' }
  ]
  const resumen = id => ({ periodo: { ...periodos.find(p => p.id === id) },
    conteos: { obligaciones: id === 'A' ? 10 : 20, recibidas: 0, pendientes_revision: 0, aprobadas: 0,
      rechazadas: 0, sin_entrega: 0, no_recibidas_por_cierre: 0 }, alumnos: [],
    puede_cerrar_recepcion: periodos.find(p => p.id === id).recepcion === 'abierta',
    puede_finalizar: periodos.find(p => p.id === id).recepcion === 'cerrada' && periodos.find(p => p.id === id).evaluacion !== 'finalizada' })
  const perfil = { nombre: 'Coordinación sintética C15', roles: { coordinador_dual: true } }
  user.set(perfil)
  api.auth.me = async () => perfil
  api.dual.cuatrimestreActual = async () => ({ ...periodos[0], abierto: periodos[0].recepcion === 'abierta', cerrado: periodos[0].recepcion === 'cerrada' })
  api.dual.periodosEstado = async () => periodos.map(p => ({ ...p }))
  api.dual.resumenPeriodo = async id => {
    if (id === 'A' && retenerA) {
      retenerA = false
      return new Promise(resolve => { pendienteA = () => { resolve(resumen('A')); pendienteA = null } })
    }
    return resumen(id)
  }
  const ejecutar = (accion, id) => new Promise(resolve => {
    resultado = `${accion} enviado a ${id}`
    pendienteAccion = () => {
      const p = periodos.find(p => p.id === id)
      if (accion === 'cierre') p.recepcion = 'cerrada'
      else p.evaluacion = 'finalizada'
      pendienteAccion = null
      resolve({ periodo: { ...p } })
    }
  })
  api.dual.cerrarRecepcion = id => ejecutar('cierre', id)
  api.dual.finalizarEvaluacion = id => ejecutar('finalizar', id)
  api.dual.abrirCuatrimestre = async () => { throw new Error('Apertura fuera del preview C15') }
</script>

<aside class="controles" aria-label="Controles de prueba C15">
  <strong>PRUEBA C15 · datos y API simulados</strong>
  <label><input type="checkbox" bind:checked={retenerA}> Retener próxima carga A</label>
  <button disabled={!pendienteA} on:click={() => pendienteA()}>Liberar respuesta A</button>
  <button disabled={!pendienteAccion} on:click={() => pendienteAccion()}>Completar operación simulada</button>
  <output aria-live="polite">{resultado}</output>
</aside>
<Router><PeriodosDual /></Router>
<style>
  .controles { position: relative; z-index: 100; margin-top: 64px; padding: 16px; background: #fff4d6; color: #222; display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
  button { padding: 6px; }
</style>
