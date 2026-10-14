# Validación y operación local

Guía de preparación, no registro de comandos ejecutados. Completar valores reales y resultados en C01/C10. No requiere servicios publicados.

## Preparación en C01

1. Inventariar Python/Node/PostgreSQL disponibles y dependencias fijadas por proyecto. No copiar secretos al informe.
2. Crear BD nueva exclusiva del piloto y usuario adecuado; confirmar destino antes de ejecutar SQL.
3. Fijar script de instalación canónico tras reconciliar backend y esquema. No ejecutar todos los scripts de database en orden sin revisión.
4. Crear fixtures sintéticos de coordinador, tutor y dos alumnos de grupos/períodos distintos. Claves de prueba locales no reutilizadas.
5. Configurar variables desde ejemplos sin imprimir secretos. Variables DB_*, SECRET_KEY, FRONTEND_URL, CORS_ORIGINS y VITE_API_URL según configuración real.
6. Si se usa Drive, renovar credenciales y carpeta privada; el nombre histórico GMAIL_CREDENTIALS_PATH no implica envío de correo.
7. Registrar comandos verificados en README_INTEGRACION.md; no asumir que npm ci sirve sin lockfile válido.

## Comprobaciones existentes

Desde ute-api-clean, con entorno virtual y dependencias disponibles:

```text
python -m unittest discover -s tests -q
python -m compileall -q app
uvicorn app.main:app --reload --port 8000
```

Desde ute-dual-frontend, después de instalación reproducible:

```text
npm test
npm run build
npm run dev
```

Desde raíz:

```text
node --test integration-tests/api-contract.test.mjs
```

Estas órdenes se tomaron de la estructura actual. Ejecutarlas es trabajo de C01; podrían revelar fallos. La prueba de contratos usa simulación, no PostgreSQL ni Drive reales.

## Matriz de verificación

| Nivel | Comprobar | Evidencia necesaria |
|---|---|---|
| Dominio | Semanas parciales, límites período, atraso, nota entera, promedio | Tests deterministas con reloj fijo |
| Persistencia | FK, unicidad, versiones, cierre concurrente | PostgreSQL real aislado |
| API | Roles/propiedad, estado cerrado, contratos y errores | Solicitudes reales más tests negativos |
| Archivos | Original y firmado, fallos/reintentos, privados | Lectura binaria real del proveedor elegido |
| UI | Upload, visor, buzón, navegación y cierre | Navegador real, pantallas relevantes sin PII |
| Integral | Incorporación → entrega → revisión → expediente → cierre | Recorrido reproducible con cuentas sintéticas |
| Recuperación | BD y documentos consistentes tras restaurar | Restauración a destino nuevo aislado |

## Recorrido de aceptación local

Crear grupo y alumno; configurar empresa/inicio; registrar alumno; ingresar al foro; descargar plantillas; entregar dos semanas; rechazar una y reenviar; aprobar con firma; comprobar historia y expediente; cerrar recepción con otra entrega pendiente; verificar bloqueo de archivo y aprobación posterior; finalizar; comprobar promedio. Abrir un segundo período según política aprobada y confirmar que el primero no cambia.

Probar también acceso cruzado alumno A/B, rol tutor intentando cierre, fallo de almacenamiento, PDF corrupto, duplicación de envío, conversación completa del buzón y descarga de períodos anteriores.

## Respaldo y restauración

Respaldar PostgreSQL y objetos/documentos referenciados como conjunto consistente; conservar manifiesto de versión. Guardar credenciales por separado de los backups compartibles. Restaurar únicamente a BD y carpeta nuevas de prueba, verificar conteos/referencias y descargar una muestra de originales/firmados. No declarar respaldo recuperable sin probar restauración.

Antes de uso real definir responsable, frecuencia y retención. El piloto local no garantiza disponibilidad cuando se apaga el equipo. Selección de alojamiento gratuito se investiga aparte con límites actuales y consentimiento de publicación.

## Registro en la spec

No registrar contraseñas, tokens, archivos personales ni rutas de credenciales. Incluir fecha, revisión del código, entorno, comando/recorrido, resultado y limitación. Marcar proveedor no utilizado como NO_VERIFICADA. Una prueba de restauración de fixtures no demuestra recuperación de producción.
