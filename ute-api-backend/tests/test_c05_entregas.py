import asyncio
import os
import tempfile
import time
import unittest
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import fitz

from app.application.errors import ApplicationError
from app.application.use_cases.dual import entregas, obligaciones
from app.domain import reports
from app.infrastructure.documents import dual_reports

ROOT = Path(__file__).resolve().parents[2]


def pdf_bytes(paginas=1):
    documento = fitz.open()
    for numero in range(paginas):
        pagina = documento.new_page()
        pagina.insert_text((72, 72), f"Reporte semanal {numero + 1}")
    contenido = documento.tobytes()
    documento.close()
    return contenido


class Upload:
    def __init__(self, contenido, filename="reporte.pdf"):
        self.contenido, self.filename, self.pos = contenido, filename, 0

    async def read(self, size=-1):
        fin = len(self.contenido) if size < 0 else self.pos + size
        bloque = self.contenido[self.pos:fin]
        self.pos += len(bloque)
        return bloque


class NotaTests(unittest.TestCase):
    def test_accepts_integers_one_to_ten(self):  # AC-10
        for valor in (1, 10, "1", "10", " 7 ", "08"):
            self.assertIn(reports.parse_nota(valor), range(1, 11))

    def test_rejects_zero_eleven_decimals_and_text(self):  # AC-10
        for valor in ("0", "11", "8.5", "8.0", "8,5", "abc", "", "-3", "²", "٨", True, 0, 11):
            with self.assertRaises(reports.EntregaInvalida, msg=repr(valor)):
                reports.parse_nota(valor)

    def test_dates_only_require_start_before_or_equal_end(self):  # DP-12
        reports.validar_fechas(date(2026, 10, 5), date(2026, 10, 5))
        reports.validar_fechas(date(2025, 1, 1), date(2030, 1, 1))  # fuera de la semana: lo verifica el tutor
        with self.assertRaises(reports.EntregaInvalida):
            reports.validar_fechas(date(2026, 10, 6), date(2026, 10, 5))


