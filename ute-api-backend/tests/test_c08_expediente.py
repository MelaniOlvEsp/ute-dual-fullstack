import json
import os
import tempfile
import unittest
import zipfile
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import fitz

from app.application.errors import ApplicationError
from app.application.use_cases.dual import expediente, paquetes
from app.domain import archive
from app.infrastructure.documents import dual_reports
from app.infrastructure.documents import paquetes as constructor

ROOT = Path(__file__).resolve().parents[2]
FINALIZADA = datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)


def pdf_bytes(texto="reporte"):
    documento = fitz.open()
    documento.new_page().insert_text((72, 72), texto)
    contenido = documento.tobytes()
    documento.close()
    return contenido


# --- Dominio -----------------------------------------------------------------------------------

class VentanaDelAlumnoTests(unittest.TestCase):
    def test_not_available_until_the_evaluation_is_finalized(self):  # DP-14
        ventana = archive.ventana_alumno(None)
        self.assertFalse(ventana["disponible"])
        self.assertIsNone(ventana["hasta"])

    def test_one_week_from_finalization_then_closed(self):  # C08-AC8
        dentro = archive.ventana_alumno(FINALIZADA, FINALIZADA + timedelta(days=6, hours=23))
        self.assertTrue(dentro["disponible"])
        self.assertEqual(dentro["hasta"], date(2026, 10, 23))
        exacto = archive.ventana_alumno(FINALIZADA, FINALIZADA + timedelta(days=7))
        self.assertTrue(exacto["disponible"])
        despues = archive.ventana_alumno(FINALIZADA, FINALIZADA + timedelta(days=7, seconds=1))
        self.assertFalse(despues["disponible"])
        self.assertIn("2026-10-23", despues["motivo"])


class NombresSegurosTests(unittest.TestCase):
    def test_names_never_contain_separators_or_parent_references(self):  # AC-04, zip slip
        for hostil in ("../../etc/passwd", "..\\..\\x", "C:\\Windows\\sys", "a/b\\c", "..", "", None, "\x00evil"):
            seguro = archive.nombre_seguro(hostil)
            for prohibido in ("/", "\\", "..", ":", "\x00"):
                self.assertNotIn(prohibido, seguro, repr(hostil))
            self.assertTrue(seguro)

    def test_accents_and_spaces_are_normalised(self):
        self.assertEqual(archive.nombre_seguro("Septiembre-Diciembre 2026"), "Septiembre-Diciembre-2026")
        self.assertEqual(archive.nombre_seguro("Tecnología Ñandú"), "Tecnologia-Nandu")

    def test_path_in_package_is_built_only_from_server_values(self):
        ruta = archive.ruta_documento_en_paquete("TII", "Septiembre-Diciembre 2026", "34TII-3214-I-1A",
                                                  "123456789", 4, 2, "firmado")
        self.assertEqual(ruta, "TII/Septiembre-Diciembre-2026/34TII-3214-I-1A/123456789/S4-v2-firmado.pdf")
        hostil = archive.ruta_documento_en_paquete("../x", "..\\y", "a/../b", "9/../9", 1, 1, "original")
        self.assertNotIn("..", hostil)
        self.assertEqual(hostil.count("/"), 4)
        with self.assertRaises(ValueError):
            archive.ruta_documento_en_paquete("TII", "p", "g", "m", 1, 1, "otro")


class CsvSeguroTests(unittest.TestCase):
    def test_formula_prefixes_are_neutralised(self):  # OWASP CSV Injection
        for peligrosa in ("=1+1", "+cmd", "-2", "@SUM(A1)", "\tx", "\rx", "\nx"):
            self.assertEqual(archive.celda_csv_segura(peligrosa), "'" + peligrosa, repr(peligrosa))
        for normal in ("Ana", "9.34", "", None, "a=b", "34TII"):
            self.assertFalse(str(archive.celda_csv_segura(normal)).startswith("'"), repr(normal))

    def test_csv_quotes_values_and_protects_every_cell(self):
        contenido = archive.construir_csv(["matricula", "nombre"], [["1", '=HYPERLINK("http://x","clic")'], ["2", 'Ana "A", B']])
        texto = contenido.decode("utf-8-sig")
        self.assertTrue(contenido.startswith(b"\xef\xbb\xbf"))
        self.assertIn("\"'=HYPERLINK(\"\"http://x\"\",\"\"clic\"\")\"", texto)
        self.assertIn('"Ana ""A"", B"', texto)


