import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.application.errors import ApplicationError
from app.application.use_cases.dual import coordinador_dual, obligaciones
from app.domain import calendar

ROOT = Path(__file__).resolve().parents[2]


class Cursor:
    def __init__(self, one=None, many=None):
        self.one = list(one or [])
        self.many = list(many or [])
        self.calls = []

    async def execute(self, query, params=None):
        self.calls.append((query, params))

    async def fetchone(self):
        return self.one.pop(0) if self.one else None

    async def fetchall(self):
        return self.many.pop(0) if self.many else []


class Database:
    def __init__(self, cursor):
        self.cursor = cursor

    @asynccontextmanager
    async def read(self):
        yield self.cursor

    @asynccontextmanager
    async def transaction(self):
        yield self.cursor


class WeeksTests(unittest.TestCase):
    def test_wednesday_start_has_partial_first_week(self):  # AC-06
        weeks = calendar.semanas_incorporacion(date(2026, 10, 14), None, date(2026, 10, 14))
        self.assertEqual(len(weeks), 1)
        w = weeks[0]
        self.assertEqual((w.semana_inicio, w.semana_fin), (date(2026, 10, 12), date(2026, 10, 18)))
        self.assertEqual((w.inicio_efectivo, w.fin_efectivo), (date(2026, 10, 14), date(2026, 10, 18)))
        self.assertTrue(w.parcial)

    def test_two_students_with_different_starts_get_their_own_weeks(self):  # AC-06
        wednesday = calendar.semanas_incorporacion(date(2026, 10, 14), None, date(2026, 10, 21))
        monday = calendar.semanas_incorporacion(date(2026, 10, 12), None, date(2026, 10, 21))
        self.assertEqual([w.parcial for w in wednesday], [True, False])
        self.assertEqual([w.parcial for w in monday], [False, False])
        self.assertEqual(wednesday[0].semana_inicio, monday[0].semana_inicio)
        self.assertNotEqual(wednesday[0].inicio_efectivo, monday[0].inicio_efectivo)

    def test_future_weeks_are_never_generated(self):  # RN-09/RN-10
        self.assertEqual(len(calendar.semanas_incorporacion(date(2026, 10, 5), None, date(2026, 10, 18))), 2)
        self.assertEqual(len(calendar.semanas_incorporacion(date(2026, 10, 5), None, date(2026, 10, 19))), 3)
        self.assertEqual(calendar.semanas_incorporacion(date(2026, 10, 20), None, date(2026, 10, 14)), [])

    def test_ordinal_is_continuous_and_not_capped_at_18(self):
        weeks = calendar.semanas_incorporacion(date(2026, 1, 5), None, date(2026, 12, 31))
        self.assertEqual([w.ordinal for w in weeks], list(range(1, len(weeks) + 1)))
        self.assertGreater(len(weeks), 18)

    def test_baja_is_inclusive_and_stops_later_weeks(self):  # DP-03
        weeks = calendar.semanas_incorporacion(date(2026, 10, 5), date(2026, 10, 14), date(2026, 12, 1))
        self.assertEqual(len(weeks), 2)
        self.assertFalse(weeks[0].parcial)
        self.assertEqual(weeks[1].fin_efectivo, date(2026, 10, 14))
        self.assertEqual(weeks[1].semana_fin, date(2026, 10, 18))
        self.assertTrue(weeks[1].parcial)

    def test_start_and_baja_in_same_week(self):
        (w,) = calendar.semanas_incorporacion(date(2026, 10, 14), date(2026, 10, 16), date(2026, 11, 1))
        self.assertEqual((w.inicio_efectivo, w.fin_efectivo), (date(2026, 10, 14), date(2026, 10, 16)))
        self.assertTrue(w.parcial)

    def test_baja_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            calendar.semanas_incorporacion(date(2026, 10, 14), date(2026, 10, 13), date(2026, 10, 20))

    def test_week_ending_in_may_starts_in_april(self):  # AC-07 / DP-01
        weeks = calendar.semanas_incorporacion(date(2027, 4, 30), None, date(2027, 6, 10))
        first = weeks[0]
        self.assertEqual((first.semana_inicio, first.semana_fin), (date(2027, 4, 26), date(2027, 5, 2)))
        self.assertEqual(first.semana_fin.month, 5)  # el período se resuelve por el domingo
        self.assertEqual(first.inicio_efectivo, date(2027, 4, 30))


