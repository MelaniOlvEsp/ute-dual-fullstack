import tempfile
import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.application.errors import ApplicationError
from app.application.use_cases.dual import archivado, expediente, paquetes, purgas
from app.infrastructure.documents import dual_reports
from app.infrastructure.storage import registro
from app.infrastructure.storage.base import AlmacenamientoNoDisponible
from app.infrastructure.storage.memoria import MemoriaAlmacenamiento

FINALIZADA = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
AHORA = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


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
        self.cursor, self.transacciones, self.revertidas = cursor, 0, 0

    @asynccontextmanager
    async def read(self):
        yield self.cursor

    @asynccontextmanager
    async def transaction(self):
        self.transacciones += 1
        try:
            yield self.cursor
        except BaseException:
            self.revertidas += 1
            raise


def runtime(cursor, **servicios):
    return SimpleNamespace(database=Database(cursor), services=SimpleNamespace(**servicios))


def periodo(finalizada=FINALIZADA):
    return {"id": uuid4(), "cuatrimestre": "Septiembre-Diciembre 2026", "periodo_label": "Septiembre-Diciembre 2026",
            "fecha_inicio": date(2026, 9, 1), "fecha_fin": date(2026, 12, 31), "abierto": False, "cerrado": True,
            "cerrado_at": FINALIZADA, "evaluacion_finalizada_en": finalizada}


def fila_documentos(n, **extra):
    fila = {"reporte_id": uuid4(), "ordinal": n, "version": 1, "semana_inicio": date(2026, 9, 7),
            "semana_fin": date(2026, 9, 13), "fecha_inicio": date(2026, 9, 7), "fecha_fin": date(2026, 9, 11),
            "nota": 9, "original_clave": f"{n:032x}.pdf", "original_sha": "1" * 64, "original_tamano": 100,
            "firmado_clave": f"{n + 100:032x}.pdf", "firmado_sha": "2" * 64, "firmado_tamano": 120,
            "original_id": uuid4(), "original_archivado": None, "original_purga": None,
            "firmado_id": uuid4(), "firmado_archivado": None, "firmado_purga": None}
    fila.update(extra)
    return fila


FRASE = "DEPURAR Septiembre-Diciembre 2026 TII"


class ArchivadoTests(unittest.TestCase):
    def test_archived_document_answers_410_with_the_date_and_reassurance(self):
        with self.assertRaises(ApplicationError) as caught:
            archivado.exigir_vigente({"original_archivado": FINALIZADA}, "original")
        self.assertEqual(caught.exception.status_code, 410)
        self.assertIn("se conservan", caught.exception.detail)

    def test_only_the_requested_document_is_checked(self):
        archivado.exigir_vigente({"original_archivado": FINALIZADA, "firmado_archivado": None}, "firmado")
        archivado.exigir_vigente({}, "original")


class DescargasArchivadasTests(unittest.IsolatedAsyncioTestCase):
    async def test_staff_download_of_an_archived_document_is_410_and_never_reads_storage(self):
        leer = AsyncMock()
        cursor = ScriptCursor(uno={"dual.expediente.documentos_aprobados": [
            {"original": "a" * 32 + ".pdf", "firmado": "b" * 32 + ".pdf", "matricula": "1",
             "original_archivado": FINALIZADA, "firmado_archivado": FINALIZADA}]})
        with self.assertRaises(ApplicationError) as caught:
            await expediente.descargar_aprobado(uuid4(), 1, "firmado", {}, runtime=runtime(cursor, leer_documento=leer))
        self.assertEqual(caught.exception.status_code, 410)
        leer.assert_not_called()