class ManifiestoTests(unittest.TestCase):
    def test_manifest_serialisation_is_stable(self):
        a = archive.manifiesto_bytes({"b": 2, "a": date(2026, 1, 2)})
        b = archive.manifiesto_bytes({"a": date(2026, 1, 2), "b": 2})
        self.assertEqual(a, b)
        self.assertEqual(archive.sha256_hex(a), archive.sha256_hex(b))
        self.assertEqual(json.loads(a), {"a": "2026-01-02", "b": 2})


# --- Constructor del ZIP con almacenamiento real -------------------------------------------------

class ConstructorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(dual_reports, "_raiz", return_value=Path(self.tmp.name))
        self.patch.start()
        self.destino = Path(self.tmp.name) / "salida.zip"

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    async def _documento(self, texto):
        contenido = pdf_bytes(texto)
        guardado = await dual_reports.guardar_documento(contenido)
        return contenido, {"ruta": f"TII/p/g/1/{texto}.pdf", "clave": guardado["clave"],
                           "sha256": guardado["sha256"], "tamano": guardado["tamano"], "etiqueta": texto}

    async def test_zip_contains_manifest_csv_and_byte_identical_documents(self):  # C08-AC6
        contenido, entrada = await self._documento("uno")
        estadisticas = constructor.construir_zip([entrada], b'{"a": 1}', b"x\r\n", self.destino)
        self.assertEqual((estadisticas["archivos"], estadisticas["bytes"]), (1, len(contenido)))
        with zipfile.ZipFile(self.destino) as z:
            self.assertEqual(sorted(z.namelist()), ["TII/p/g/1/uno.pdf", "manifiesto.json", "resumen.csv"])
            self.assertEqual(z.read("TII/p/g/1/uno.pdf"), contenido)
            self.assertIsNone(z.testzip())

    async def test_a_missing_document_fails_the_whole_package_without_error_files(self):  # AC6, DP-14
        _, entrada = await self._documento("uno")
        os.unlink(dual_reports.ruta_documento(entrada["clave"]))
        with self.assertRaises(ApplicationError) as caught:
            constructor.construir_zip([entrada], b"{}", b"", self.destino)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("Falta el documento", caught.exception.detail)

    async def test_a_document_that_does_not_match_its_hash_fails(self):  # integridad
        _, entrada = await self._documento("uno")
        dual_reports.ruta_documento(entrada["clave"]).write_bytes(b"%PDF-alterado")
        with self.assertRaises(ApplicationError) as caught:
            constructor.construir_zip([entrada], b"{}", b"", self.destino)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("no coincide con su hash", caught.exception.detail)

    async def test_duplicate_names_are_rejected(self):
        _, entrada = await self._documento("uno")
        with self.assertRaises(ApplicationError):
            constructor.construir_zip([entrada, dict(entrada)], b"{}", b"", self.destino)

    def test_stale_temporary_packages_are_cleaned(self):
        reciente = constructor.nuevo_temporal()
        antiguo = reciente.with_name("viejo-" + reciente.name)
        antiguo.write_bytes(b"x")
        viejo = datetime.now().timestamp() - 7200
        os.utime(antiguo, (viejo, viejo))
        self.assertGreaterEqual(constructor.limpiar_temporales(3600), 1)
        self.assertFalse(antiguo.exists())
        self.assertTrue(reciente.exists())
        reciente.unlink()


# --- Casos de uso con dobles -----------------------------------------------------------------

class ScriptCursor:
    def __init__(self, uno=None, todos=None):
        self.uno = {k: list(v) for k, v in (uno or {}).items()}
        self.todos = {k: list(v) for k, v in (todos or {}).items()}
        self.calls, self._ultimo = [], None

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


def periodo_fila(finalizada=None, abierto=False, cerrado=True):
    return {"id": uuid4(), "cuatrimestre": "Septiembre-Diciembre 2026", "periodo_label": "Septiembre-Diciembre 2026",
            "fecha_inicio": date(2026, 9, 1), "fecha_fin": date(2026, 12, 31), "abierto": abierto,
            "cerrado": cerrado, "cerrado_at": FINALIZADA, "evaluacion_finalizada_en": finalizada}


