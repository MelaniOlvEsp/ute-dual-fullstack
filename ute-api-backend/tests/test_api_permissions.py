"""Comprueba que los endpoints sensibles exijan el rol correcto."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def guards(path):
    # Extrae dependencias declaradas sin iniciar FastAPI ni PostgreSQL.
    module = ast.parse(path.read_text())
    mapping = {}
    for node in module.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        dependencies = []
        for default in node.args.defaults:
            if (isinstance(default, ast.Call) and
                isinstance(default.func, ast.Name) and
                default.func.id == 'Depends' and default.args):
                dependencies.append(getattr(default.args[0], 'id', None))
        mapping[node.name] = dependencies
    return mapping


class PermissionTest(unittest.TestCase):
    def test_tutor_only_mutates_reports_and_groups(self):
        dual = guards(ROOT / 'app/presentation/api/routers/dual/coordinador_dual.py')
        # C07 (MP-11): solo el coordinador cierra la recepción y finaliza la evaluación.
        for name in ('cerrar_recepcion', 'finalizar_evaluacion'):
            self.assertIn('get_coordinator', dual[name], name)
        for name in ('listar_periodos_estado', 'resumen_periodo'):
            self.assertIn('get_consulta_periodos', dual[name], name)
        self.assertNotIn('cerrar_cuatrimestre', dual)
        career = guards(ROOT / 'app/presentation/api/routers/dual/coordinador_carrera.py')
        for name in ('detalle_reporte', 'revisar_version', 'descargar_version_pdf_tutor',
                     'cargar_firma', 'crear_empresa', 'asignar_alumno_empresa'):
            self.assertIn('get_coordinador_dual', dual[name])
        # C06 (MP-08): ni el alumno ni el coordinador revisan, solo el tutor.
        self.assertNotIn('get_coordinator', dual['revisar_version'])
        for name in ('crear_grupo', 'cargar_alumnos_csv',
                     'agregar_alumno_individual', 'actualizar_alumno',
                     'eliminar_alumno', 'listar_grupos'):
            self.assertIn('get_tutor_academico', career[name])
        for name in ('listar_alumnos', 'expediente_alumno',
                     'descargar_aprobado_pdf'):
            self.assertIn('get_coordinador_carrera', career[name])
        # C08 / DP-14: el paquete de archivo lo genera solo el tutor; el coordinador consulta pero no exporta.
        for name in ('paquete_alumno', 'paquete_carrera'):
            self.assertIn('get_tutor_academico', career[name], name)
        # C08B / D2: tutor y coordinador pueden depurar; el alumno no tiene acceso.
        for name in ('archivo_periodo', 'programar_purga', 'cancelar_purga', 'ejecutar_purga'):
            self.assertIn('get_coordinador_carrera', career[name], name)
        alumno = guards(ROOT / 'app/presentation/api/routers/dual/alumno_dual.py')
        for name in ('mi_expediente', 'mi_paquete'):
            self.assertIn('get_alumno_dual', alumno[name], name)
            self.assertNotIn('matricula', alumno[name])

    def test_only_coordinator_manages_periods(self):
        # DP-04 / MP-18: el coordinador abre y cierra períodos; el tutor no.
        dual = guards(ROOT / 'app/presentation/api/routers/dual/coordinador_dual.py')
        for name in ('abrir_cuatrimestre', 'cuatrimestre_actual'):
            self.assertIn('get_coordinator', dual[name], name)
            self.assertNotIn('get_coordinador_dual', dual[name], name)
        # Las consultas de pendientes siguen siendo del tutor.
        for name in ('alumnos_atrasados', 'alumnos_sin_reporte', 'obligaciones_alumno'):
            self.assertIn('get_coordinador_dual', dual[name], name)

    def test_only_coordinator_creates_tutors(self):
        auth = guards(ROOT / 'app/presentation/api/routers/auth.py')
        for name in ('crear_tutor', 'listar_tutores', 'eliminar_tutor'):
            self.assertIn('get_coordinator', auth[name])
        self.assertIn('get_tutor', auth['password_provisional'])
