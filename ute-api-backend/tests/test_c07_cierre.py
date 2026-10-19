import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.application.errors import ApplicationError
from app.application.use_cases.dual import cierres, entregas, obligaciones
from app.domain import calendar, grading

ROOT = Path(__file__).resolve().parents[2]


class PromedioTests(unittest.TestCase):
    def test_approved_8_9_10_average_9_and_a_rejection_does_not_count(self):  # AC-16
        resultado = grading.calcular([8, 9, 10])
        self.assertEqual((resultado.suma, resultado.cantidad, resultado.promedio), (27, 3, Decimal("9.00")))
        self.assertEqual(grading.mostrar(resultado.promedio), "9.00")

    def test_no_approved_reports_is_sin_calificacion_not_zero(self):  # AC-16, RN-22
        resultado = grading.calcular([])
        self.assertIsNone(resultado.promedio)
        self.assertEqual(grading.mostrar(resultado.promedio), "Sin calificación")
        self.assertNotEqual(grading.mostrar(resultado.promedio), "0.00")

    def test_two_decimals_half_up_and_never_rounded_to_an_integer(self):  # DP-11
        self.assertEqual(grading.promedio_de(1867, 200), Decimal("9.34"))  # 9.335 → 9.34
        self.assertEqual(grading.promedio_de(1401, 200), Decimal("7.01"))  # 7.005 → 7.01
        self.assertEqual(grading.promedio_de(28, 3), Decimal("9.33"))      # 9.3333… → 9.33
        self.assertEqual(grading.promedio_de(29, 3), Decimal("9.67"))
        self.assertEqual(grading.calcular([9, 10]).promedio, Decimal("9.50"))
        self.assertEqual(grading.mostrar(Decimal("9.5")), "9.50")

    def test_notes_outside_1_to_10_or_non_integers_are_rejected(self):
        for nota in (0, 11, 8.5, True, "9", None):
            with self.assertRaises(ValueError, msg=repr(nota)):
                grading.calcular([8, nota])


class EtiquetaPorCierreTests(unittest.TestCase):
    FIN = date(2026, 10, 11)  # domingo

    def test_week_cut_by_an_early_closure_is_not_a_delay(self):  # DP-03, RN-24
        for cierre in (date(2026, 10, 7), date(2026, 10, 11)):
            self.assertEqual(
                calendar.estado_obligacion(self.FIN, date(2026, 10, 20), False, cierre),
                calendar.NO_RECIBIDA_POR_CIERRE, cierre)

    def test_week_already_over_before_the_closure_stays_late(self):
        self.assertEqual(
            calendar.estado_obligacion(self.FIN, date(2026, 10, 20), False, date(2026, 10, 12)),
            calendar.ATRASADA)

    def test_received_weeks_and_open_periods_keep_their_state(self):
        self.assertEqual(calendar.estado_obligacion(self.FIN, date(2026, 10, 20), True, date(2026, 10, 7)),
                         calendar.RECIBIDA)
        self.assertEqual(calendar.estado_obligacion(self.FIN, date(2026, 10, 9), False), calendar.PENDIENTE)
        self.assertEqual(calendar.estado_obligacion(self.FIN, date(2026, 10, 14), False), calendar.ATRASADA)

    def test_closing_instant_is_read_in_the_operating_zone(self):  # RN-24
        # 04:30 UTC del lunes 12 es el domingo 11 a las 22:30 en America/Mexico_City.
        instante = datetime(2026, 10, 12, 4, 30, tzinfo=timezone.utc)
        self.assertEqual(calendar.fecha_de_cierre(instante), date(2026, 10, 11))
        self.assertIsNone(calendar.fecha_de_cierre(None))

    def test_presented_obligation_exposes_the_closure_apart_from_calendar_dates(self):
        fila = {"semana_fin": self.FIN, "recibida": False, "entrega": None, "periodo": "Septiembre-Diciembre 2026",
                "periodo_abierto": False, "periodo_cerrado": True,
                "periodo_cerrado_en": datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)}
        item = obligaciones._presentar([fila], date(2026, 10, 20))[0]
        self.assertEqual(item["estado"], calendar.NO_RECIBIDA_POR_CIERRE)
        self.assertEqual(item["cierre_efectivo"], date(2026, 10, 8))
        self.assertFalse(item["puede_entregar"])
        pendiente = obligaciones._como_pendiente(dict(item, matricula="1", nombre="A", nomenclatura="G",
                                                      empresa="E", ordinal=2, periodo_label="P",
                                                      semana_inicio=date(2026, 10, 5), inicio_efectivo=date(2026, 10, 5),
                                                      fin_efectivo=self.FIN, parcial=False))
        self.assertEqual(pendiente["status"], obligaciones.NOT_RECEIVED)


