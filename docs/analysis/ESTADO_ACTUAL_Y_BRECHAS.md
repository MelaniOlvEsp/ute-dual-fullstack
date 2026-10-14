# Estado actual y brechas

Corte: 14/10/2026. Inspección estática de archivos; no se ejecutó la aplicación ni SQL. Los fallos reportados por el usuario pertenecen a la demo anterior y deben reproducirse.

## Inventario

| Área | Evidencia local | Estado y brecha |
|---|---|---|
| Stack | ute-api-clean y ute-dual-frontend | FastAPI/PostgreSQL y Svelte 4/Vite existentes, organizados por capas. |
| Accesos | app/domain/roles.py; consultas auth.py | Tres roles existen. Propuesta DB y backend difieren en columnas/baja de cuenta. |
| Grupos/empresa | use_cases/dual/coordinador_carrera.py y coordinador_dual.py | Operaciones existentes; falta historia académica y fecha real de incorporación como base de semanas. |
| Semana alumno | use_cases/dual/alumno_dual.py: obtener_semana_actual | Usa último reporte y aprobación, no calendario individual acordado. |
| Pendientes tutor | use_cases/dual/coordinador_dual.py: alumnos_atrasados | Calcula semana desde ciclo global; difiere del alumno. |
| Reenvío | use_cases/dual/alumno_dual.py: subir_reporte | Elimina registro rechazado anterior; incumple conservación de versiones acordada. |
| Calificación | application/dto/reportes.py; domain/dual/report.js frontend | Acepta valores decimales; objetivo exige entero 1–10. |
| PDF | infrastructure/documents/dual_reports.py; frontend domain/dual/report.js | API 10 MB frente a cliente 2 MB. Visores fallaban según usuario; causa no verificada. |
| Firma | use_cases/dual/coordinador_dual.py; documents/signatures.py | Firma mediante imagen existe; usuario no ha validado resultado visual. |
| Períodos | DTO/SQL y database/README.md | Se mezcla grado académico con etiqueta de calendario; falta separación cierre/fin de evaluación. |
| Expediente | rutas carrera, repositorio frontend | Consulta/exportaciones existen; historia, permisos, promedio y descargas requieren prueba integral. |
| Foro/buzón | routers/foro y páginas frontend | Código y pruebas presentes; buzón fallaba según usuario. |
| Plantillas | public/plantillas | Word/PDF/Excel estáticos; objetivo requiere Word/PDF administrables por coordinador. |
| Pruebas | tests backend/frontend e integration-tests | Archivos presentes. Sus resultados actuales no se verificaron en esta entrega. |
| Base nueva | database/schema_dual_desde_cero.sql | Propuesta de 12 tablas; no es modelo final aprobado. |

Rutas app/* corresponden a ute-api-clean/app; rutas frontend a ute-dual-frontend/src.

## Incompatibilidades verificadas por lectura

1. database/README.md afirma backend alineado; consultas auth.py todavía insertan email_verificado, ausente del esquema nuevo.
2. Ese README describe baja lógica de tutor; consultas actuales contienen DELETE FROM usuarios.
3. El CHECK de carreras y nomenclatura del esquema nuevo incluye Educación; alcance confirmado requiere Mercadotecnia.
4. La tabla reportes_dual usa cuatrimestre textual y semana 1–18; no resuelve incorporación individual, períodos por fecha ni versiones.
5. La prueba integration-tests/api-contract.test.mjs usa fetch simulado y route_contract.json; no demuestra integración real con FastAPI/PostgreSQL.

## Secuencia de resolución

C01 demuestra base local coherente sin declarar todo funcional. C02–C04 alinean accesos, grupos y calendario. C05–C08 completan entrega, revisión, firma, cierre y expediente. C09 completa comunicación/plantillas. C10 verifica el recorrido completo y recuperación.

No ejecutar 03_limpieza_final.sql, migración de roles ni scripts Supabase sobre una instancia existente. El proyecto comenzará con base vacía. Conservar esos scripts como referencia histórica hasta que C01 documente la ruta nueva.

## Clasificación de evidencia heredada

README_INTEGRACION.md informa pruebas simuladas y pendientes de build/e2e; database/README.md menciona 31 tests de otro backend alineado. Son afirmaciones históricas, no evidencia reproducida para el árbol actual. No declarar porcentajes de avance ni componentes “terminados” a partir del número de archivos.