def aprobado(ordinal, nota, **extra):
    fila = {"reporte_id": uuid4(), "semana_inicio": date(2026, 9, 7), "semana_fin": date(2026, 9, 13),
            "ordinal": ordinal, "version": 1, "declarada_inicio": date(2026, 9, 7),
            "declarada_fin": date(2026, 9, 11), "declarada_nota": nota, "fecha_inicio": date(2026, 9, 7),
            "fecha_fin": date(2026, 9, 11), "nota": nota, "observacion": None, "revisado_en": FINALIZADA,
            "firmado": True, "paginas": 2, "tamano_original": 10}
    fila.update(extra)
    return fila


class ExpedienteTests(unittest.IsolatedAsyncioTestCase):
    def cursor(self, periodos, aprobados_por_periodo, congelados=None):
        uno = {"dual.expediente.alumno": [{"matricula": "123456789", "nombre": "Ana", "activo": False,
                                            "fecha_baja": date(2026, 12, 1)}],
               "dual.expediente.grupo": [{"nomenclatura": "G-P1", "carrera": "TIC", "grado": 3, "carrera_codigo": "TII"},
                                         {"nomenclatura": "G-P2", "carrera": "TIC", "grado": 4, "carrera_codigo": "TII"}],
               "dual.expediente.resultado": congelados or []}
        cur = ScriptCursor(uno=uno, todos={"dual.expediente.periodos": periodos})
        original = cur.fetchall
        cola = list(aprobados_por_periodo)

        async def fetchall():
            if cur._ultimo == "dual.expediente.aprobados":
                return cola.pop(0)
            return await original()
        cur.fetchall = fetchall
        return cur

    async def test_two_periods_keep_their_historical_group_and_average(self):  # C08-AC1 / AC-19
        p1, p2 = periodo_fila(finalizada=FINALIZADA), periodo_fila()
        p2["cuatrimestre"] = p2["periodo_label"] = "Mayo-Agosto 2027"
        cursor = self.cursor([p1, p2], [[aprobado(1, 8), aprobado(2, 10)], [aprobado(1, 9)]],
                             congelados=[{"suma": 18, "cantidad": 2, "promedio": Decimal("9.00"), "cerrado_en": FINALIZADA}])
        runtime = SimpleNamespace(database=Database(cursor))
        resultado = await expediente.expediente("123456789", {}, runtime=runtime)
        self.assertEqual([p["grupo"]["nomenclatura"] for p in resultado["periodos"]], ["G-P1", "G-P2"])
        primero, segundo = resultado["periodos"]
        self.assertEqual((primero["resumen"]["promedio"], primero["resumen"]["definitivo"]), ("9.00", True))
        self.assertEqual((segundo["resumen"]["promedio"], segundo["resumen"]["definitivo"]), ("9.00", False))
        self.assertEqual([a["nota"] for a in primero["aprobados"]], [8, 10])
        self.assertFalse(resultado["alumno"]["activo"], "Un alumno de baja conserva su expediente (RN-29)")

    async def test_final_average_comes_from_the_frozen_result_not_from_live_reports(self):  # C07, RN-22
        cursor = self.cursor([periodo_fila(finalizada=FINALIZADA)], [[aprobado(1, 5)]],
                             congelados=[{"suma": 18, "cantidad": 2, "promedio": Decimal("9.00"), "cerrado_en": FINALIZADA}])
        resultado = await expediente.expediente("123456789", {}, runtime=SimpleNamespace(database=Database(cursor)))
        self.assertEqual(resultado["periodos"][0]["resumen"]["promedio"], "9.00")

    async def test_period_without_approved_reports_is_sin_calificacion(self):  # RN-22
        cursor = self.cursor([periodo_fila()], [[]])
        resultado = await expediente.expediente("123456789", {}, runtime=SimpleNamespace(database=Database(cursor)))
        resumen = resultado["periodos"][0]["resumen"]
        self.assertEqual((resumen["promedio"], resumen["promedio_texto"]), (None, "Sin calificación"))

    async def test_own_package_window_and_staff_availability(self):  # C08-AC8
        cursor = self.cursor([periodo_fila(finalizada=FINALIZADA)], [[]])
        propio = await expediente.expediente("123456789", {}, propio=True, ahora=FINALIZADA + timedelta(days=3),
                                             runtime=SimpleNamespace(database=Database(cursor)))
        self.assertTrue(propio["periodos"][0]["paquete"]["disponible"])
        cursor = self.cursor([periodo_fila(finalizada=FINALIZADA)], [[]])
        vencido = await expediente.expediente("123456789", {}, propio=True, ahora=FINALIZADA + timedelta(days=9),
                                              runtime=SimpleNamespace(database=Database(cursor)))
        self.assertFalse(vencido["periodos"][0]["paquete"]["disponible"])
        cursor = self.cursor([periodo_fila()], [[]])
        sin_finalizar = await expediente.expediente("123456789", {}, runtime=SimpleNamespace(database=Database(cursor)))
        self.assertFalse(sin_finalizar["periodos"][0]["paquete"]["disponible"])

    async def test_unknown_student_is_404(self):
        with self.assertRaises(ApplicationError) as caught:
            await expediente.expediente("0", {}, runtime=SimpleNamespace(database=Database(ScriptCursor())))
        self.assertEqual(caught.exception.status_code, 404)

    async def test_download_only_serves_approved_versions(self):  # AC-04, MP-10
        runtime = SimpleNamespace(database=Database(ScriptCursor(uno={"dual.expediente.documentos_aprobados": [None]})),
                                  services=SimpleNamespace(leer_documento=AsyncMock(return_value=b"%PDF")))
        with self.assertRaises(ApplicationError) as caught:
            await expediente.descargar_aprobado(uuid4(), 1, "firmado", {}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 404)
        runtime.services.leer_documento.assert_not_awaited()
        sin_firmado = {"original": "a" * 32 + ".pdf", "firmado": None, "matricula": "123456789"}
        runtime = SimpleNamespace(database=Database(ScriptCursor(uno={"dual.expediente.documentos_aprobados": [sin_firmado, sin_firmado]})),
                                  services=SimpleNamespace(leer_documento=AsyncMock(return_value=b"%PDF")))
        with self.assertRaises(ApplicationError):
            await expediente.descargar_aprobado(uuid4(), 1, "firmado", {}, runtime=runtime)
        resultado = await expediente.descargar_aprobado(uuid4(), 1, "original", {}, runtime=runtime)
        runtime.services.leer_documento.assert_awaited_once_with("a" * 32 + ".pdf")
        self.assertIn("123456789-v1.pdf", resultado.headers["Content-Disposition"])


class PaquetesTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, periodo, extra_uno=None, extra_todos=None, falla=None):
        self.periodo_id = periodo["id"]
        uno = {"dual.cierres.periodo": [periodo],
               "dual.expediente.alumno": [{"matricula": "123456789", "nombre": "Ana"}],
               "dual.expediente.grupo": [{"nomenclatura": "G", "carrera": "TIC", "carrera_codigo": "TII"}]}
        uno.update(extra_uno or {})
        todos = {"dual.expediente.periodos": [{"id": periodo["id"]}], "dual.cierres.resultados": [],
                 "dual.paquetes.documentos": []}
        todos.update(extra_todos or {})
        cursor = ScriptCursor(uno=uno, todos=todos)
        self.destino = Path(tempfile.mkstemp(suffix=".zip")[1])
        servicios = SimpleNamespace(
            nuevo_paquete_temporal=lambda: self.destino,
            construir_paquete=lambda *a: (_ for _ in ()).throw(falla) if falla else {"archivos": 0, "bytes": 0, "tamano_zip": 5})
        return SimpleNamespace(database=Database(cursor), services=servicios), cursor

    def tearDown(self):
        if getattr(self, "destino", None) and self.destino.exists():
            self.destino.unlink()

    async def test_package_requires_a_finalized_evaluation(self):  # DP-14
        runtime, cursor = self.runtime(periodo_fila())
        with self.assertRaises(ApplicationError) as caught:
            await paquetes.paquete_de_alumno("123456789", self.periodo_id, {"id": uuid4()}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("dual.paquetes.registrar", cursor.claves)

    async def test_student_package_window_expired_is_403_and_builds_nothing(self):  # C08-AC8
        runtime, cursor = self.runtime(periodo_fila(finalizada=FINALIZADA))
        with self.assertRaises(ApplicationError) as caught:
            await paquetes.paquete_propio(self.periodo_id, {"id": uuid4(), "matricula": "123456789"},
                                          runtime=runtime, ahora=FINALIZADA + timedelta(days=8))
        self.assertEqual(caught.exception.status_code, 403)
        self.assertNotIn("dual.paquetes.registrar", cursor.claves)
        self.assertFalse(self.destino.read_bytes(), "No se construyó ningún paquete")

    async def test_generation_is_recorded_and_the_streamed_file_is_removed(self):  # DP-14
        usuario = {"id": uuid4(), "matricula": "123456789"}
        runtime, cursor = self.runtime(periodo_fila(finalizada=FINALIZADA))
        self.destino.write_bytes(b"PK-zip")
        resultado = await paquetes.paquete_propio(self.periodo_id, usuario, runtime=runtime, ahora=FINALIZADA + timedelta(days=1))
        registro = next(c[1] for c in cursor.calls if c[0] == "dual.paquetes.registrar")
        self.assertEqual((registro[0], registro[2], registro[3], registro[4]), ("alumno", "123456789", None, "alumno"))
        self.assertRegex(registro[6], r"^[0-9a-f]{64}$")
        self.assertEqual(b"".join(resultado.content), b"PK-zip")
        self.assertFalse(self.destino.exists(), "El temporal se elimina al terminar la descarga")
        self.assertIn("mi-paquete-123456789", resultado.headers["Content-Disposition"])

    async def test_failure_building_leaves_no_record_and_no_temporary(self):  # DP-14, fallo explícito
        runtime, cursor = self.runtime(periodo_fila(finalizada=FINALIZADA),
                                       falla=ApplicationError(409, "Falta el documento"))
        with self.assertRaises(ApplicationError):
            await paquetes.paquete_de_alumno("123456789", self.periodo_id, {"id": uuid4()}, runtime=runtime)
        self.assertNotIn("dual.paquetes.registrar", cursor.claves)
        self.assertFalse(self.destino.exists())

    async def test_unknown_career_and_empty_selection_are_404(self):
        runtime, _ = self.runtime(periodo_fila(finalizada=FINALIZADA))
        with self.assertRaises(ApplicationError) as caught:
            await paquetes.paquete_de_carrera("XXX", uuid4(), {"id": uuid4()}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 404)
        runtime, _ = self.runtime(periodo_fila(finalizada=FINALIZADA), extra_todos={"dual.paquetes.alumnos_carrera": []})
        with self.assertRaises(ApplicationError) as caught:
            await paquetes.paquete_de_carrera("tii", uuid4(), {"id": uuid4()}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_manifest_lists_files_with_their_hashes_and_protected_csv(self):  # C08-AC6
        ordinal_fila = {"reporte_id": uuid4(), "semana_inicio": date(2026, 9, 7), "semana_fin": date(2026, 9, 13),
                        "ordinal": 2, "version": 1, "fecha_inicio": date(2026, 9, 7), "fecha_fin": date(2026, 9, 11),
                        "nota": 9, "original_clave": "a" * 32 + ".pdf", "original_sha": "1" * 64, "original_tamano": 5,
                        "firmado_clave": "b" * 32 + ".pdf", "firmado_sha": "2" * 64, "firmado_tamano": 6}
        capturado = {}

        def construir(entradas, manifiesto, resumen_csv, destino):
            capturado.update(entradas=entradas, manifiesto=json.loads(manifiesto), csv=resumen_csv)
            return {"archivos": 2, "bytes": 11, "tamano_zip": 5}
        runtime, _ = self.runtime(periodo_fila(finalizada=FINALIZADA),
                                  extra_uno={"dual.expediente.alumno": [{"matricula": "123456789", "nombre": "=Ana"}]},
                                  extra_todos={"dual.paquetes.documentos": [ordinal_fila]})
        runtime.services.construir_paquete = construir
        self.destino.write_bytes(b"x")
        await paquetes.paquete_de_alumno("123456789", self.periodo_id, {"id": uuid4()}, runtime=runtime)
        rutas = [e["ruta"] for e in capturado["entradas"]]
        self.assertEqual(rutas, ["TII/Septiembre-Diciembre-2026/G/123456789/S2-v1-firmado.pdf",
                                 "TII/Septiembre-Diciembre-2026/G/123456789/S2-v1-original.pdf"])
        archivos = capturado["manifiesto"]["alumnos"][0]["reportes"][0]["archivos"]
        self.assertEqual([(a["tipo"], a["sha256"]) for a in archivos], [("firmado", "2" * 64), ("original", "1" * 64)])
        self.assertIn("'=Ana", capturado["csv"].decode("utf-8-sig"))


class EntradasMalformadasTests(unittest.IsolatedAsyncioTestCase):
    """Revisión C08 M1: NUL y desplazamientos fuera de rango responden 422, nunca 500."""

    def runtime(self):
        cursor = ScriptCursor()
        return cursor, SimpleNamespace(database=Database(cursor))

    async def test_directory_rejects_nul_and_out_of_range_offset_before_querying(self):
        for argumentos in (
                (None, None, None, "todos", 50, expediente.DESPLAZAMIENTO_MAXIMO + 1),
                (None, None, None, "todos", 50, 10 ** 30),
                (None, None, "a\x00b", "todos", 50, 0),
                ("x\x00", None, None, "todos", 50, 0),
                (None, "g\x00", None, "todos", 50, 0)):
            cursor, runtime = self.runtime()
            with self.assertRaises(ApplicationError) as caught:
                await expediente.directorio(*argumentos, {}, runtime=runtime)
            self.assertEqual(caught.exception.status_code, 422, argumentos)
            self.assertEqual(cursor.calls, [], "No debe llegar a la base")

    async def test_directory_accepts_the_maximum_offset(self):
        _, runtime = self.runtime()
        resultado = await expediente.directorio(
            None, None, None, "todos", 50, expediente.DESPLAZAMIENTO_MAXIMO, {}, runtime=runtime)
        self.assertEqual(resultado["items"], [])

    async def test_record_and_package_reject_nul_in_the_student_id(self):
        cursor, runtime = self.runtime()
        with self.assertRaises(ApplicationError) as caught:
            await expediente.expediente("123\x00", {}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 422)
        with self.assertRaises(ApplicationError) as caught:
            await paquetes._alumno_en_periodo(cursor, "123\x00", uuid4())
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(cursor.calls, [])


class SqlContractTests(unittest.TestCase):
    def test_migration_008_makes_the_package_registry_immutable(self):
        sql = (ROOT / "database/migrations/008_paquetes.sql").read_text(encoding="utf-8")
        for fragmento in ("paquetes_inmutables", "BEFORE UPDATE OR DELETE", "manifiesto_sha256",
                          "paquetes_alcance_coherente", "paquetes_alumno_solo_alcance_alumno"):
            self.assertIn(fragmento, sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_legacy_pointer_reads_and_exports_are_gone(self):
        carrera = (ROOT / "ute-api-backend/app/presentation/api/routers/dual/coordinador_carrera.py").read_text(encoding="utf-8")
        for retirado in ("exportar-csv", "exportar-zip", "/reporte/{reporte_id}/pdf", "/alumnos/{matricula}/reportes"):
            self.assertNotIn(retirado, carrera)
        caso = (ROOT / "ute-api-backend/app/application/use_cases/dual/coordinador_carrera.py").read_text(encoding="utf-8")
        self.assertNotIn("zipfile", caso)
        self.assertNotIn("archivo_pdf_local", caso)

    def test_directory_includes_students_with_baja_and_filters_by_period_without_dynamic_where(self):
        from app.infrastructure.database.queries.dual_expediente import QUERIES
        sql = " ".join(QUERIES["dual.expediente.directorio"]["sql"].split())
        self.assertNotIn("ad.activo = TRUE", sql)
        self.assertIn("count(*) OVER () AS total", sql)
        self.assertIsNone(QUERIES["dual.expediente.directorio"]["dynamic"])


if __name__ == "__main__":
    unittest.main()
