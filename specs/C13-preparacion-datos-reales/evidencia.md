# Evidencia C13 — Preparación para datos reales

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; sin push).
Clases: REAL = PostgreSQL, Compose y Drive reales de una cuenta de pruebas con datos sintéticos, en un proyecto limpio (`c13-origen`, base y carpeta de Drive nuevas); SIMULADA = pruebas con almacenamiento en memoria; NO_VERIFICADA = no observado. Las claves de la prueba eran de usar y tirar (se eliminaron al terminar) y no son las del piloto; no se anotan claves ni identificadores de Drive.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C13-AC1 el respaldo cifrado en Drive no se puede abrir sin la clave | REAL: en el espacio de respaldos hay 14 objetos (volcado, 12 documentos y manifiesto), ninguno `.dump` ni PDF sueltos; el volcado y las copias empiezan con el encabezado de age y no contienen `PGDMP` ni `%PDF`; el manifiesto no contiene claves privadas | `respaldo.ps1`, inspección del espacio de respaldos |
| C13-AC2 restauración aislada con la clave correcta | REAL: «VERIFICADA (respaldo cifrado)»: 12 documentos restaurados y descifrados, 12 referencias con su SHA-256, 6 descargas de muestra correctas; proyecto y carpeta eliminados y sin temporales | `restaurar.ps1 -Identidad` |
| C13-AC3 clave ausente o incorrecta | REAL: sin `-Identidad` y con una clave de otro par la restauración se rechaza (mensaje claro) antes de crear la carpeta o el proyecto; `verificar -Identidad` con la clave incorrecta responde código 3; el respaldo sin clave pública se rechaza (código 1); SIMULADA: 19 pruebas | `restaurar.ps1`, `respaldo.ps1`, `test_c13_cifrado.py` |
| C13-AC4 respaldo sin cifrar (versión 1) | REAL: un respaldo `-SinCifrar` se lista como «SIN CIFRAR» y se restaura sin clave («VERIFICADA (respaldo SIN CIFRAR)»); SIMULADA: manifiesto v1 en las pruebas. Los respaldos de C10 siguen en las carpetas de validación de la cuenta de pruebas, pero ya no se tienen sus identificadores, así que no se pudieron restaurar con este código | `respaldo.ps1 -SinCifrar`, `test_c13_cifrado.py` |
| C13-AC5 endurecimiento | REAL: `verificar-restauracion` ejecutado a mano en el entorno de origen se niega; la poda en simulación funciona; SIMULADA: candado entre respaldo y poda (único, abandonado a las 2 h, la poda se niega con un respaldo en curso), guardas de los tres subcomandos que escriben, etiquetas de prueba reservadas, variantes de prueba fuera de `ids_de` y de la retención, `quitar-prueba` solo con variantes. No se forzó un respaldo y una poda reales a la vez | pruebas y ejecución real |
| C13-AC6 Drive sin caducidad semanal | NO_VERIFICADA: no existe todavía la cuenta de Workspace de la universidad (D2); la guía documenta el cambio (sección 6.3) | guía |
| C13-AC7 guía y lista de comprobación | REAL parcial: la guía de custodia (crear, guardar, probar, perder y rotar la clave) y la lista del paso a datos reales se siguieron en lo que corre aquí (crear el par, respaldar, verificar con y sin clave, restaurar); no se siguió desde cero en un equipo nuevo, ni la copia sellada con una segunda persona ni el cambio a Workspace | `GUIA_DE_USO_Y_OPERACION.md` sección 6 |

## Qué se implementó

- **Cifrado con age (D1):** biblioteca `pyrage` 1.2.5 (age en Rust, sin binarios externos) añadida a `requirements.txt`. `respaldo.py` cifra el volcado (`respaldo-<id>.dump.age`) y cada documento (`doc-<clave>.<huella>.age`) con la clave pública antes de subirlos; el nombre de la copia lleva la huella del destinatario, así que cambiar de clave no mezcla copias. El manifiesto `version: 2` registra el método, la huella del destinatario, la huella del texto cifrado (que `verificar` comprueba sin la clave) y la del contenido (que se comprueba al descifrar). Sin clave pública el respaldo se rechaza; `--sin-cifrar` / `-SinCifrar` produce el formato anterior (`version: 1`).
- **Claves:** `respaldo.ps1 -Orden generar-clave -Salida <ruta>` crea el par: la privada va a la ruta indicada (fuera del repositorio, permisos solo del usuario) y la pública a `.secretos\respaldo_clave_publica.txt`; no sobrescribe y no imprime la privada. `restaurar.ps1 -Identidad <ruta>` copia la clave a la carpeta temporal solo mientras restaura y la borra al terminar o al fallar.
- **Endurecimiento:** los subcomandos que escriben (`restaurar-documentos`, `verificar-restauracion`, `descartar-carpeta`) solo corren dentro de `restaurar.ps1` (variable `RESPALDO_ENTORNO`) y se niegan si el destino es la carpeta de los respaldos; candado `en-curso.lock` entre `crear` y `podar`; etiquetas de prueba reservadas, variantes fuera de la retención y de «el más reciente».
- **Documentación:** sección 6 de la guía rehecha (custodia de la clave, tabla de órdenes, lista de comprobación del paso a datos reales y pendiente de Drive), registro de respaldos, validación y operación.