class ExpedienteArchivoTests(unittest.TestCase):
    def test_archive_state_is_normal_scheduled_or_archived_and_never_hides_grades(self):
        p = {"periodo_label": "X"}
        self.assertEqual(expediente._archivo([], p, "1", False)["estado"], "normal")
        programada = {"estado": "programada", "ejecutar_en": AHORA, "purga_id": uuid4(), "completada_en": None}
        a = expediente._archivo([programada], p, "1", False)
        self.assertEqual((a["estado"], a["eliminacion_en"], a["purga_id"]),
                         ("programada", AHORA.date(), programada["purga_id"]))
        self.assertNotIn("purga_id", expediente._archivo([programada], p, "1", True))
        hecha = {"estado": "completada", "ejecutar_en": AHORA, "purga_id": uuid4(), "completada_en": AHORA}
        a = expediente._archivo([hecha], p, "1", False)
        self.assertEqual((a["estado"], a["archivado_en"]), ("archivado", AHORA.date()))

    def test_archived_period_makes_the_package_unavailable_for_student_and_staff(self):
        per = expediente.presentar_periodo(periodo())
        archivo = {"estado": "archivado", "archivado_en": AHORA.date()}
        for propio in (True, False):
            paquete = expediente._paquete(per, periodo(), propio, AHORA, archivo)
            self.assertFalse(paquete["disponible"])
            self.assertIn("se conservan", paquete["motivo"])
        self.assertTrue(expediente._paquete(per, periodo(), False, AHORA, {"estado": "programada"})["disponible"])


class PaqueteDepuradoTests(unittest.IsolatedAsyncioTestCase):
    async def test_package_generation_is_refused_once_files_were_purged(self):
        cursor = ScriptCursor(
            todos={"dual.cierres.resultados": [], "dual.paquetes.documentos": [fila_documentos(1, original_archivado=AHORA)]})
        alumno = {"matricula": "1", "nombre": "Ana", "nomenclatura": "G", "carrera": "TI", "carrera_codigo": "TII"}
        with self.assertRaises(ApplicationError) as caught:
            await paquetes._plan(cursor, periodo(), [alumno])
        self.assertEqual(caught.exception.status_code, 409)


