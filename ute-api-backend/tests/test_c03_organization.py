import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.application.errors import ApplicationError
from app.application.use_cases.dual import organization
from app.domain.organization import CAREERS, canonical_career


class Upload:
    def __init__(self, content):
        self.content = content

    async def read(self):
        return self.content


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


class OrganizationRulesTests(unittest.TestCase):
    def test_catalog_is_closed_to_three_careers(self):
        self.assertEqual([item.code for item in CAREERS], ["TII", "LOG", "MER"])
        self.assertEqual(canonical_career("MER").name, "LIC. NME MERCADOTECNIA")
        with self.assertRaises(ValueError):
            canonical_career("EDU")

    def test_csv_contract_exact_headers_duplicates_and_limit(self):
        rows = organization.parse_student_csv(
            b"matricula,nombre\n012345678,Ana\n012345678,Ana\n"
        )
        self.assertIsNone(rows[0]["razon"])
        self.assertIn("repetida", rows[1]["razon"])
        with self.assertRaises(ApplicationError):
            organization.parse_student_csv(b"nombre,matricula\nAna,012345678\n")
        oversized = b"matricula,nombre\n" + b"\n".join(
            f"{100000000 + i},Alumno {i}".encode() for i in range(501)
        )
        with self.assertRaisesRegex(ApplicationError, "500"):
            organization.parse_student_csv(oversized)

    def test_matricula_requires_ascii_digits(self):
        rows = organization.parse_student_csv(
            "matricula,nombre\n12345678²,Ana\n٠١٢٣٤٥٦٧٨,Luis\n012345678,Eva\n".encode("utf-8")
        )
        self.assertIsNotNone(rows[0]["razon"])
        self.assertIsNotNone(rows[1]["razon"])
        self.assertIsNone(rows[2]["razon"])

    def test_current_group_follows_latest_period_and_company_is_deterministic(self):
        from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES as DUAL
        from app.infrastructure.database.queries.dual_organization import QUERIES as ORG

        group_sql = " ".join(ORG["dual.organization.set_current_group"]["sql"].split())
        self.assertIn("FROM alumno_grupo_periodo", group_sql)
        self.assertIn("DESC", group_sql)
        self.assertEqual(group_sql.count("%s"), 2)
        report_sql = " ".join(DUAL["dual.coordinador_dual.q000"]["sql"].split())
        self.assertIn("ORDER BY ad2.activo DESC, ad2.fecha_inicio DESC", report_sql)
        self.assertNotIn("LIMIT 1),", report_sql)

    def test_incorporation_is_independent_of_cuatrimestre_text(self):
        from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES
        insert = " ".join(QUERIES["dual.coordinador_dual.insert_incorporation"]["sql"].split())
        self.assertNotIn("cuatrimestre", insert.split("RETURNING")[0])
        for key in ("q005", "q006"):
            sql = " ".join(QUERIES[f"dual.coordinador_dual.{key}"]["sql"].split())
            self.assertNotIn("ad.cuatrimestre", sql, key)
            self.assertIn("p.fecha_inicio", sql, key)
        # q015/q017 se sustituyeron en C04 por consultas sobre obligaciones semanales.
        self.assertNotIn("dual.coordinador_dual.q015", QUERIES)
        self.assertNotIn("dual.coordinador_dual.q017", QUERIES)
        migration = (Path(__file__).resolve().parents[2]
                     / "database/migrations/003_grupos_incorporacion.sql").read_text(encoding="utf-8")
        self.assertIn("ALTER COLUMN cuatrimestre DROP NOT NULL", migration)

    def test_base_schema_has_no_education_career(self):
        root = Path(__file__).resolve().parents[2] / "database"
        base = (root / "schema_dual_desde_cero.sql").read_text(encoding="utf-8")
        self.assertNotIn("EDUCACI", base.upper())
        self.assertNotIn("'EDU'", base)
        self.assertIn("LIC. NME MERCADOTECNIA", base)
        self.assertIn("THEN 'MER'", base)

    def test_group_list_exposes_ciclo_ingreso(self):
        from app.infrastructure.database.queries.dual_coordinador_carrera import QUERIES
        sql = " ".join(
            item["sql"] for key, item in QUERIES.items()
            if "total_alumnos" in item["sql"] and "carreras c" in item["sql"]
        )
        self.assertIn("g.ciclo_ingreso", sql)

    def test_migration_preserves_institutional_nomenclature(self):
        sql = (Path(__file__).resolve().parents[2] / "database/migrations/003_grupos_incorporacion.sql").read_text(encoding="utf-8")
        self.assertIn("THEN 'TII'", sql)
        self.assertIn("THEN 'LOG'", sql)
        self.assertIn("THEN 'MER'", sql)
        self.assertNotIn("THEN 'EDU'", sql)
        self.assertIn("alumno_grupo_periodo", sql)
        self.assertIn("idx_alumnos_dual_unico_activo", sql)


class OrganizationAtomicityTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeated_only_preview_cannot_be_applied(self):
        group_id, period_id = uuid4(), uuid4()
        cursor = Cursor(
            one=[{"grupo_id": group_id, "nomenclatura": "24TII-1-B-5A",
                  "periodo_id": period_id, "periodo_label": "Septiembre-Diciembre 2026"}],
            many=[[{"matricula": "012345678", "nombre": "Ana",
                    "grupo_id": group_id, "nomenclatura": "24TII-1-B-5A"}]],
        )
        runtime = SimpleNamespace(database=Database(cursor))
        result = await organization.preview_csv(
            group_id, period_id, Upload(b"matricula,nombre\n012345678,Ana\n"),
            {"id": uuid4()}, runtime=runtime)
        self.assertEqual(len(result["repetidos"]), 1)
        self.assertFalse(result["puede_aplicar"])

    async def test_csv_conflict_never_reaches_insert(self):
        group_id, period_id = uuid4(), uuid4()
        cursor = Cursor(
            one=[{"grupo_id": group_id, "nomenclatura": "24TII-1-B-5A",
                  "periodo_id": period_id, "periodo_label": "Septiembre-Diciembre 2026"}],
            many=[[{"matricula": "012345678", "nombre": "Nombre anterior",
                   "grupo_id": None, "nomenclatura": None}]],
        )
        runtime = SimpleNamespace(database=Database(cursor))
        with self.assertRaises(ApplicationError) as caught:
            await organization.apply_csv(
                group_id, period_id,
                Upload(b"matricula,nombre\n012345678,Nombre nuevo\n"),
                {"id": uuid4()}, runtime=runtime,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual([call[0] for call in cursor.calls], [
            "dual.organization.group_period",
            "dual.organization.students_for_period",
        ])


if __name__ == "__main__":
    unittest.main()