## Defectos encontrados durante la prueba real (corregidos)

- `restaurar.ps1` borraba la copia temporal de la clave privada al terminar de restaurar el volcado, antes de restaurar los documentos: la restauración con la clave correcta se rechazaba. Ahora la clave se borra solo al terminar o al fallar (`Limpiar-Identidad`).

## Revisión y corrección (2026-10-17)

La revisión técnica (mismo agente, no independiente) concluyó CHANGES_REQUESTED con un defecto material. **M1:** la guía decía «se crea un par nuevo» para la pérdida o la rotación de la clave, pero generar-clave no sobrescribe y el mensaje no nombraba el archivo que hay que apartar; seguirla al pie de la letra fallaba justo en esa situación. **Corrección:** la sección 6.1 tiene un paso 6 con el procedimiento completo (apartar la pública con fecha, otra ruta de salida, guardar la nueva, respaldar y verificar con la clave nueva, registrar y retirar a mano los respaldos viejos), y el mensaje de generar-clave nombra .secretos\respaldo_clave_publica.txt y remite a la guía; comprobado con un archivo marcador (se rechaza y no se creó ninguna clave; el marcador se eliminó). También se corrigió el texto de AC4 sobre los respaldos de C10. Se comprobó además que probar-fallos funciona sobre un respaldo cifrado (detecta las cuatro alteraciones y deja una variante que ids_de excluye). Revisión focal (mismo agente): cambio de documentación y de un mensaje, sin hallazgos nuevos.

## Pruebas

Backend: 300 pruebas OK con 1 omitida (281 + 19 de `test_c13_cifrado.py`: cifrado de ida y vuelta, clave incorrecta, nada legible en el almacenamiento, verificación con y sin clave, texto cifrado alterado, documento o volcado ausente, formato, compatibilidad con la versión 1, variantes de prueba, candado, poda, guardas, etiquetas reservadas); también con `ALMACENAMIENTO=memoria`. Sin cambios de API, de contrato, de base de datos ni de interfaz.

## Lo que NO se probó

- **C13-AC6:** Drive sin caducidad semanal (falta la cuenta de Workspace).
- La copia sellada con una segunda persona y la prueba de la clave en otro equipo; la guía desde cero.
- Un respaldo y una poda reales ejecutándose a la vez (solo simulado); un respaldo con actividad real sobre los documentos mientras se cifra.
- Rendimiento con muchos o con grandes documentos (el cifrado se hace en memoria: PDF de hasta 10 MB y un volcado pequeño); la caducidad real del permiso de Drive, la cuota y los límites de Drive.
- Hospedaje, aviso de privacidad y cifrado de la base viva y del tráfico (fuera de alcance).

## Decisiones e interpretaciones

D1 y D2 de la spec (2026-10-17). Interpretaciones al implementar: (1) age se usa a través de `pyrage` (biblioteca) y no del binario `age`, para no añadir una herramienta a la imagen; el formato es el mismo y la clave privada también se puede usar con la herramienta `age`; (2) la clave pública se toma de `RESPALDO_CLAVE_PUBLICA` o de `.secretos/respaldo_clave_publica.txt` (no es secreta); (3) el cifrado se hace antes de subir y en memoria (tamaño máximo de documento 10 MB); (4) la integridad se comprueba sin la clave con las huellas del texto cifrado y con la clave con las del contenido; (5) un candado de 2 horas evita que la poda borre copias de un respaldo en curso; (6) la clave privada nunca se pasa por la línea de comandos ni por una variable de entorno: solo por un archivo temporal que se borra.
## Acta de cierre

La segunda revisión técnica (mismo agente) concluyó APPROVED el 2026-10-17 sin defectos materiales, después de corregir la guía de rotación de la clave. El responsable otorgó la aprobación de cierre con `CLOSE C13` sabiendo que no se verificaron Drive sin caducidad semanal (falta la cuenta de Workspace), la copia sellada con una segunda persona, un respaldo con actividad real mientras se cifra, el rendimiento con archivos grandes ni el procedimiento de rotación de punta a punta. C13 queda DONE; el sistema sigue sin ser apto para datos reales hasta cumplir la lista de comprobación de la guía (6.2). El commit local se hizo con el cierre; no hay push.