class PdfTests(unittest.IsolatedAsyncioTestCase):
    def test_valid_pdf_returns_page_count(self):
        self.assertEqual(dual_reports.inspeccionar_pdf(pdf_bytes(3)), 3)

    def test_rejects_empty_non_pdf_corrupt_truncated_and_protected(self):  # AC-10
        valido = pdf_bytes(2)
        documento = fitz.open(stream=valido, filetype="pdf")
        protegido = documento.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="clave", owner_pw="otra")
        documento.close()
        casos = {
            "vacío": b"",
            "texto": b"esto no es un pdf",
            "cabecera falsa": b"%PDF-1.7\nbasura sin estructura",
            "truncado": valido[: len(valido) // 2],
            "protegido": protegido,
        }
        for nombre, contenido in casos.items():
            with self.assertRaises(ApplicationError, msg=nombre) as caught:
                dual_reports.inspeccionar_pdf(contenido)
            self.assertEqual(caught.exception.status_code, 422, nombre)

    async def test_size_limit_is_enforced_while_reading(self):
        grande = b"%PDF-" + b"0" * (reports.MAX_PDF_BYTES + 10)
        with self.assertRaises(ApplicationError) as caught:
            await dual_reports.leer_pdf_limitado(Upload(grande))
        self.assertEqual(caught.exception.status_code, 413)
        exacto = b"%PDF-" + b"0" * (reports.MAX_PDF_BYTES - 5)
        self.assertEqual(len(await dual_reports.leer_pdf_limitado(Upload(exacto))), reports.MAX_PDF_BYTES)

    async def test_extension_is_required(self):
        with self.assertRaises(ApplicationError) as caught:
            await dual_reports.leer_pdf_limitado(Upload(pdf_bytes(), "reporte.png"))
        self.assertEqual(caught.exception.status_code, 422)

    def test_api_limit_is_ten_megabytes(self):  # DP-08 (el límite del cliente se prueba en JS)
        self.assertEqual(reports.MAX_PDF_BYTES, 10 * 1024 * 1024)


class StorageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(dual_reports, "_raiz", return_value=Path(self.tmp.name))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    async def test_original_is_stored_byte_for_byte_with_server_key(self):  # AC4
        contenido = pdf_bytes(2)
        guardado = await dual_reports.guardar_documento(contenido)
        self.assertRegex(guardado["clave"], r"^[0-9a-f]{32}\.pdf$")
        self.assertEqual(await dual_reports.leer_documento(guardado["clave"]), contenido)
        self.assertEqual(Path(guardado["ruta"]).read_bytes(), contenido)
        self.assertEqual(guardado["tamano"], len(contenido))

    async def test_each_save_uses_a_new_key_and_never_overwrites(self):
        a = await dual_reports.guardar_documento(pdf_bytes(1))
        b = await dual_reports.guardar_documento(pdf_bytes(1))
        self.assertNotEqual(a["clave"], b["clave"])
        self.assertTrue(Path(a["ruta"]).is_file() and Path(b["ruta"]).is_file())

    def test_client_supplied_keys_cannot_escape_the_store(self):
        for clave in ("../../etc/passwd", "..\\x.pdf", "a" * 32, "a" * 32 + ".exe", "", "../" + "a" * 32 + ".pdf"):
            with self.assertRaises(ApplicationError):
                dual_reports.ruta_documento(clave)

    async def test_orphan_cleanup_is_by_reference_and_age(self):  # AC7
        referenciado = await dual_reports.guardar_documento(pdf_bytes(1))
        huerfano = await dual_reports.guardar_documento(pdf_bytes(1))
        reciente = await dual_reports.guardar_documento(pdf_bytes(1))
        parcial = Path(huerfano["ruta"] + ".part")
        parcial.write_bytes(b"x")
        ajeno = Path(self.tmp.name) / "notas.txt"
        ajeno.write_text("no tocar")
        viejo = time.time() - 7200
        for ruta in (Path(referenciado["ruta"]), Path(huerfano["ruta"]), parcial, ajeno):
            os.utime(ruta, (viejo, viejo))
        eliminados = dual_reports.limpiar_huerfanos({referenciado["clave"]}, antiguedad_segundos=3600)
        self.assertCountEqual(eliminados, [huerfano["clave"], parcial.name])
        self.assertTrue(Path(referenciado["ruta"]).is_file())  # referenciado: nunca se borra
        self.assertTrue(Path(reciente["ruta"]).is_file())  # reciente: puede estar en una entrega en curso
        self.assertTrue(ajeno.is_file())  # archivos sin forma de clave: no se tocan


class ScriptCursor:
    """Cursor de pruebas: responde por consulta y registra el orden de ejecución."""

    def __init__(self, guion):
        self.guion = {k: list(v) for k, v in guion.items()}
        self.calls = []
        self._ultimo = None

    async def execute(self, query, params=None):
        self.calls.append((query, params))
        self._ultimo = query

    async def fetchone(self):
        cola = self.guion.get(self._ultimo, [])
        return cola.pop(0) if cola else None

    async def fetchall(self):
        return []


class Database:
    def __init__(self, cursor, falla=None):
        self.cursor, self.falla = cursor, falla

    @asynccontextmanager
    async def read(self):
        yield self.cursor

    @asynccontextmanager
    async def transaction(self):
        yield self.cursor
        if self.falla:
            raise self.falla


def obligacion(abierto=True, cerrado=False, periodo_id="p1"):
    return {"id": uuid4(), "semana_inicio": date(2026, 10, 5), "semana_fin": date(2026, 10, 11),
            "periodo_id": periodo_id, "matricula": "123456789", "ordinal": 2,
            "periodo": "Septiembre-Diciembre 2026", "abierto": abierto, "cerrado": cerrado}


def runtime_con(cursor, falla=None):
    servicios = SimpleNamespace(
        leer_pdf_limitado=AsyncMock(side_effect=lambda archivo: archivo.contenido),
        inspeccionar_pdf=lambda contenido: 1,
        guardar_documento=AsyncMock(return_value={
            "clave": "a" * 32 + ".pdf", "ruta": "/almacen/a.pdf", "tamano": 10, "sha256": "f" * 64}),
        eliminar_documento=AsyncMock(),
    )
    return SimpleNamespace(database=Database(cursor, falla), services=servicios)


USUARIO = {"id": uuid4(), "matricula": "123456789"}


async def entregar(runtime, nota="9", inicio=date(2026, 10, 5), fin=date(2026, 10, 9), obligacion_id=None):
    return await entregas.entregar(obligacion_id or uuid4(), inicio, fin, nota, Upload(pdf_bytes()),
                                   USUARIO, runtime=runtime)


class EntregaTests(unittest.IsolatedAsyncioTestCase):
    def guion(self, **extra):
        base = {"dual.entregas.obligacion_propia": [obligacion(), obligacion()],
                "dual.entregas.reporte_de_obligacion": [None],
                "dual.entregas.insert_documento": [{"id": uuid4()}],
                "dual.entregas.insert_reporte": [{"id": uuid4()}],
                "dual.entregas.insert_version": [{"id": uuid4(), "numero": 1, "recibido_en": None}]}
        base.update(extra)
        return base

    async def test_first_delivery_creates_report_and_version_one(self):
        cursor = ScriptCursor(self.guion())
        runtime = runtime_con(cursor)
        resultado = await entregar(runtime)
        self.assertEqual((resultado["version"], resultado["repetido"]), (1, False))
        claves = [c[0] for c in cursor.calls]
        self.assertEqual(claves[claves.index("dual.entregas.lock") + 1], "dual.entregas.obligacion_propia")
        for esperado in ("dual.entregas.insert_documento", "dual.entregas.insert_reporte",
                         "dual.entregas.insert_version"):
            self.assertIn(esperado, claves)
        self.assertNotIn("dual.entregas.reenviar", claves)
        runtime.services.eliminar_documento.assert_not_awaited()

    async def test_closed_period_is_rejected_before_storing_anything(self):  # DP-13 / AC5
        for fila in (obligacion(abierto=False), obligacion(cerrado=True), obligacion(periodo_id=None)):
            cursor = ScriptCursor({"dual.entregas.obligacion_propia": [fila]})
            runtime = runtime_con(cursor)
            with self.assertRaises(ApplicationError) as caught:
                await entregar(runtime)
            self.assertEqual(caught.exception.status_code, 409)
            runtime.services.guardar_documento.assert_not_awaited()

    async def test_foreign_or_unknown_obligation_is_404(self):  # AC6
        runtime = runtime_con(ScriptCursor({"dual.entregas.obligacion_propia": [None]}))
        with self.assertRaises(ApplicationError) as caught:
            await entregar(runtime)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_invalid_note_or_dates_are_422_without_touching_storage(self):  # AC2
        runtime = runtime_con(ScriptCursor({}))
        for nota in ("0", "11", "8.5"):
            with self.assertRaises(ApplicationError) as caught:
                await entregar(runtime, nota=nota)
            self.assertEqual(caught.exception.status_code, 422)
        with self.assertRaises(ApplicationError):
            await entregar(runtime, inicio=date(2026, 10, 9), fin=date(2026, 10, 5))
        runtime.services.leer_pdf_limitado.assert_not_awaited()

    async def test_approved_report_is_not_replaced(self):  # RN-17
        guion = self.guion(**{"dual.entregas.reporte_de_obligacion": [
            {"id": uuid4(), "estado": "Aprobada", "nota_agente": None, "revisado_por": None,
             "revisado_en": None, "ultima": 1}]})
        runtime = runtime_con(ScriptCursor(guion))
        with self.assertRaises(ApplicationError) as caught:
            await entregar(runtime)
        self.assertEqual(caught.exception.status_code, 409)
        runtime.services.eliminar_documento.assert_awaited_once()  # solo el archivo nuevo

    async def test_pending_report_blocks_a_different_resend_but_identical_retry_is_stable(self):  # AC3
        reporte = {"id": uuid4(), "estado": "Pendiente", "nota_agente": None, "revisado_por": None,
                   "revisado_en": None, "ultima": 1}
        igual = {"numero": 1, "fecha_inicio": date(2026, 10, 5), "fecha_fin": date(2026, 10, 9),
                 "nota": 9, "sha256": "f" * 64}
        cursor = ScriptCursor(self.guion(**{"dual.entregas.reporte_de_obligacion": [reporte],
                                            "dual.entregas.version_actual": [igual]}))
        runtime = runtime_con(cursor)
        resultado = await entregar(runtime)
        self.assertTrue(resultado["repetido"])
        self.assertNotIn("dual.entregas.insert_version", [c[0] for c in cursor.calls])
        runtime.services.eliminar_documento.assert_awaited_once()  # el duplicado no se queda

        distinto = dict(igual, nota=8)
        cursor = ScriptCursor(self.guion(**{"dual.entregas.reporte_de_obligacion": [dict(reporte)],
                                            "dual.entregas.version_actual": [distinto]}))
        with self.assertRaises(ApplicationError) as caught:
            await entregar(runtime_con(cursor))
        self.assertEqual(caught.exception.status_code, 409)

    async def test_resend_after_rejection_keeps_previous_decision_and_adds_version(self):  # AC3
        revisado = date(2026, 10, 12)
        rechazado = {"id": uuid4(), "estado": "Rechazada", "nota_agente": "Falta la firma de la empresa",
                     "revisado_por": uuid4(), "revisado_en": revisado, "ultima": 1}
        cursor = ScriptCursor(self.guion(**{
            "dual.entregas.reporte_de_obligacion": [rechazado],
            "dual.entregas.insert_version": [{"id": uuid4(), "numero": 2, "recibido_en": None}]}))
        resultado = await entregar(runtime_con(cursor))
        self.assertEqual(resultado["version"], 2)
        claves = [c[0] for c in cursor.calls]
        self.assertLess(claves.index("dual.entregas.snapshot_decision"), claves.index("dual.entregas.reenviar"))
        self.assertNotIn("dual.entregas.insert_reporte", claves)  # un solo reporte lógico por obligación
        snapshot = next(c[1] for c in cursor.calls if c[0] == "dual.entregas.snapshot_decision")
        self.assertEqual(snapshot[:2], ("Rechazada", "Falta la firma de la empresa"))
        self.assertEqual(snapshot[-1], 1)  # la decisión se guarda en la versión que la recibió

    async def test_database_failure_discards_only_the_new_file(self):  # AC7
        runtime = runtime_con(ScriptCursor(self.guion()), falla=RuntimeError("fallo de base de datos"))
        with self.assertRaises(RuntimeError):
            await entregar(runtime)
        runtime.services.eliminar_documento.assert_awaited_once_with("a" * 32 + ".pdf")

    async def test_unreadable_pdf_never_reaches_storage(self):  # AC2
        runtime = runtime_con(ScriptCursor({"dual.entregas.obligacion_propia": [obligacion()]}))
        runtime.services.inspeccionar_pdf = lambda contenido: (_ for _ in ()).throw(
            ApplicationError(422, "El PDF está dañado"))
        with self.assertRaises(ApplicationError):
            await entregar(runtime)
        runtime.services.guardar_documento.assert_not_awaited()


class PresentationTests(unittest.TestCase):
    def fila(self, **cambios):
        base = {"semana_fin": date(2026, 10, 11), "recibida": False, "entrega": None,
                "periodo": "Septiembre-Diciembre 2026", "periodo_abierto": True, "periodo_cerrado": False}
        base.update(cambios)
        return base

    def test_delivery_is_allowed_only_with_open_period_and_no_blocking_report(self):
        casos = [
            (self.fila(), True),
            (self.fila(entrega="Rechazada", recibida=True), True),
            (self.fila(entrega="Pendiente", recibida=True), False),
            (self.fila(entrega="Aprobada", recibida=True), False),
            (self.fila(periodo_abierto=False), False),
            (self.fila(periodo_cerrado=True), False),
            (self.fila(periodo=None), False),
        ]
        for fila, esperado in casos:
            puede, motivo = obligaciones._entregable(fila)
            self.assertEqual(puede, esperado, fila)
            self.assertEqual(motivo is None, esperado, fila)

    def test_any_week_can_be_delivered_without_other_weeks_being_approved(self):  # AC-09
        pendiente_de_revision = self.fila(entrega="Pendiente", recibida=True)
        otra_semana = self.fila(semana_fin=date(2026, 10, 18))
        self.assertFalse(obligaciones._entregable(pendiente_de_revision)[0])
        self.assertTrue(obligaciones._entregable(otra_semana)[0])


class SqlContractTests(unittest.TestCase):
    def test_migration_005_makes_versions_immutable_and_unique(self):
        sql = (ROOT / "database/migrations/005_entregas.sql").read_text(encoding="utf-8")
        for fragmento in ("reporte_versiones_unica", "UNIQUE (reporte_id, numero)", "BEFORE UPDATE OR DELETE",
                          "Las versiones de reporte no se eliminan", "CHECK (nota BETWEEN 1 AND 10)",
                          "idx_reportes_dual_obligacion", "documentos_clave_formato"):
            self.assertIn(fragmento, sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_obligation_queries_use_the_real_report_not_dates(self):
        from app.infrastructure.database.queries.dual_obligaciones import QUERIES
        for clave in ("by_student", "open", "missing_in_period"):
            sql = " ".join(QUERIES[f"dual.obligaciones.{clave}"]["sql"].split())
            self.assertIn("rd.obligacion_id = n.id", sql)
            self.assertNotIn("r.fecha_fin BETWEEN", sql)

    def test_sequential_flow_queries_are_gone(self):
        from app.infrastructure.database.queries.dual_alumno_dual import QUERIES
        self.assertEqual(set(QUERIES), {"dual.alumno_dual.q005", "dual.alumno_dual.q006", "dual.alumno_dual.q011"})

    def test_legacy_deletion_of_rejected_report_and_compression_are_removed(self):
        for ruta in ("ute-api-backend/app/application/use_cases/dual/alumno_dual.py",
                     "ute-api-backend/app/infrastructure/documents/dual_reports.py"):
            texto = (ROOT / ruta).read_text(encoding="utf-8")
            self.assertNotIn("comprimir_pdf", texto)
            self.assertNotIn("DELETE FROM reportes_dual", texto)
            self.assertNotIn("subir_reporte", texto)


if __name__ == "__main__":
    unittest.main()