class ProgramarTests(unittest.IsolatedAsyncioTestCase):
    def escenario(self, documentos=None, paquete="ok", existente=None, per=None):
        per = per or periodo()
        documentos = [fila_documentos(1), fila_documentos(2)] if documentos is None else documentos
        total = sum(2 for _ in documentos)
        uno = {"dual.cierres.periodo": [per], "dual.purgas.programada_de_alcance": [existente] if existente else [],
               "dual.purgas.paquete_vigente": [{"id": uuid4(), "generado_en": AHORA, "archivos": total,
                                                "manifiesto_sha256": "f" * 64}] if paquete == "ok" else
               [{"id": uuid4(), "generado_en": AHORA, "archivos": total + 1, "manifiesto_sha256": "f" * 64}] if paquete == "distinto" else [],
               "dual.purgas.insertar": [{"id": uuid4(), "solicitada_en": AHORA, "ejecutar_en": AHORA + timedelta(days=7)}]}
        todos = {"dual.paquetes.alumnos_carrera": [{"matricula": "1", "nombre": "Ana", "nomenclatura": "G",
                                                    "carrera": "TI", "carrera_codigo": "TII"}],
                 "dual.paquetes.documentos": documentos}
        cursor = ScriptCursor(uno=uno, todos=todos)
        return per, cursor, runtime(cursor)

    async def llamar(self, rt, per, **cambios):
        argumentos = dict(carrera="tii", matricula=None, confirmar=True, frase=FRASE)
        argumentos.update(cambios)
        return await purgas.programar(per["id"], user={"id": uuid4()}, runtime=rt, **argumentos)

    async def test_schedules_with_grace_and_marks_the_documents_without_deleting(self):
        per, cursor, rt = self.escenario()
        resultado = await self.llamar(rt, per)
        self.assertFalse(resultado["repetido"])
        self.assertEqual((resultado["purga"]["archivos"], resultado["purga"]["bytes"]), (4, 440))
        insertar = next(p for k, p in cursor.calls if k == "dual.purgas.insertar")
        self.assertEqual(insertar[7], purgas.GRACIA_DIAS)
        marcar = next(p for k, p in cursor.calls if k == "dual.purgas.marcar_documentos")
        self.assertEqual(len(marcar[1]), 4)
        self.assertNotIn("dual.purgas.archivar_documento", cursor.claves)

    async def test_validates_confirmation_scope_and_phrase_before_touching_the_database(self):
        per, cursor, rt = self.escenario()
        for cambios, estado in (({"confirmar": False}, 422), ({"confirmar": "si"}, 422),
                                ({"carrera": None}, 422), ({"matricula": "1"}, 422),
                                ({"frase": "depurar septiembre"}, 422), ({"carrera": "ZZZ"}, 404),
                                ({"frase": "x\x00"}, 422)):
            with self.assertRaises(ApplicationError) as caught:
                await self.llamar(rt, per, **cambios)
            self.assertEqual(caught.exception.status_code, estado, cambios)
        self.assertNotIn("dual.purgas.insertar", cursor.claves)

    async def test_requires_a_finalized_period_and_a_matching_package(self):
        casos = (("sin paquete", dict(paquete="no"), None), ("paquete distinto", dict(paquete="distinto"), None),
                 ("sin archivos", dict(documentos=[]), None), ("no finalizado", {}, periodo(finalizada=None)))
        for nombre, kwargs, per in casos:
            p, cursor, rt = self.escenario(per=per, **kwargs)
            with self.assertRaises(ApplicationError) as caught:
                await self.llamar(rt, p)
            self.assertEqual(caught.exception.status_code, 409, nombre)
            self.assertNotIn("dual.purgas.insertar", cursor.claves, nombre)

    async def test_repeating_returns_the_existing_schedule_and_conflicts_are_refused(self):
        existente = {"id": uuid4(), "estado": "programada", "ejecutar_en": AHORA, "archivos": 4, "bytes": 440}
        per, cursor, rt = self.escenario(existente=existente)
        self.assertTrue((await self.llamar(rt, per))["repetido"])
        self.assertNotIn("dual.purgas.insertar", cursor.claves)
        per, cursor, rt = self.escenario(documentos=[fila_documentos(1, original_purga=uuid4())])
        with self.assertRaises(ApplicationError) as caught:
            await self.llamar(rt, per)
        self.assertEqual(caught.exception.status_code, 409)
        per, cursor, rt = self.escenario(documentos=[fila_documentos(1, original_archivado=AHORA, firmado_archivado=AHORA)])
        with self.assertRaises(ApplicationError) as caught:
            await self.llamar(rt, per)
        self.assertIn("ya están depurados", caught.exception.detail)

    async def test_already_archived_documents_count_for_the_package_but_are_not_marked_again(self):
        docs = [fila_documentos(1, original_archivado=AHORA, firmado_archivado=AHORA), fila_documentos(2)]
        per, cursor, rt = self.escenario(documentos=docs)
        resultado = await self.llamar(rt, per)
        self.assertEqual(resultado["purga"]["archivos"], 2)


