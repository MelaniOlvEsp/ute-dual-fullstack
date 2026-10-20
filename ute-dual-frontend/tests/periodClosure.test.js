import test from 'node:test'
import assert from 'node:assert/strict'
import { crearCierrePeriodo } from '../src/application/use-cases/periodClosure.js'

const diferida = () => {
  let resolve, reject
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail })
  return { promise, resolve, reject }
}
const resumen = (id, extras = {}) => ({ periodo: { id, periodo_label: `Período ${id}` },
  puede_cerrar_recepcion: true, puede_finalizar: true, conteos: {}, alumnos: [], ...extras })
function escenario() {
  const solicitudes = [], acciones = []
  const operacion = diferida()
  const cierre = crearCierrePeriodo({
    resumenPeriodo(id) { const d = diferida(); solicitudes.push({ id, ...d }); return d.promise },
    cerrarRecepcion(id) { acciones.push(['cierre', id]); return operacion.promise },
    finalizarEvaluacion(id) { acciones.push(['finalizar', id]); return operacion.promise }
  })
  let estado
  cierre.subscribe(value => { estado = value })
  return { cierre, solicitudes, acciones, operacion, estado: () => estado }
}

test('una respuesta A tardía nunca reemplaza el resumen B', async () => {
  const e = escenario()
  const a = e.cierre.cargar('A'), b = e.cierre.cargar('B')
  e.solicitudes[1].resolve(resumen('B')); await b
  e.solicitudes[0].resolve(resumen('A')); await a
  assert.equal(e.estado().resumen.periodo.id, 'B')
  assert.equal(e.estado().periodoId, 'B')
  assert.equal(e.estado().cargando, false)
})

test('A/B/A distingue solicitudes del mismo ID y conserva el último resumen', async () => {
  const e = escenario()
  const a1 = e.cierre.cargar('A'), b = e.cierre.cargar('B'), a2 = e.cierre.cargar('A')
  e.solicitudes[2].resolve(resumen('A', { marca: 'nueva' })); await a2
  e.solicitudes[0].resolve(resumen('A', { marca: 'vieja' })); await a1
  e.solicitudes[1].resolve(resumen('B')); await b
  assert.equal(e.estado().resumen.marca, 'nueva')
})

test('el finally y el error de A no terminan ni contaminan la carga B', async () => {
  const e = escenario()
  const a = e.cierre.cargar('A'), b = e.cierre.cargar('B')
  e.solicitudes[0].reject(new Error('error obsoleto')); await a
  assert.equal(e.estado().cargando, true)
  assert.equal(e.estado().errorResumen, '')
  assert.equal(e.estado().resumen, null)
  assert.equal(e.cierre.confirmar('cierre'), false)
  e.solicitudes[1].resolve(resumen('B')); await b
  assert.equal(e.estado().resumen.periodo.id, 'B')
})

test('un error antiguo tampoco borra un resumen nuevo ya cargado', async () => {
  const e = escenario()
  const a = e.cierre.cargar('A'), b = e.cierre.cargar('B')
  e.solicitudes[1].resolve(resumen('B')); await b
  e.solicitudes[0].reject(new Error('antiguo')); await a
  assert.equal(e.estado().resumen.periodo.id, 'B')
  assert.equal(e.estado().errorResumen, '')
})

test('un payload de otro período se rechaza y no permite ejecutar', async () => {
  const e = escenario(), carga = e.cierre.cargar('A')
  e.solicitudes[0].resolve(resumen('B')); await carga
  assert.equal(e.estado().resumen, null)
  assert.match(e.estado().errorResumen, /no corresponde/)
  assert.equal(e.cierre.confirmar('cierre'), false)
  assert.equal(await e.cierre.ejecutar(), false)
  assert.deepEqual(e.acciones, [])
})

test('cambiar selección elimina inmediatamente resumen y confirmación; no envía la acción anterior', async () => {
  const e = escenario(), a = e.cierre.cargar('A')
  e.solicitudes[0].resolve(resumen('A')); await a
  assert.equal(e.cierre.confirmar('cierre'), true)
  const b = e.cierre.cargar('B')
  assert.equal(e.estado().confirmacion, null)
  assert.equal(e.estado().resumen, null)
  assert.equal(await e.cierre.ejecutar(), false)
  e.solicitudes[1].resolve(resumen('B')); await b
  assert.equal(await e.cierre.ejecutar(), false)
  assert.deepEqual(e.acciones, [])
})

for (const accion of ['cierre', 'finalizar']) {
  test(`${accion}: usa el ID confirmado, bloquea selección y evita doble envío`, async () => {
    const e = escenario(), carga = e.cierre.cargar('A')
    e.solicitudes[0].resolve(resumen('A')); await carga
    assert.equal(e.cierre.confirmar(accion), true)
    assert.equal(e.estado().confirmacion.etiqueta, 'Período A')
    const envio = e.cierre.ejecutar()
    await e.cierre.cargar('B')
    e.cierre.cancelar()
    assert.equal(e.cierre.confirmar('finalizar'), false)
    assert.equal(await e.cierre.ejecutar(), false)
    assert.equal(e.estado().periodoId, 'A')
    assert.equal(e.estado().confirmacion.periodoId, 'A')
    assert.deepEqual(e.acciones, [[accion, 'A']])
    e.operacion.resolve({ periodo: { id: 'A' } })
    assert.equal(await envio, true)
    assert.match(e.estado().exitoAccion, /Período A/)
    assert.equal(e.estado().confirmacion, null)
    assert.equal(e.estado().ejecutando, false)
  })
}

test('permisos del resumen y acción desconocida no habilitan confirmación', async () => {
  const e = escenario(), carga = e.cierre.cargar('A')
  e.solicitudes[0].resolve(resumen('A', { puede_cerrar_recepcion: false, puede_finalizar: false })); await carga
  for (const accion of ['cierre', 'finalizar', 'otra']) assert.equal(e.cierre.confirmar(accion), false)
  assert.equal(await e.cierre.ejecutar(), false)
  assert.deepEqual(e.acciones, [])
})

test('un fallo limpia confirmación, conserva error al refrescar y exige confirmar otra vez', async () => {
  const e = escenario(), carga = e.cierre.cargar('A')
  e.solicitudes[0].resolve(resumen('A')); await carga
  e.cierre.confirmar('cierre')
  const envio = e.cierre.ejecutar()
  e.operacion.reject(new Error('No disponible'))
  assert.equal(await envio, false)
  const refresco = e.cierre.cargar('A', { conservarMensajes: true })
  e.solicitudes[1].resolve(resumen('A')); await refresco
  assert.equal(e.estado().errorAccion, 'No disponible')
  assert.equal(e.estado().confirmacion, null)
  assert.equal(await e.cierre.ejecutar(), false)
  assert.equal(e.acciones.length, 1)
})

test('vaciar selección o cancelar confirmación no deja una operación ejecutable', async () => {
  const e = escenario(), carga = e.cierre.cargar('A')
  e.solicitudes[0].resolve(resumen('A')); await carga
  e.cierre.confirmar('cierre'); e.cierre.cancelar()
  assert.equal(await e.cierre.ejecutar(), false)
  const antigua = e.cierre.cargar('A')
  await e.cierre.cargar('')
  e.solicitudes[1].resolve(resumen('A')); await antigua
  assert.equal(e.estado().resumen, null)
  assert.equal(e.estado().cargando, false)
  assert.deepEqual(e.acciones, [])
})
