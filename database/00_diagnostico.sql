-- Solo lectura. Ejecutar primero contra copia de la base.
-- Las consultas con resultado > 0 requieren revisión manual.
SELECT 'becas_convocatorias' AS revision, count(*) AS filas
FROM public.convocatorias_becas
UNION ALL SELECT 'becas_solicitudes', count(*) FROM public.solicitudes
UNION ALL SELECT 'buzon_fuera_dual', count(*) FROM public.buzon_mensajes
 WHERE area <> 'dual'
UNION ALL SELECT 'roles_no_v2', count(*) FROM public.usuarios
 WHERE roles NOT IN ('{"alumno":true}'::jsonb,
                     '{"tutor_academico":true}'::jsonb,
                     '{"coordinador_dual":true}'::jsonb)
UNION ALL SELECT 'cuentas_alumno_sin_matricula', count(*) FROM public.usuarios
 WHERE roles = '{"alumno":true}'::jsonb AND matricula IS NULL
UNION ALL SELECT 'reportes_sin_asignacion_mismo_periodo', count(*)
 FROM public.reportes_dual r
 WHERE NOT EXISTS (
   SELECT 1 FROM public.alumnos_dual ad
   WHERE ad.matricula = r.matricula
     AND ad.cuatrimestre = r.cuatrimestre)
UNION ALL SELECT 'ciclos_abiertos', count(*) FROM public.ciclos_dual
 WHERE abierto IS TRUE
UNION ALL SELECT 'ciclos_con_estados_contradictorios', count(*)
 FROM public.ciclos_dual WHERE abierto IS TRUE AND cerrado IS TRUE
UNION ALL SELECT 'semanas_invalidas', count(*) FROM public.reportes_dual
 WHERE semana NOT BETWEEN 1 AND 18
UNION ALL SELECT 'fecha_reportes_invertidas', count(*)
 FROM public.reportes_dual WHERE fecha_fin < fecha_inicio;

-- Los valores siguientes son grupos de duplicados, no filas totales.
SELECT 'emails_sin_distinguir_mayusculas' AS revision,
       lower(email) AS valor, count(*) AS repeticiones
FROM public.usuarios GROUP BY lower(email) HAVING count(*) > 1;

SELECT 'matriculas_con_multiples_cuentas' AS revision,
       matricula AS valor, count(*) AS repeticiones
FROM public.usuarios WHERE matricula IS NOT NULL
GROUP BY matricula HAVING count(*) > 1;

SELECT 'multiples_asignaciones_dual_activas' AS revision,
       matricula AS valor, count(*) AS repeticiones
FROM public.alumnos_dual WHERE activo IS TRUE
GROUP BY matricula HAVING count(*) > 1;

-- Relación entre distintos significados de cuatrimestre.
SELECT r.matricula, r.cuatrimestre, r.semana
FROM public.reportes_dual r
WHERE NOT EXISTS (
 SELECT 1 FROM public.alumnos_dual ad
 WHERE ad.matricula = r.matricula
   AND ad.cuatrimestre = r.cuatrimestre)
ORDER BY r.matricula, r.cuatrimestre, r.semana LIMIT 50;

-- Revisión de permisos visibles en el esquema public.
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('anon', 'authenticated')
ORDER BY table_name, grantee, privilege_type;