class ScriptCursor:
    def __init__(self, uno=None, todos=None):
        self.uno = {k: list(v) for k, v in (uno or {}).items()}
        self.todos = {k: list(v) for k, v in (todos or {}).items()}
        self.calls = []
        self._ultimo = None

    async def execute(self, query, params=None):
        self.calls.append((query, params))
        self._ultimo = query

    async def fetchone(self):
        cola = self.uno.get(self._ultimo, [])
        return cola.pop(0) if cola else None

    async def fetchall(self):
        return list(self.todos.get(self._ultimo, []))

    @property
    def claves(self):
        return [c[0] for c in self.calls]


class Database:
    def __init__(self, cursor):
        self.cursor = cursor

    @asynccontextmanager
    async def read(self):
        yield self.cursor

    @asynccontextmanager
    async def transaction(self):
        yield self.cursor


PERIODO_ID = uuid4()
COORDINADOR = {"id": uuid4(), "sub": "coordinador@example.test"}


def periodo(abierto=False, cerrado=False, finalizada=None, cerrado_at=None):
    return {"id": PERIODO_ID, "cuatrimestre": "Septiembre-Diciembre 2026",
            "periodo_label": "Septiembre-Diciembre 2026", "fecha_inicio": date(2026, 9, 1),
            "fecha_fin": date(2026, 12, 31), "abierto": abierto, "cerrado": cerrado, "cerrado_por": None,
            "cerrado_at": cerrado_at, "evaluacion_finalizada_en": finalizada, "evaluacion_finalizada_por": None}


CONTEOS = {"obligaciones": 4, "recibidas": 3, "pendientes_revision": 0, "rechazadas": 1, "aprobadas": 2,
           "sin_entrega": 1, "no_recibidas_por_cierre": 0}
ALUMNOS = [{"matricula": "111", "nombre": "Ana", "nomenclatura": "G1", "obligaciones": 3, "aprobadas": 2,
            "pendientes_revision": 0, "rechazadas": 1, "sin_entrega": 0},
           {"matricula": "222", "nombre": "Beto", "nomenclatura": "G1", "obligaciones": 1, "aprobadas": 0,
            "pendientes_revision": 0, "rechazadas": 0, "sin_entrega": 1}]
APROBADAS = [{"matricula": "111", "reporte_id": uuid4(), "nota": 8}, {"matricula": "111", "reporte_id": uuid4(), "nota": 10}]
CERRADO_EN = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)


def runtime_con(cursor):
    return SimpleNamespace(database=Database(cursor))