class StateAndZoneTests(unittest.TestCase):
    def test_friday_allows_delivery_and_monday_is_late(self):  # AC-08
        sunday = date(2026, 10, 18)
        self.assertEqual(calendar.estado_obligacion(sunday, date(2026, 10, 16), False), calendar.PENDIENTE)
        self.assertEqual(calendar.estado_obligacion(sunday, date(2026, 10, 18), False), calendar.PENDIENTE)
        self.assertEqual(calendar.estado_obligacion(sunday, date(2026, 10, 19), False), calendar.ATRASADA)
        self.assertEqual(calendar.estado_obligacion(sunday, date(2026, 10, 19), True), calendar.RECIBIDA)

    def test_monday_cutoff_uses_mexico_city_not_utc(self):  # AC-08
        # Domingo 21:30 en México ya es lunes en UTC: no debe contarse como atraso.
        sunday_night = datetime(2026, 10, 19, 3, 30, tzinfo=timezone.utc)
        self.assertEqual(calendar.hoy(sunday_night), date(2026, 10, 18))
        monday_start = datetime(2026, 10, 19, 6, 0, tzinfo=timezone.utc)
        self.assertEqual(calendar.hoy(monday_start), date(2026, 10, 19))
        week_end = date(2026, 10, 18)
        self.assertEqual(calendar.estado_obligacion(week_end, calendar.hoy(sunday_night), False), calendar.PENDIENTE)
        self.assertEqual(calendar.estado_obligacion(week_end, calendar.hoy(monday_start), False), calendar.ATRASADA)

    def test_naive_instants_are_rejected(self):
        with self.assertRaises(ValueError):
            calendar.hoy(datetime(2026, 10, 18, 12, 0))


