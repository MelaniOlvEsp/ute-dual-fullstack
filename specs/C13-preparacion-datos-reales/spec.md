# C13 — Preparación para datos reales

Estado: DONE
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C12 DONE (2026-10-17) y C10 DONE (respaldo y restauración probados con datos sintéticos). D1 y D2 resueltas el 2026-10-17 (tal como se recomendó); sin decisiones bloqueantes: solo falta la orden `IMPLEMENT C13` para pasar a READY. El punto 3 (Drive sin caducidad semanal) queda condicionado a que exista la cuenta de Workspace. El plan maestro terminaba en C12; esta spec reúne lo que C10 dejó como condición antes de usar datos reales (D3 de C10: cifrar los respaldos) y los pendientes de operación.

## Problema y resultado esperado

El piloto se validó solo con datos sintéticos y con tres condiciones que impiden usarlo con datos reales de alumnos:

1. **Los respaldos no van cifrados.** El volcado de PostgreSQL contiene datos personales y hashes de contraseñas, y las copias de los documentos son los PDF de los reportes. Están en una carpeta privada de Drive, pero C10 (D3) dejó escrito que hay que cifrarlos antes de usar datos reales.
2. **El permiso de Drive caduca cada 7 días.** Con la aplicación de Google en modo de prueba, el token se pierde a la semana y el sistema deja de guardar reportes hasta volver a autorizar (503 a propósito). Con datos reales eso no es operable.
3. **Tres observaciones menores del respaldo** que C10 dejó abiertas: los subcomandos que se ejecutan a mano no comprueban en qué entorno corren (`verificar-restauracion` inserta un usuario y `restaurar-documentos` escribe en el almacenamiento del entorno), `probar-fallos` y `quitar-prueba` no están en la guía (y la variante «dañada» puede quedar como «más reciente»), y la poda puede chocar con un respaldo en curso.

Resultado esperado: respaldos cifrados de punta a punta (en Drive solo hay texto cifrado y quien no tenga la clave no puede leerlos), una restauración que pide la clave y falla con un mensaje claro si falta o es incorrecta, un acceso a Drive que no caduca cada semana (según D2), los subcomandos con guardas y la guía de operación al día, con una lista de comprobación para el paso a datos reales.

## Fuentes y alcance

US/RN/AC: sin AC nuevos del producto; RN-25 y RN-29 (conservación y base nueva), AC-24 (restauración) y la decisión D3 de [C10](../C10-validacion-integral-local/spec.md).
Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [guía de uso y operación](../../docs/construction/GUIA_DE_USO_Y_OPERACION.md), [registro de respaldos](../../docs/construction/REGISTRO_DE_RESPALDOS.md), [evidencia C10](../C10-validacion-integral-local/evidencia.md), [C10A](../C10A-almacenamiento-drive/spec.md), [ADR-08 y ADR-09](../../docs/analysis/DECISIONES_DE_ARQUITECTURA.md).

Incluye:

1. **Respaldo cifrado:** `respaldo.py` cifra el volcado y cada copia de documento antes de subirlos a Drive, con una clave pública (la máquina de respaldo no necesita el secreto); el manifiesto registra el método y las huellas del texto cifrado y del contenido; `restaurar` descifra con la clave privada que aporta el responsable. Cambio del formato del manifiesto con versión y compatibilidad con los respaldos sin cifrar ya hechos (se pueden restaurar y se marcan «sin cifrar»).
2. **Custodia de la clave:** procedimiento de generación, almacenamiento fuera del equipo y de Drive, copia de seguridad de la clave, prueba periódica y qué hacer si se pierde (sin la clave no hay restauración: se documenta con claridad).
3. **Identidad de Drive sin caducidad semanal** (según D2): configuración y guía del cambio de autenticación sin cambiar los casos de uso (ya previsto en C10A D1).
4. **Endurecimiento de los subcomandos de respaldo:** protección contra ejecutar a mano los que escriben en una base o carpeta que no es de restauración, documentación de `probar-fallos` y `quitar-prueba` y exclusión de las variantes de prueba de la retención y de «el más reciente», y la poda que no elimina copias de un respaldo en curso.
5. **Lista de comprobación del paso a datos reales** en la guía: base nueva (ADR-09), cifrado activo, prueba de restauración con clave, cuenta de Drive definitiva, cuentas iniciales, respaldos programados por el responsable, qué hacer ante pérdida de clave o de acceso a Drive.

Excluye: elección y contratación de hospedaje (se investiga aparte con límites actuales y consentimiento de publicación), aviso de privacidad y consentimiento de datos personales (decisión institucional que no está en el repositorio), automatización de los respaldos programados (ADR-08), migración de datos de la demo (ADR-09: base nueva), H5 y la prueba con lector de pantalla (accesibilidad), cifrado de la base viva en reposo y del tráfico (hospedaje) y móvil físico.

## Decisiones