class CerrarRecepcionTests(unittest.IsolatedAsyncioTestCase):
    def cursor(self, antes, despues=None):
        return ScriptCursor(
            uno={"dual.cierres.bloquear_exclusivo": [antes], "dual.cierres.periodo": [despues or antes],
                 "dual.cierres.conteos": [CONTEOS]},
            todos={"dual.cierres.alumnos": ALUMNOS, "dual.cierres.aprobadas": APROBADAS})

    async def test_closing_identifies_the_period_by_id_and_never_renames_it(self):  # AC-14
        cursor = self.cursor(periodo(abierto=True), periodo(cerrado=True, cerrado_at=CERRADO_EN))
        resultado = await cierres.cerrar_recepcion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        self.assertFalse(resultado["repetido"])
        self.assertEqual(resultado["periodo"]["recepcion"], "cerrada")
        self.assertEqual(resultado["periodo"]["cierre_efectivo"], date(2026, 10, 8))
        self.assertEqual(resultado["periodo"]["periodo_label"], "Septiembre-Diciembre 2026")
        cerrar = next(c for c in cursor.calls if c[0] == "dual.cierres.cerrar")
        self.assertEqual(cerrar[1], (COORDINADOR["id"], PERIODO_ID))  # sin etiqueta: no hay renombrado

    async def test_closing_takes_the_exclusive_row_lock_first(self):  # AC-15
        cursor = self.cursor(periodo(abierto=True), periodo(cerrado=True, cerrado_at=CERRADO_EN))
        await cierres.cerrar_recepcion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        # C14: la sincronización de obligaciones va antes, en otra transacción; ya con el período bloqueado no se toca
        # ninguna obligación (evita el interbloqueo con una entrega).
        claves = list(cursor.claves)
        bloqueo = claves.index("dual.cierres.bloquear_exclusivo")
        self.assertTrue(all(c.startswith("dual.obligaciones.") for c in claves[:bloqueo]), claves[:bloqueo])
        self.assertFalse([c for c in claves[bloqueo:] if c.startswith("dual.obligaciones.")])

    async def test_repeating_the_closure_is_idempotent(self):  # AC-15
        cursor = self.cursor(periodo(cerrado=True, cerrado_at=CERRADO_EN))
        resultado = await cierres.cerrar_recepcion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        self.assertTrue(resultado["repetido"])
        self.assertNotIn("dual.cierres.cerrar", cursor.claves)

    async def test_a_period_that_never_received_cannot_be_closed_and_unknown_is_404(self):
        with self.assertRaises(ApplicationError) as caught:
            await cierres.cerrar_recepcion(PERIODO_ID, COORDINADOR, runtime=runtime_con(self.cursor(periodo())))
        self.assertEqual(caught.exception.status_code, 409)
        vacio = ScriptCursor()
        with self.assertRaises(ApplicationError) as caught:
            await cierres.cerrar_recepcion(PERIODO_ID, COORDINADOR, runtime=runtime_con(vacio))
        self.assertEqual(caught.exception.status_code, 404)