class PeriodOpeningRulesTests(unittest.TestCase):
    """M2: se puede abrir el período en curso; no uno ya terminado (zona America/Mexico_City)."""

    def build(self, label, inicio, fin, hoy):
        from unittest.mock import patch
        from app.application.dto.reportes import CuatrimestreAbrir
        with patch("app.application.dto.reportes._hoy", return_value=hoy):
            return CuatrimestreAbrir(periodo_label=label, fecha_inicio=inicio, fecha_fin=fin)

    def test_period_in_course_can_be_opened(self):
        # 15 de octubre de 2026: Septiembre-Diciembre ya empezó (1 de septiembre) y no termina.
        period = self.build("Septiembre-Diciembre 2026", date(2026, 9, 1), date(2026, 12, 31), date(2026, 10, 15))
        self.assertEqual(period.fecha_inicio, date(2026, 9, 1))

    def test_future_period_can_be_opened_and_last_day_counts(self):
        self.build("Enero-Abril 2027", date(2027, 1, 1), date(2027, 4, 30), date(2026, 10, 15))
        self.build("Septiembre-Diciembre 2026", date(2026, 9, 1), date(2026, 12, 31), date(2026, 12, 31))

    def test_finished_period_is_rejected_with_a_clear_message(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError) as caught:
            self.build("Septiembre-Diciembre 2026", date(2026, 9, 1), date(2026, 12, 31), date(2027, 1, 2))
        message = str(caught.exception)
        self.assertIn("solo se pueden abrir períodos en curso o futuros", message)

    def test_existing_duration_and_order_rules_still_apply(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.build("Mayo-Agosto 2027", date(2027, 5, 1), date(2027, 5, 20), date(2027, 4, 1))
        with self.assertRaises(ValidationError):
            self.build("Mayo-Agosto 2027", date(2027, 8, 31), date(2027, 5, 1), date(2027, 4, 1))


class UseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_generation_locks_first_and_is_repeatable(self):
        inc = {"id": uuid4(), "fecha_inicio": date(2026, 10, 14), "fecha_baja": None}
        cursor = Cursor()
        first = await obligaciones.generar(cursor, inc, date(2026, 10, 21))
        calls_first = list(cursor.calls)
        second = await obligaciones.generar(cursor, inc, date(2026, 10, 21))
        self.assertEqual((first, second), (2, 2))
        self.assertEqual(calls_first[0][0], "dual.obligaciones.lock")
        self.assertEqual({c[0] for c in calls_first[1:]}, {"dual.obligaciones.upsert"})
        self.assertEqual(cursor.calls[len(calls_first):], calls_first)  # mismas sentencias: idempotente por ON CONFLICT

    async def test_sync_skips_up_to_date_and_future_incorporations(self):
        today = date(2026, 10, 21)
        up_to_date = {"id": uuid4(), "matricula": "1", "fecha_inicio": date(2026, 10, 5),
                      "fecha_baja": None, "activo": True, "ultima": date(2026, 10, 19)}
        future = {"id": uuid4(), "matricula": "2", "fecha_inicio": date(2026, 11, 2),
                  "fecha_baja": None, "activo": True, "ultima": None}
        behind = {"id": uuid4(), "matricula": "3", "fecha_inicio": date(2026, 10, 5),
                  "fecha_baja": None, "activo": True, "ultima": date(2026, 10, 12)}
        ended = {"id": uuid4(), "matricula": "4", "fecha_inicio": date(2026, 10, 5),
                 "fecha_baja": date(2026, 10, 14), "activo": False, "ultima": date(2026, 10, 12)}
        cursor = Cursor(many=[[up_to_date, future, behind, ended]])
        await obligaciones.sincronizar(cursor, today)
        locked = [c[1][0] for c in cursor.calls if c[0] == "dual.obligaciones.lock"]
        self.assertEqual(locked, [str(behind["id"])])

    async def test_unknown_student_is_404_and_does_not_generate(self):
        cursor = Cursor(one=[None])
        runtime = SimpleNamespace(database=Database(cursor))
        with self.assertRaises(ApplicationError) as caught:
            await obligaciones.obligaciones_de_alumno("999999999", None, {"id": uuid4()}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual([c[0] for c in cursor.calls], ["dual.obligaciones.student_exists"])

    async def test_states_are_derived_from_today_and_receipt(self):
        rows = [
            {"semana_fin": date(2026, 10, 11), "recibida": False},
            {"semana_fin": date(2026, 10, 18), "recibida": False},
            {"semana_fin": date(2026, 10, 4), "recibida": True},
        ]
        states = [r["estado"] for r in obligaciones._presentar(rows, date(2026, 10, 14))]
        self.assertEqual(states, ["ATRASADA", "PENDIENTE", "RECIBIDA"])

    async def test_overlapping_period_is_rejected_before_insert(self):  # DP-04
        cursor = Cursor(one=[None, {"cuatrimestre": "Mayo-Agosto 2027", "periodo_label": "Mayo-Agosto 2027",
                                     "fecha_inicio": date(2027, 5, 1), "fecha_fin": date(2027, 8, 31)}])
        runtime = SimpleNamespace(database=Database(cursor))
        data = SimpleNamespace(periodo_label="Mayo-Agosto 2027 B",
                               fecha_inicio=date(2027, 8, 1), fecha_fin=date(2027, 12, 15))
        with self.assertRaises(ApplicationError) as caught:
            await coordinador_dual.abrir_cuatrimestre(data, {"sub": "t"}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 409)
        keys = [c[0] for c in cursor.calls]
        self.assertEqual(keys[0], "dual.obligaciones.period_lock")
        self.assertNotIn("dual.coordinador_dual.q021", keys)

    async def test_sin_reporte_rejects_week_zero(self):
        runtime = SimpleNamespace(database=Database(Cursor()))
        with self.assertRaises(ApplicationError):
            await obligaciones.alumnos_sin_reporte("Mayo-Agosto 2027", 0, {}, runtime=runtime)


class SqlContractTests(unittest.TestCase):
    def setUp(self):
        from app.infrastructure.database.queries.dual_obligaciones import QUERIES
        self.sql = {k: " ".join(v["sql"].split()) for k, v in QUERIES.items()}

    def test_ordinal_is_computed_before_the_period_filter(self):
        sql = self.sql["dual.obligaciones.by_student"]
        self.assertLess(sql.index("ROW_NUMBER()"), sql.index("p.cuatrimestre = %s"))

    def test_weeks_after_baja_are_excluded_not_deleted(self):
        for key in ("by_student", "open", "missing_in_period"):
            self.assertIn("o.semana_inicio <= COALESCE(ad.fecha_baja", self.sql[f"dual.obligaciones.{key}"])
        self.assertNotIn("DELETE", " ".join(self.sql.values()))

    def test_group_comes_from_the_period_membership(self):
        for key in ("open", "missing_in_period"):
            sql = self.sql[f"dual.obligaciones.{key}"]
            self.assertIn("alumno_grupo_periodo agp", sql)
            self.assertIn("agp.periodo_id = n.periodo_id", sql)

    def test_migration_004_defines_uniqueness_and_period_exclusion(self):
        sql = (ROOT / "database/migrations/004_obligaciones.sql").read_text(encoding="utf-8")
        for fragment in ("EXCLUDE USING gist", "ciclos_dual_sin_solape", "obligaciones_semanales_unica",
                         "UNIQUE (incorporacion_id, semana_inicio)", "ISODOW", "REFERENCES public.alumnos_dual(id)"):
            self.assertIn(fragment, sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_retired_legacy_queries_are_gone(self):
        from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES
        for key in ("q009", "q013", "q014"):
            self.assertNotIn(f"dual.coordinador_dual.{key}", QUERIES)


if __name__ == "__main__":
    unittest.main()