class CancelarTests(unittest.IsolatedAsyncioTestCase):
    async def test_expired_or_started_purge_never_releases_documents(self):
        # La autorización se decide atómicamente por SQL, con reloj del servidor.
        cursor = ScriptCursor(uno={"dual.purgas.obtener": [{"id": uuid4(), "estado": "programada"}]})
        with self.assertRaises(ApplicationError) as caught:
            await purgas.cancelar(uuid4(), uuid4(), {"id": uuid4()}, runtime=runtime(cursor))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("dual.purgas.liberar_documentos", cursor.claves)

    async def test_cancel_frees_the_documents_and_is_idempotent(self):
        purga = {"id": uuid4(), "estado": "programada", "ejecutar_en": AHORA}
        cursor = ScriptCursor(uno={"dual.purgas.obtener": [purga], "dual.purgas.cancelar": [{"id": purga["id"]}]})
        resultado = await purgas.cancelar(uuid4(), purga["id"], {"id": uuid4()}, runtime=runtime(cursor))
        self.assertEqual(resultado["purga"]["estado"], "cancelada")
        self.assertIn("dual.purgas.liberar_documentos", cursor.claves)
        cursor = ScriptCursor(uno={"dual.purgas.obtener": [{**purga, "estado": "cancelada"}]})
        self.assertTrue((await purgas.cancelar(uuid4(), purga["id"], {"id": uuid4()}, runtime=runtime(cursor)))["repetido"])
        self.assertNotIn("dual.purgas.liberar_documentos", cursor.claves)

    async def test_a_completed_purge_cannot_be_cancelled_and_unknown_ids_are_404(self):
        cursor = ScriptCursor(uno={"dual.purgas.obtener": [{"id": uuid4(), "estado": "completada"}]})
        with self.assertRaises(ApplicationError) as caught:
            await purgas.cancelar(uuid4(), uuid4(), {"id": uuid4()}, runtime=runtime(cursor))
        self.assertEqual(caught.exception.status_code, 409)
        with self.assertRaises(ApplicationError) as caught:
            await purgas.cancelar(uuid4(), uuid4(), {"id": uuid4()}, runtime=runtime(ScriptCursor()))
        self.assertEqual(caught.exception.status_code, 404)