Confirmadas: la clave privada nunca viaja con el respaldo ni se guarda en el repositorio, en `.secretos` de la máquina de respaldo ni en Drive; el cifrado se hace antes de subir (Drive solo ve texto cifrado); un respaldo no cifrado se rechaza cuando el cifrado está activado; los datos reales solo se cargan en una base nueva.

Resueltas por el responsable el 2026-10-17, tal como se recomendó (D1: opción a, age con la clave pública en la máquina de respaldo y custodia del responsable con una copia sellada; D2: opción a, cuenta de Workspace de la universidad, y si aún no existe el punto 3 queda pendiente de la cuenta). Se conserva el texto de las opciones:

- **D1 — Herramienta y custodia del cifrado.** Opciones: (a) **age** (clave pública de destinatario; la máquina solo guarda la pública; el responsable guarda la identidad en un lugar fuera de línea y una copia sellada en otro) con un binario pequeño en la imagen; (b) GPG (más conocido y más pesado de operar); (c) cifrar con una contraseña (más simple, pero la contraseña tendría que vivir en la máquina que respalda). Y la custodia: ¿quién guarda la clave privada y su copia? Recomendación: (a) con el responsable del proyecto como custodio y una copia sellada con una segunda persona designada por la universidad (si la hay), para que el respaldo no dependa de una sola persona.
- **D2 — Cuenta de Drive para el uso real.** El permiso de una aplicación de Google en modo de prueba caduca a los 7 días (según foros y documentación de terceros; se confirma contra la documentación oficial de Google al implementar). Opciones: (a) una cuenta de Workspace de la universidad con la aplicación como «interna» (sin caducidad semanal) y cambio solo de configuración; (b) publicar la aplicación con la misma cuenta personal (los reportes de la comunidad indican que el token deja de caducar, pero Google puede exigir verificación y no es una cuenta institucional); (c) seguir en modo de prueba con reautorización semanal (no apto para datos reales). Recomendación: (a); si todavía no hay cuenta institucional, esta parte queda condicionada: C13 se puede aprobar con los puntos 1, 2, 4 y 5 y dejar el 3 como «pendiente de la cuenta».

Propuestas técnicas incluidas en esta aprobación (sujetas a D1 y D2): cifrado en flujo del volcado y de cada documento antes de subirlo; manifiesto con `version: 2`, método y huellas; restauración que acepta ambas versiones; prueba de ida y vuelta con Drive real, con clave incorrecta y sin clave; nada de la clave privada en los registros ni en la salida.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (guías de terceros; criterio de diseño, no norma). La búsqueda no devolvió documentación oficial de las herramientas, así que lo específico de cada una se confirma al implementar:

- [Mejores prácticas de gestión de claves (SSL.com)](https://www.ssl.com/article/key-management-best-practices/), [10 prácticas de gestión de claves (Fortanix)](https://www.fortanix.com/blog/10-key-management-best-practices-you-should-know) y [16 prácticas (phoenixNAP)](https://phoenixnap.com/blog/encryption-key-management-best-practices): generar claves con buena aleatoriedad, no guardarlas en texto plano junto a los datos, rotarlas y retirarlas, revocar las comprometidas y comprobar periódicamente que el respaldo se puede abrir.
- [Foro de rclone: la autorización de Drive caduca cada 7 días](https://forum.rclone.org/t/google-drive-requires-manual-refresh-every-7-days/29023) y [discusión sobre el token tras unos días](https://forum.rclone.org/t/google-drive-cannot-refresh-token-after-a-few-days/22036/18): con la aplicación de OAuth en estado de prueba el token de actualización caduca a los 7 días; publicar la aplicación lo evita según los usuarios, pero es relato de terceros y puede requerir verificación. Se confirma contra la documentación oficial de Google antes de decidir.
- Lo que la búsqueda no cubrió y se verifica al implementar: el formato y la especificación de la herramienta de cifrado elegida, y la diferencia entre cuenta de servicio, aplicación interna de Workspace y aplicación publicada para el alcance `drive.file`.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: sin cambios en la API (73 rutas); el cifrado es del procedimiento de respaldo, no de las rutas.
Datos, restricciones y conservación: manifiesto `version: 2` con método de cifrado y huellas del texto cifrado y del contenido; los respaldos `version: 1` se siguen pudiendo verificar y restaurar; los documentos de la base y de Drive vivo no cambian.
Permisos y estados: lo ejecuta el responsable con acceso a la máquina; no son rutas de la API.
Archivos/módulos previstos: `ute-api-backend/scripts/respaldo.py` y `scripts/respaldo.ps1` y `restaurar.ps1`, la imagen de la API (binario de cifrado), `docker-compose.yml` (variable de la clave pública), pruebas de `tests/test_c10_respaldo.py` y nuevas, `GUIA_DE_USO_Y_OPERACION.md`, `REGISTRO_DE_RESPALDOS.md` y `VALIDACION_Y_OPERACION_LOCAL.md`; la configuración de Drive según D2.
Comportamiento ante fallos/reintentos: sin la clave pública no se crea el respaldo; con la clave privada ausente o incorrecta la restauración se rechaza antes de tocar la base de prueba; un cifrado interrumpido no deja manifiesto (el respaldo no existe, como hoy).

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C13-AC1 | Un respaldo cifrado se sube a Drive; lo que hay en Drive no se puede abrir como volcado ni como PDF sin la clave | Drive real, base nueva, datos sintéticos | REAL (14 objetos en Drive, todos cifrados) |
| C13-AC2 | La restauración aislada con la clave correcta recupera base y documentos (conteos, SHA-256, descargas de muestra) | Compose y Drive reales | REAL |
| C13-AC3 | Clave ausente o incorrecta: la restauración se rechaza con un motivo claro antes de tocar nada | Fallos reales | REAL y SIMULADA |
| C13-AC4 | Un respaldo `version: 1` sin cifrar sigue verificándose y restaurándose y se marca «sin cifrar» | Respaldo de C10 | REAL y SIMULADA |
| C13-AC5 | Los subcomandos que escriben se niegan a correr fuera de un entorno de restauración; la poda no elimina copias de un respaldo en curso; las variantes de prueba no cuentan para la retención | Pruebas unitarias y reales | REAL parcial y SIMULADA (no se forzó un respaldo y una poda reales a la vez) |
| C13-AC6 | La cuenta de Drive no caduca cada 7 días (según D2) | Cuenta definitiva; si no existe, NO_VERIFICADA | NO_VERIFICADA (falta la cuenta de Workspace) |
| C13-AC7 | La guía y la lista de comprobación del paso a datos reales se siguen sin pasos implícitos, incluida la custodia y la prueba de la clave | Revisión documental y ejecución de la guía | REAL parcial (sin la copia sellada ni desde cero) |

## Evidencia de implementación

Implementada el 2026-10-17 y verificada con Drive real en un entorno limpio; ver [evidencia C13](evidencia.md) (cifrado, restauración con clave, rechazos, endurecimiento, defecto hallado y corregido, lo no probado). C13-AC6 (Drive sin caducidad) queda NO_VERIFICADA por falta de la cuenta de Workspace. Revisión: pendiente. Sin commit ni push.

## Revisión

Veredicto: APPROVED (segunda revisión, 2026-10-17).
Revisor y modalidad (mismo agente / independiente): el mismo agente que implementó; técnica (sin interfaz ni PDF, así que sin revisión visual); no es una revisión independiente.
Hallazgos materiales: primera revisión: la guía no tenía el procedimiento para rehacer o rotar la clave y el mensaje de `generar-clave` no nombraba el archivo que hay que apartar. Segunda: sin defectos.
Correcciones y verificación focal: paso 6 de la sección 6.1 de la guía, mensaje de `generar-clave` y texto de AC4; `probar-fallos` comprobado sobre un respaldo cifrado; 300 pruebas de backend OK y cifrado, restauración con clave y rechazos verificados con Drive real.
Limitaciones previstas: no cubre hospedaje, cifrado de la base viva ni el aviso de privacidad; la pérdida de la clave privada hace irrecuperables los respaldos cifrados; sin cuenta institucional el punto 3 queda pendiente.

## Aprobaciones y cierre

Aprobación de implementación: D1 y D2 resueltas el 2026-10-17; el responsable autorizó la implementación con `IMPLEMENT C13` el 2026-10-17: sin decisiones bloqueantes, la spec pasó de DRAFT a READY y a IN_PROGRESS el mismo día. Sin commit ni push.
Aprobación de cierre: el responsable la otorgó con `CLOSE C13` el 2026-10-17, tras la segunda revisión APPROVED y sabiendo lo que no se verificó: Drive sin caducidad semanal (C13-AC6, falta la cuenta de Workspace de la universidad), la copia sellada con una segunda persona, un respaldo con actividad real mientras se cifra, el rendimiento con archivos grandes y el procedimiento de rotación de punta a punta. C13 queda DONE con esas limitaciones: **el sistema sigue sin ser apto para datos reales** hasta que se cumpla la lista de comprobación de la guía (6.2), en particular la cuenta de Workspace. El commit local se hizo con el cierre; no hay push.
Resumen final: respaldos cifrados con age (volcado y documentos cifrados antes de subir; clave pública en la máquina y clave privada con el responsable), restauración que exige la clave y se rechaza antes de crear nada si falta o es incorrecta, compatibilidad con los respaldos sin cifrar, subcomandos con guardas, candado entre respaldo y poda, etiquetas de prueba reservadas, guía de custodia de la clave y lista de comprobación del paso a datos reales; 300 pruebas de backend, verificación real con Drive. Pendiente: Drive sin caducidad semanal.
Siguiente spec: el hospedaje y el aviso de privacidad no están en el plan maestro; se investigan aparte con límites actuales y consentimiento de publicación cuando el responsable decida publicarlo.
Commit/push: commit local con el cierre; push no autorizado.