class FinalizarTests(unittest.IsolatedAsyncioTestCase):
    def cursor(self, antes, pendientes=0, despues=None, resultados=None):
        return ScriptCursor(
            uno={"dual.cierres.bloquear_exclusivo": [antes], "dual.cierres.periodo": [despues or antes],
                 "dual.cierres.pendientes": [{"pendientes": pendientes}], "dual.cierres.conteos": [CONTEOS],
                 "dual.cierres.insert_cierre": [{"id": uuid4()}, {"id": uuid4()}]},
            todos={"dual.cierres.alumnos": ALUMNOS, "dual.cierres.aprobadas": APROBADAS,
                   "dual.cierres.resultados": resultados or []})

    async def test_cannot_finalize_before_closing_reception(self):  # RN-20
        cursor = self.cursor(periodo(abierto=True))
        with self.assertRaises(ApplicationError) as caught:
            await cierres.finalizar_evaluacion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("dual.cierres.insert_cierre", cursor.claves)

    async def test_a_pending_review_blocks_finalizing_and_nothing_is_frozen(self):  # AC-17
        cursor = self.cursor(periodo(cerrado=True, cerrado_at=CERRADO_EN), pendientes=2)
        with self.assertRaises(ApplicationError) as caught:
            await cierres.finalizar_evaluacion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("Quedan 2 reportes pendientes de revisión", caught.exception.detail)
        self.assertEqual(cierres._texto_pendientes(1), "Queda 1 reporte pendiente de revisión.")
        for clave in ("dual.cierres.insert_cierre", "dual.cierres.insert_nota", "dual.cierres.finalizar"):
            self.assertNotIn(clave, cursor.claves)

    async def test_finalizing_freezes_each_student_with_the_exact_sum_count_and_rounded_average(self):  # AC-16/17
        cierre = periodo(cerrado=True, cerrado_at=CERRADO_EN)
        listo = periodo(cerrado=True, cerrado_at=CERRADO_EN, finalizada=CERRADO_EN)
        cursor = self.cursor(cierre, despues=listo, resultados=[
            {"matricula": "111", "suma": 18, "cantidad": 2, "promedio": Decimal("9.00")},
            {"matricula": "222", "suma": 0, "cantidad": 0, "promedio": None}])
        resultado = await cierres.finalizar_evaluacion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        self.assertFalse(resultado["repetido"])
        insertos = [c[1] for c in cursor.calls if c[0] == "dual.cierres.insert_cierre"]
        self.assertEqual(insertos[0][1:5], ("111", 18, 2, Decimal("9.00")))
        self.assertEqual(insertos[1][1:5], ("222", 0, 0, None))  # sin aprobados: nulo, no 0.00
        self.assertEqual(len([c for c in cursor.calls if c[0] == "dual.cierres.insert_nota"]), 2)
        self.assertEqual(resultado["periodo"]["evaluacion"], "finalizada")
        por_matricula = {a["matricula"]: a for a in resultado["alumnos"]}
        self.assertEqual((por_matricula["111"]["promedio"], por_matricula["111"]["definitivo"]), ("9.00", True))
        self.assertEqual(por_matricula["222"]["promedio_texto"], "Sin calificación")
        self.assertIsNone(por_matricula["222"]["promedio"])

    async def test_finalizing_twice_changes_nothing(self):  # AC-17
        listo = periodo(cerrado=True, cerrado_at=CERRADO_EN, finalizada=CERRADO_EN)
        cursor = self.cursor(listo)
        resultado = await cierres.finalizar_evaluacion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        self.assertTrue(resultado["repetido"])
        self.assertNotIn("dual.cierres.insert_cierre", cursor.claves)
        self.assertNotIn("dual.cierres.finalizar", cursor.claves)

    async def test_summary_of_an_open_evaluation_is_provisional_and_uses_the_same_rule(self):  # AC-16
        cursor = self.cursor(periodo(cerrado=True, cerrado_at=CERRADO_EN))
        resumen = await cierres.resumen(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        ana = next(a for a in resumen["alumnos"] if a["matricula"] == "111")
        self.assertEqual((ana["promedio"], ana["suma"], ana["aprobados"], ana["definitivo"]), ("9.00", 18, 2, False))
        self.assertTrue(resumen["puede_finalizar"])
        self.assertEqual(resumen["periodo"]["recepcion"], "cerrada")
        self.assertEqual(resumen["periodo"]["evaluacion"], "en_curso")

    async def test_finalization_never_touches_other_periods_or_obligations(self):  # AC-18
        cursor = self.cursor(periodo(cerrado=True, cerrado_at=CERRADO_EN),
                             despues=periodo(cerrado=True, cerrado_at=CERRADO_EN, finalizada=CERRADO_EN))
        await cierres.finalizar_evaluacion(PERIODO_ID, COORDINADOR, runtime=runtime_con(cursor))
        for clave, params in cursor.calls:
            self.assertTrue(clave.startswith("dual.cierres."), clave)
            self.assertNotIn("obligaciones", clave)
        escrituras = [c for c in cursor.calls if c[0] in ("dual.cierres.finalizar", "dual.cierres.cerrar")]
        for _, params in escrituras:
            self.assertIn(PERIODO_ID, params)  # solo la fila del período indicado


class EntregaFrenteAlCierreTests(unittest.IsolatedAsyncioTestCase):
    def obligacion(self, cerrado):
        return {"id": uuid4(), "semana_inicio": date(2026, 10, 5), "semana_fin": date(2026, 10, 11),
                "periodo_id": PERIODO_ID, "matricula": "123456789", "ordinal": 2,
                "periodo": "Septiembre-Diciembre 2026", "abierto": not cerrado, "cerrado": cerrado}

    async def test_delivery_shares_the_period_lock_and_rereads_the_state(self):  # AC-15
        cursor = ScriptCursor(uno={"dual.entregas.obligacion_propia": [self.obligacion(False), self.obligacion(True)],
                                   "dual.entregas.reporte_de_obligacion": [None]})
        # Compite con el cierre: tras esperar el bloqueo compartido ve el período ya cerrado.
        with self.assertRaises(ApplicationError) as caught:
            await entregas._registrar(cursor, uuid4(), "123456789", uuid4(), 8, date(2026, 10, 5),
                                      date(2026, 10, 9), {"clave": "a" * 32 + ".pdf", "sha256": "f" * 64,
                                                          "tamano": 1, "ruta": "/x"}, 1)
        self.assertEqual(caught.exception.status_code, 409)
        claves = cursor.claves
        self.assertEqual(claves[:4], ["dual.entregas.lock", "dual.entregas.obligacion_propia",
                                      "dual.cierres.bloquear_compartido", "dual.entregas.obligacion_propia"])
        self.assertNotIn("dual.entregas.insert_documento", claves)


class DirectorioPorPeriodoTests(unittest.IsolatedAsyncioTestCase):
    """El filtro por período debe pasar por `resolve_query`: separa el WHERE por « AND »."""

    def test_no_allowed_filter_contains_the_clause_separator(self):
        from app.infrastructure.database.repository import ASSIGNMENTS, FILTERS
        for clave, filtros in FILTERS.items():
            for filtro in filtros:
                self.assertNotIn(" AND ", filtro, (clave, filtro))

    async def _consulta_de(self, cuatrimestre, grupo, busqueda=None, situacion="todos"):
        from app.application.use_cases.dual import expediente
        cursor = ScriptCursor()
        await expediente.directorio(cuatrimestre, grupo, busqueda, situacion, 50, 0, {}, runtime=runtime_con(cursor))
        return cursor.calls[0]

    async def test_every_filter_combination_binds_all_parameters_of_the_static_query(self):  # AC-16 / C08-AC4
        # C08: el directorio usa una consulta estática (sin cláusulas dinámicas que dependan del texto).
        from app.infrastructure.database.queries.dual_expediente import QUERIES
        for cuatrimestre, grupo, busqueda, situacion in (
                (None, None, None, "todos"), ("Septiembre-Diciembre 2026", None, None, "todos"),
                (None, "34TII-3214-I-1A", None, "activos"), ("Septiembre-Diciembre 2026", "34TII-3214-I-1A", "ana", "baja")):
            clave, params = await self._consulta_de(cuatrimestre, grupo, busqueda, situacion)
            self.assertEqual(clave, "dual.expediente.directorio")
            self.assertEqual(QUERIES[clave]["sql"].count("%s"), len(params), (cuatrimestre, grupo))

    async def test_directory_validates_pagination_and_situation_and_escapes_the_search(self):  # C08-AC4
        from app.application.use_cases.dual import expediente
        for situacion, limite, desplazamiento in (("x", 50, 0), ("todos", 0, 0), ("todos", 201, 0), ("todos", 10, -1)):
            with self.assertRaises(ApplicationError) as caught:
                await expediente.directorio(None, None, None, situacion, limite, desplazamiento, {},
                                            runtime=runtime_con(ScriptCursor()))
            self.assertEqual(caught.exception.status_code, 422, (situacion, limite, desplazamiento))
        _, params = await self._consulta_de(None, None, "50%_x")
        self.assertEqual(params[8:11], ("50\\%\\_x",) * 3)


class SqlContractTests(unittest.TestCase):
    def test_migration_007_freezes_results_and_protects_finalized_periods(self):
        sql = (ROOT / "database/migrations/007_cierre.sql").read_text(encoding="utf-8")
        for fragmento in ("cierres_inmutables", "BEFORE UPDATE OR DELETE", "cierres_promedio_si_hay_aprobados",
                          "ciclos_dual_finaliza_tras_cierre", "ciclos_finalizado_protegido",
                          "rechaza_si_periodo_finalizado", "numeric(4, 2)", "cierres_alumno_periodo_unico"):
            self.assertIn(fragmento, sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_closing_query_never_rewrites_the_label_and_lock_modes_are_row_level(self):
        from app.infrastructure.database.queries.dual_cierres import QUERIES
        cerrar = " ".join(QUERIES["dual.cierres.cerrar"]["sql"].split())
        self.assertNotIn("periodo_label", cerrar)
        self.assertIn("FOR NO KEY UPDATE", QUERIES["dual.cierres.bloquear_exclusivo"]["sql"])
        self.assertIn("FOR SHARE", QUERIES["dual.cierres.bloquear_compartido"]["sql"])

    def test_legacy_closure_by_label_and_its_queries_are_gone(self):
        from app.application.dto import reportes
        from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES
        self.assertFalse(hasattr(reportes, "CuatrimestreCerrar"))
        self.assertNotIn("dual.coordinador_dual.q023", QUERIES)
        router = (ROOT / "ute-api-backend/app/presentation/api/routers/dual/coordinador_dual.py").read_text(encoding="utf-8")
        self.assertNotIn('"/cierre"', router)

    def test_directory_average_uses_the_period_not_the_grade(self):
        from app.infrastructure.database.queries.dual_expediente import QUERIES
        sql = " ".join(QUERIES["dual.expediente.directorio"]["sql"].split())
        self.assertNotIn("g.cuatrimestre::text", sql)
        self.assertIn("p.cuatrimestre = %s", sql)
        self.assertIn("JOIN obligaciones_semanales", sql)


if __name__ == "__main__":
    unittest.main()