class EjecutarTests(unittest.IsolatedAsyncioTestCase):
    def cursor(self, documentos):
        fila = {"id": uuid4(), "archivos": len(documentos), "bytes": sum(d["tamano"] for d in documentos)}
        return ScriptCursor(uno={"dual.purgas.bloquear_vencida": [fila] * (len(documentos) + 2),
                                 "dual.purgas.siguiente_documento": documentos})

    async def test_deletes_files_then_archives_rows_and_completes(self):
        docs = [{"id": uuid4(), "clave": "a" * 32 + ".pdf", "tamano": 10}, {"id": uuid4(), "clave": "b" * 32 + ".pdf", "tamano": 20}]
        cursor, borrar = self.cursor(docs), AsyncMock(return_value=True)
        resultado = await purgas.ejecutar_purga(runtime(cursor, purgar_documento=borrar), uuid4())
        self.assertEqual((resultado["archivos"], resultado["bytes"]), (2, 30))
        self.assertEqual(borrar.await_count, 2)
        self.assertEqual(cursor.claves.count("dual.purgas.archivar_documento"), 2)
        self.assertEqual(cursor.claves[-1], "dual.purgas.completar")

    async def test_a_failure_rolls_back_records_the_error_and_leaves_the_purge_pending(self):
        docs = [{"id": uuid4(), "clave": "a" * 32 + ".pdf", "tamano": 10}]
        cursor = self.cursor(docs)
        rt = runtime(cursor, purgar_documento=AsyncMock(side_effect=OSError("disco")))
        with self.assertRaises(OSError):
            await purgas.ejecutar_purga(rt, uuid4())
        self.assertEqual(rt.database.revertidas, 1)
        self.assertNotIn("dual.purgas.completar", cursor.claves)
        self.assertEqual(cursor.claves[-1], "dual.purgas.registrar_error")

    async def test_second_file_failure_commits_start_and_first_file_separately(self):
        docs = [{"id": uuid4(), "clave": f"{n:032x}.pdf", "tamano": 10} for n in (1, 2)]
        cursor = self.cursor(docs)
        rt = runtime(cursor)
        async def borrar(clave):
            if clave == docs[1]["clave"]:
                self.assertEqual(rt.database.transacciones, 3)
                self.assertIn("dual.purgas.archivar_documento", cursor.claves)
                raise OSError("segundo archivo")
            self.assertEqual(rt.database.transacciones, 2, "El inicio debe estar confirmado antes de borrar")
        rt.services.purgar_documento = borrar
        with self.assertRaises(OSError):
            await purgas.ejecutar_purga(rt, uuid4())
        self.assertEqual(cursor.claves.count("dual.purgas.archivar_documento"), 1)
        self.assertEqual(rt.database.revertidas, 1)
        self.assertNotIn("dual.purgas.completar", cursor.claves)

    async def test_retry_returns_original_totals_even_if_only_one_file_remains(self):
        fila = {"id": uuid4(), "archivos": 2, "bytes": 30}
        cursor = ScriptCursor(uno={"dual.purgas.bloquear_vencida": [fila] * 3,
            "dual.purgas.siguiente_documento": [{"id": uuid4(), "clave": "a" * 32 + ".pdf", "tamano": 20}]})
        borrar = AsyncMock(return_value=False)  # Ya ausente: interrupción entre borrado y commit.
        result = await purgas.ejecutar_purga(runtime(cursor, purgar_documento=borrar), fila["id"])
        self.assertEqual((result["archivos"], result["bytes"]), (2, 30))
        self.assertEqual(borrar.await_count, 1)

    async def test_not_due_or_locked_purges_do_nothing(self):
        cursor = ScriptCursor()
        borrar = AsyncMock()
        self.assertIsNone(await purgas.ejecutar_purga(runtime(cursor, purgar_documento=borrar), uuid4()))
        borrar.assert_not_called()

    async def test_manual_execution_reports_completed_cancelled_and_not_due(self):
        pid = uuid4()
        casos = (("completada", None, True), ("cancelada", None, 409), ("programada", None, 409))
        for estado, _, esperado in casos:
            cursor = ScriptCursor(todos={"dual.purgas.listar_periodo": [{"id": pid, "estado": estado}]})
            rt = runtime(cursor, purgar_documento=AsyncMock())
            if esperado is True:
                self.assertTrue((await purgas.ejecutar_manual(uuid4(), pid, {}, runtime=rt))["repetido"])
            else:
                with self.assertRaises(ApplicationError) as caught:
                    await purgas.ejecutar_manual(uuid4(), pid, {}, runtime=rt)
                self.assertEqual(caught.exception.status_code, esperado)
        with self.assertRaises(ApplicationError) as caught:
            await purgas.ejecutar_manual(uuid4(), pid, {}, runtime=runtime(ScriptCursor()))
        self.assertEqual(caught.exception.status_code, 404)

    async def test_manual_execution_failure_is_reported_without_internals_and_stays_pending(self):
        pid = uuid4()
        cursor = ScriptCursor(todos={"dual.purgas.listar_periodo": [{"id": pid, "estado": "programada"}]})
        with patch.object(purgas, "ejecutar_purga", AsyncMock(side_effect=OSError("/ruta/interna"))):
            with self.assertRaises(ApplicationError) as caught:
                await purgas.ejecutar_manual(uuid4(), pid, {}, runtime=runtime(cursor))
        self.assertEqual(caught.exception.status_code, 500)
        self.assertNotIn("/ruta/interna", caught.exception.detail)

    async def test_one_failing_purge_does_not_stop_the_others(self):
        llamadas = []

        async def falsa(rt, purga_id):
            llamadas.append(purga_id)
            if len(llamadas) == 1:
                raise OSError("x")
            return {"id": purga_id}

        cursor = ScriptCursor(todos={"dual.purgas.vencidas": [{"id": uuid4()}, {"id": uuid4()}]})
        with patch.object(purgas, "ejecutar_purga", falsa):
            self.assertEqual(await purgas.ejecutar_vencidas(runtime(cursor)), 1)
        self.assertEqual(len(llamadas), 2)


class ResumenTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_states_and_phrase_per_career(self):
        per = periodo()
        cursor = ScriptCursor(
            uno={"dual.cierres.periodo": [per]},
            todos={"dual.purgas.resumen_carreras": [
                {"carrera": "TII", "alumnos": 2, "archivos_total": 4, "archivos_vigentes": 4, "bytes_vigentes": 440},
                {"carrera": "MER", "alumnos": 1, "archivos_total": 2, "archivos_vigentes": 0, "bytes_vigentes": 0}],
                "dual.purgas.paquetes_vigentes": [{"id": uuid4(), "carrera": "TII", "generado_en": AHORA, "archivos": 4}]})
        resultado = await purgas.resumen(per["id"], {}, runtime=runtime(cursor))
        por_codigo = {c["codigo"]: c for c in resultado["carreras"]}
        self.assertTrue(por_codigo["TII"]["puede_depurar"])
        self.assertEqual(por_codigo["TII"]["frase_esperada"], FRASE)
        self.assertEqual(por_codigo["MER"]["estado"], "depurado")
        self.assertFalse(por_codigo["MER"]["puede_depurar"])
        self.assertEqual(resultado["gracia_dias"], 7)

    async def test_an_unfinalized_period_cannot_be_purged(self):
        per = periodo(finalizada=None)
        resultado = await purgas.resumen(per["id"], {}, runtime=runtime(ScriptCursor(uno={"dual.cierres.periodo": [per]})))
        self.assertFalse(resultado["finalizada"])
        self.assertEqual(resultado["carreras"], [])


class AlmacenamientoTests(unittest.IsolatedAsyncioTestCase):
    async def test_purgar_documento_deletes_is_idempotent_and_rejects_foreign_keys(self):
        clave = "a" * 32 + ".pdf"
        memoria = MemoriaAlmacenamiento()
        with registro.usar(memoria):
            memoria.guardar("documentos", clave, b"%PDF")
            self.assertTrue(await dual_reports.purgar_documento(clave))
            self.assertFalse(memoria.existe("documentos", clave))
            self.assertFalse(await dual_reports.purgar_documento(clave), "Un archivo ausente cuenta como eliminado")
            with self.assertRaises(ApplicationError):
                await dual_reports.purgar_documento("../../etc/passwd")

    async def test_an_unavailable_storage_propagates_so_the_purge_stays_pending(self):
        class Caido(MemoriaAlmacenamiento):
            def eliminar(self, espacio, clave):
                raise AlmacenamientoNoDisponible("sin red", "red")

        with registro.usar(Caido()):
            with self.assertRaises(OSError):
                await dual_reports.purgar_documento("b" * 32 + ".pdf")

class SqlContractTests(unittest.TestCase):
    def test_migration_009_protects_documents_and_the_purge_registry(self):
        sql = (Path(__file__).resolve().parents[2] / "database/migrations/009_depuracion.sql").read_text(encoding="utf-8")
        for fragmento in ("CREATE TABLE IF NOT EXISTS public.purgas_archivo", "purgas_protegidas",
                          "documentos_protegidos", "idx_purgas_programada_unica", "ENABLE ROW LEVEL SECURITY",
                          "Un documento archivado no se restablece", "documentos_archivado_con_purga"):
            self.assertIn(fragmento, sql)

    def test_every_purge_query_binds_its_parameters(self):
        from app.infrastructure.database.queries.dual_purgas import QUERIES
        esperados = {"dual.purgas.insertar": 10, "dual.purgas.marcar_documentos": 2, "dual.purgas.obtener": 2,
                     "dual.purgas.cancelar": 2, "dual.purgas.estado_alumno": 4, "dual.purgas.resumen_carreras": 1,
                     "dual.purgas.paquete_vigente": 5, "dual.purgas.programada_de_alcance": 4}
        for clave, cantidad in esperados.items():
            self.assertEqual(QUERIES[clave]["sql"].count("%s"), cantidad, clave)


if __name__ == "__main__":
    unittest.main()
