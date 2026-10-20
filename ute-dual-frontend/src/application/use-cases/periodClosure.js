// Controla la identidad del resumen y de la confirmación (C15). Sin dependencia de UI o transporte.
export function crearCierrePeriodo(dual) {
  let estado = {
    periodoId: '', resumen: null, cargando: false, errorResumen: '',
    confirmacion: null, ejecutando: false, errorAccion: '', exitoAccion: ''
  }
  let secuencia = 0
  const oyentes = new Set()
  function publicar(cambios) {
    estado = { ...estado, ...cambios }
    for (const escuchar of oyentes) escuchar(estado)
  }
  function permitido(accion) {
    const r = estado.resumen
    return Boolean(r && r.periodo.id === estado.periodoId && !estado.cargando &&
      (accion === 'cierre' ? r.puede_cerrar_recepcion : accion === 'finalizar' && r.puede_finalizar))
  }
  return {
    subscribe(escuchar) {
      oyentes.add(escuchar)
      escuchar(estado)
      return () => oyentes.delete(escuchar)
    },
    async cargar(id, { conservarMensajes = false } = {}) {
      if (estado.ejecutando) return
      const solicitud = ++secuencia
      publicar({ periodoId: id, resumen: null, confirmacion: null, cargando: Boolean(id), errorResumen: '',
        ...(!conservarMensajes ? { errorAccion: '', exitoAccion: '' } : {}) })
      if (!id) return
      const vigente = () => solicitud === secuencia && id === estado.periodoId
      try {
        const resumen = await dual.resumenPeriodo(id)
        if (!vigente()) return
        if (resumen?.periodo?.id !== id) throw new Error('El resumen no corresponde al período seleccionado. Vuelve a seleccionarlo.')
        publicar({ resumen })
      } catch (e) {
        if (vigente()) publicar({ resumen: null, errorResumen: e.message || 'No se pudo cargar el resumen del período.' })
      } finally {
        if (vigente()) publicar({ cargando: false })
      }
    },
    confirmar(accion) {
      if (estado.ejecutando || !permitido(accion)) return false
      publicar({ confirmacion: Object.freeze({ accion, periodoId: estado.periodoId,
        etiqueta: estado.resumen.periodo.periodo_label }), errorAccion: '', exitoAccion: '' })
      return true
    },
    cancelar() {
      if (!estado.ejecutando) publicar({ confirmacion: null })
    },
    async ejecutar() {
      const objetivo = estado.confirmacion
      if (estado.ejecutando) return false
      if (!objetivo || objetivo.periodoId !== estado.periodoId || !permitido(objetivo.accion)) {
        publicar({ confirmacion: null, errorAccion: 'Selecciona el período y confirma la acción de nuevo.' })
        return false
      }
      publicar({ ejecutando: true, errorAccion: '', exitoAccion: '' })
      try {
        if (objetivo.accion === 'cierre') await dual.cerrarRecepcion(objetivo.periodoId)
        else await dual.finalizarEvaluacion(objetivo.periodoId)
        publicar({ exitoAccion: objetivo.accion === 'cierre'
          ? `Recepción de "${objetivo.etiqueta}" cerrada. El tutor puede seguir revisando lo recibido.`
          : `Evaluación de "${objetivo.etiqueta}" finalizada. Los promedios quedaron finales.` })
        return true
      } catch (e) {
        publicar({ errorAccion: e.message || 'No se pudo completar la acción.' })
        return false
      } finally {
        publicar({ ejecutando: false, confirmacion: null })
      }
    }
  }
}
