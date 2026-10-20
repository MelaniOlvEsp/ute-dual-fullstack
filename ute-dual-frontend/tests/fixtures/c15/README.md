# Preview de regresión C15

Desde `ute-dual-frontend`, ejecutar `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5185 --strictPort` y abrir `http://127.0.0.1:5185/tests/fixtures/c15/index.html`.

Se monta el componente real `PeriodosDual` dentro de `Router`, con API y usuario sintéticos. `fetch` se rechaza para evitar cualquier llamada al backend. No se abren, cierran ni finalizan períodos reales.

1. Con A seleccionado, marcar «Retener próxima carga A», seleccionar B, seleccionar A (queda cargando) y seleccionar B otra vez.
2. Liberar respuesta A: deben seguir B, sus fechas y sus 20 semanas. Abrir «Finalizar evaluación»: debe nombrar Mayo–Agosto 2027.
3. Confirmar: el control de prueba muestra `finalizar enviado a B`; selector, apertura y doble confirmación deshabilitados. Completar operación simulada: B queda finalizado.
4. Seleccionar A, abrir «Cerrar recepción» y cambiar a B: debe desaparecer la confirmación. Volver a A, confirmar cierre: el control muestra `cierre enviado a A`. Completar: solo A queda cerrado.

Las respuestas/error A/B/A, doble envío, permisos y fallos se prueban automáticamente en `tests/periodClosure.test.js` sin navegador. Este preview permite repetir la revisión visual y del cableado del componente.
