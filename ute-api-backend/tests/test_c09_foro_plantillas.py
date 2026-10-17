import io
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import fitz

from app.application.dto.foro import BuzonMensajeCreate
from app.application.errors import ApplicationError
from app.application.use_cases.dual import plantillas
from app.application.use_cases.foro import buzon, publicaciones
from app.infrastructure.documents import plantillas as almacen
from test_c08b_depuracion import Database, ScriptCursor, runtime

AHORA = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
TIPO_PRINCIPAL = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def docx(extras=None, tipos=None, sin=()):
    """DOCX mínimo válido (ZIP OOXML) con las partes indispensables."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        if "[Content_Types].xml" not in sin:
            z.writestr("[Content_Types].xml",
                       tipos or f'<Types><Override PartName="/word/document.xml" ContentType="{TIPO_PRINCIPAL}"/></Types>')
        if "word/document.xml" not in sin:
            z.writestr("word/document.xml", "<w:document/>")
        for nombre, datos in (extras or {}).items():
            z.writestr(nombre, datos)
    return memoria.getvalue()


def pdf(paginas=1):
    d = fitz.open()
    for n in range(paginas):
        d.new_page().insert_text((72, 72), f"plantilla {n}")
    contenido = d.tobytes()
    d.close()
    return contenido


class Subida:
    def __init__(self, nombre, contenido):
        self.filename, self._datos, self._pos = nombre, contenido, 0

    async def read(self, n=-1):
        bloque = self._datos[self._pos:self._pos + n] if n >= 0 else self._datos[self._pos:]
        self._pos += len(bloque)
        return bloque


class InspeccionDocxTests(unittest.TestCase):
    def rechaza(self, contenido, texto=None):
        with self.assertRaises(ApplicationError) as caught:
            almacen.inspeccionar_docx(contenido)
        self.assertEqual(caught.exception.status_code, 422, caught.exception.detail)
        if texto:
            self.assertIn(texto, caught.exception.detail)

    def test_valid_docx_is_accepted(self):
        almacen.inspeccionar_docx(docx())

    def test_rejects_fake_corrupt_and_incomplete_files(self):
        self.rechaza(b"")
        self.rechaza(b"MZ\x90\x00 esto es un ejecutable")
        self.rechaza(b"PK\x03\x04 no es un zip de verdad")
        self.rechaza(docx(sin=("word/document.xml",)), "estructura")
        self.rechaza(docx(sin=("[Content_Types].xml",)), "estructura")

    def test_rejects_macros_unsafe_paths_and_wrong_type(self):
        self.rechaza(docx(extras={"word/vbaProject.bin": b"x"}), "macros")
        self.rechaza(docx(tipos='<Types><Override ContentType="application/vnd.ms-word.document.macroEnabled.main+xml"/></Types>'))
        self.rechaza(docx(tipos="<Types/>"), "sin macros")
        self.rechaza(docx(extras={"../evil.xml": b"x"}), "rutas")
        self.rechaza(docx(extras={"/abs.xml": b"x"}), "rutas")

    def test_rejects_zip_bombs_and_oversized_structures(self):
        self.rechaza(docx(extras={"word/relleno.xml": b"0" * (5 * 1024 * 1024)}), "compresión")
        with patch.object(almacen, "MAX_DOCX_ENTRADAS", 3):
            self.rechaza(docx(extras={"a": b"1", "b": b"2"}), "demasiadas")
        with patch.object(almacen, "MAX_DOCX_DESCOMPRIMIDO", 10), patch.object(almacen, "MAX_DOCX_RAZON", 10 ** 9):
            self.rechaza(docx(), "descomprimido")

    def test_pdf_goes_through_the_c05_inspector(self):
        self.assertEqual(almacen.inspeccionar(pdf(2), "pdf"), 2)
        with self.assertRaises(ApplicationError):
            almacen.inspeccionar(b"%PDF-1.4 roto", "pdf")


class CargaYAlmacenamientoTests(unittest.IsolatedAsyncioTestCase):
    async def test_extension_and_size_limits(self):
        with self.assertRaises(ApplicationError) as caught:
            await almacen.leer_limitado(Subida("a.pdf", b"x"), "docx")
        self.assertEqual(caught.exception.status_code, 422)
        with patch.object(almacen, "MAX_PLANTILLA_BYTES", 10):
            with self.assertRaises(ApplicationError) as caught:
                await almacen.leer_limitado(Subida("a.docx", b"x" * 11), "docx")
            self.assertEqual(caught.exception.status_code, 413)
            self.assertEqual(await almacen.leer_limitado(Subida("A.DOCX", b"x" * 10), "docx"), b"x" * 10)

    async def test_storage_uses_server_keys_never_overwrites_and_rejects_foreign_keys(self):
        with tempfile.TemporaryDirectory() as raiz, patch.object(almacen, "_raiz", return_value=Path(raiz)):
            a = await almacen.guardar_plantilla(b"uno", "docx")
            b = await almacen.guardar_plantilla(b"uno", "docx")
            self.assertNotEqual(a["clave"], b["clave"])
            self.assertTrue(a["clave"].endswith(".docx") and len(a["sha256"]) == 64)
            self.assertEqual(await almacen.leer_plantilla(a["clave"]), b"uno")
            await almacen.eliminar_plantilla(a["clave"])
            with self.assertRaises(ApplicationError):
                await almacen.leer_plantilla(a["clave"])
            await almacen.eliminar_plantilla(a["clave"])  # idempotente
            for malo in ("../../etc/passwd", "x.docx", "a" * 32 + ".exe"):
                with self.assertRaises(ApplicationError):
                    almacen.ruta_plantilla(malo)
            with self.assertRaises(ApplicationError):
                await almacen.guardar_plantilla(b"x", "exe")


def servicios_reales(**cambios):
    base = dict(
        leer_limitado_plantilla=almacen.leer_limitado, inspeccionar_plantilla=almacen.inspeccionar,
        guardar_plantilla=AsyncMock(side_effect=[{"clave": "a" * 32 + ".docx", "tamano": 10, "sha256": "1" * 64},
                                                 {"clave": "b" * 32 + ".pdf", "tamano": 20, "sha256": "2" * 64}]),
        eliminar_plantilla=AsyncMock(), leer_plantilla=AsyncMock(return_value=b"contenido"))
    base.update(cambios)
    return base


class PublicarTests(unittest.IsolatedAsyncioTestCase):
    def cursor(self):
        return ScriptCursor(uno={"dual.plantillas.siguiente_numero": [{"numero": 3}],
                                 "dual.plantillas.insertar": [{"id": uuid4(), "numero": 3, "publicada_en": AHORA}]})

    async def publicar(self, rt, word=None, pdf_=None, nota=None):
        return await plantillas.publicar(word or Subida("p.docx", docx()), pdf_ or Subida("p.pdf", pdf(2)), nota,
                                         {"id": uuid4()}, runtime=rt)

    async def test_publishes_the_pair_atomically_with_the_next_number(self):
        cursor = self.cursor()
        servicios = servicios_reales()
        resultado = await self.publicar(runtime(cursor, **servicios), nota=" Nueva versión ")
        self.assertEqual((resultado["numero"], resultado["pdf"]["paginas"], resultado["vigente"]), (3, 2, True))
        self.assertEqual(cursor.claves, ["dual.plantillas.bloquear", "dual.plantillas.siguiente_numero",
                                         "dual.plantillas.retirar_vigente", "dual.plantillas.insertar"])
        self.assertEqual(next(p for k, p in cursor.calls if k == "dual.plantillas.insertar")[2], "Nueva versión")
        servicios["eliminar_plantilla"].assert_not_called()

    async def test_an_invalid_file_stores_nothing(self):
        for word, pdf_ in ((Subida("p.docx", b"no es word"), None), (None, Subida("p.pdf", b"%PDF roto")),
                           (Subida("p.doc", docx()), None), (None, Subida("p.txt", b"x"))):
            servicios = servicios_reales()
            cursor = self.cursor()
            with self.assertRaises(ApplicationError):
                await self.publicar(runtime(cursor, **servicios), word, pdf_)
            servicios["guardar_plantilla"].assert_not_called()
            self.assertEqual(cursor.calls, [])

    async def test_a_failure_saving_the_second_file_or_in_the_database_leaves_no_files(self):
        guardar = AsyncMock(side_effect=[{"clave": "a" * 32 + ".docx", "tamano": 1, "sha256": "1" * 64}, OSError("disco")])
        servicios = servicios_reales(guardar_plantilla=guardar)
        cursor = self.cursor()
        with self.assertRaises(OSError):
            await self.publicar(runtime(cursor, **servicios))
        servicios["eliminar_plantilla"].assert_awaited_once_with("a" * 32 + ".docx")
        self.assertEqual(cursor.calls, [], "No se tocó la base de datos")
        servicios = servicios_reales()
        cursor = self.cursor()

        async def falla(query, params=None):
            if query == "dual.plantillas.insertar":
                raise RuntimeError("base")
            cursor.calls.append((query, params))
            cursor._ultimo = query

        cursor.execute = falla
        with self.assertRaises(RuntimeError):
            await self.publicar(runtime(cursor, **servicios))
        self.assertEqual({c.args[0] for c in servicios["eliminar_plantilla"].await_args_list},
                         {"a" * 32 + ".docx", "b" * 32 + ".pdf"})

    async def test_note_length_is_limited(self):
        with self.assertRaises(ApplicationError) as caught:
            await self.publicar(runtime(self.cursor(), **servicios_reales()), nota="x" * 201)
        self.assertEqual(caught.exception.status_code, 422)


class ConsultaTests(unittest.IsolatedAsyncioTestCase):
    def fila(self, numero=2):
        return {"id": uuid4(), "numero": numero, "publicada_en": AHORA, "vigente": True, "nota": None,
                "publicada_por_nombre": "Coord", "word_clave": "a" * 32 + ".docx", "word_tamano": 10,
                "word_sha256": "1" * 64, "pdf_clave": "b" * 32 + ".pdf", "pdf_tamano": 20, "pdf_sha256": "2" * 64,
                "pdf_paginas": 3}

    async def test_current_version_metadata_without_storage_keys_or_none(self):
        cursor = ScriptCursor(uno={"dual.plantillas.vigente": [self.fila()]})
        resultado = await plantillas.vigente({}, runtime=runtime(cursor))
        self.assertEqual(resultado["vigente"]["numero"], 2)
        self.assertNotIn("clave", str(resultado))
        self.assertIsNone((await plantillas.vigente({}, runtime=runtime(ScriptCursor())))["vigente"])

    async def test_download_names_are_generated_and_unknown_versions_are_404(self):
        for tipo, extension in (("word", "docx"), ("pdf", "pdf")):
            cursor = ScriptCursor(uno={"dual.plantillas.por_numero": [self.fila()]})
            leer = AsyncMock(return_value=b"contenido")
            resultado = await plantillas.descargar(2, tipo, {}, runtime=runtime(cursor, leer_plantilla=leer))
            self.assertIn(f'filename="Plantilla_Reporte_Dual_v2.{extension}"', resultado.headers["Content-Disposition"])
            leer.assert_awaited_once_with("a" * 32 + ".docx" if tipo == "word" else "b" * 32 + ".pdf")
        for numero, tipo in ((9, "word"), (2, "exe")):
            with self.assertRaises(ApplicationError) as caught:
                await plantillas.descargar(numero, tipo, {}, runtime=runtime(ScriptCursor(), leer_plantilla=AsyncMock()))
            self.assertEqual(caught.exception.status_code, 404)


class BuzonTests(unittest.IsolatedAsyncioTestCase):
    ALUMNO = {"id": uuid4(), "sub": "a@ute.edu.mx", "matricula": "1", "roles": {"alumno": True}}
    TUTOR = {"id": uuid4(), "sub": "t@ute.edu.mx", "roles": {"tutor_academico": True}}

    def cursor(self, estado, dueno=None):
        return ScriptCursor(uno={"foro.buzon.q000": [{"alumno_id": dueno or self.ALUMNO["id"], "area": "dual", "estado": estado}],
                                 "foro.buzon.q006": [{"id": uuid4(), "mensaje_id": uuid4(), "autor_id": uuid4(),
                                                      "autor_rol": "x", "texto": "t", "created_at": AHORA}]})

    async def test_replying_to_a_closed_thread_is_409_for_everyone_and_never_reopens(self):
        for user in (self.ALUMNO, self.TUTOR):
            cursor = self.cursor("Cerrado")
            with self.assertRaises(ApplicationError) as caught:
                await buzon.responder_mensaje(uuid4(), SimpleNamespace(texto="hola"), user, runtime=runtime(cursor))
            self.assertEqual(caught.exception.status_code, 409)
            self.assertNotIn("foro.buzon.q006", cursor.claves)
            self.assertNotIn("foro.buzon.reabrir", cursor.claves)

    async def test_open_threads_still_accept_replies(self):
        for estado in ("Enviado", "Leido"):
            cursor = self.cursor(estado)
            await buzon.responder_mensaje(uuid4(), SimpleNamespace(texto="hola"), self.ALUMNO, runtime=runtime(cursor))
            self.assertIn("foro.buzon.q006", cursor.claves)

    async def test_only_staff_reopen_and_reopening_an_open_thread_changes_nothing(self):
        with self.assertRaises(ApplicationError) as caught:
            await buzon.reabrir_mensaje(uuid4(), self.ALUMNO, runtime=runtime(self.cursor("Cerrado")))
        self.assertEqual(caught.exception.status_code, 403)
        cursor = self.cursor("Cerrado")
        self.assertFalse((await buzon.reabrir_mensaje(uuid4(), self.TUTOR, runtime=runtime(cursor)))["repetido"])
        self.assertIn("foro.buzon.reabrir", cursor.claves)
        cursor = self.cursor("Leido")
        self.assertTrue((await buzon.reabrir_mensaje(uuid4(), self.TUTOR, runtime=runtime(cursor)))["repetido"])
        self.assertNotIn("foro.buzon.reabrir", cursor.claves)

    async def test_new_thread_can_link_only_an_own_closed_thread(self):
        datos = lambda anterior: BuzonMensajeCreate(area="dual", asunto="Sigo con el tema", mensaje="Hola", hilo_anterior_id=anterior)
        nuevo = {"id": uuid4(), "correo": "a", "area": "dual", "asunto": "x", "mensaje": "y", "estado": "Enviado",
                 "created_at": AHORA, "hilo_anterior_id": None}
        anterior = uuid4()
        cursor = ScriptCursor(uno={"foro.buzon.hilo_propio": [{"id": anterior, "estado": "Cerrado"}], "foro.buzon.q001": [nuevo]})
        await buzon.enviar_mensaje(datos(anterior), self.ALUMNO, runtime=runtime(cursor))
        self.assertEqual(next(p for k, p in cursor.calls if k == "foro.buzon.q001")[-1], anterior)
        cursor = ScriptCursor(uno={"foro.buzon.q001": [nuevo]})  # no es suyo o no existe
        with self.assertRaises(ApplicationError) as caught:
            await buzon.enviar_mensaje(datos(uuid4()), self.ALUMNO, runtime=runtime(cursor))
        self.assertEqual(caught.exception.status_code, 404)
        cursor = ScriptCursor(uno={"foro.buzon.hilo_propio": [{"id": anterior, "estado": "Leido"}], "foro.buzon.q001": [nuevo]})
        with self.assertRaises(ApplicationError) as caught:
            await buzon.enviar_mensaje(datos(anterior), self.ALUMNO, runtime=runtime(cursor))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("foro.buzon.q001", cursor.claves)

    def test_marking_as_read_never_reopens_a_closed_thread(self):
        from app.infrastructure.database.queries.foro_buzon import QUERIES
        self.assertIn("estado = 'Enviado'", QUERIES["foro.buzon.q008"]["sql"])


class AnunciosTests(unittest.IsolatedAsyncioTestCase):
    def usuario(self, **roles):
        return {"id": uuid4(), "sub": "u@ute.edu.mx", "roles": roles}

    async def eliminar(self, autor, user, existe=True):
        cursor = ScriptCursor(uno={"foro.publicaciones.q005": [{"autor_id": autor}] if existe else []})
        resultado = await publicaciones.eliminar_publicacion(uuid4(), user, runtime=runtime(cursor))
        return cursor, resultado

    async def test_author_and_coordinator_may_delete_and_deletion_is_logical(self):
        tutor = self.usuario(tutor_academico=True)
        cursor, _ = await self.eliminar(tutor["id"], tutor)
        self.assertEqual(next(p for k, p in cursor.calls if k == "foro.publicaciones.q006")[0], tutor["id"])
        coordinador = self.usuario(coordinador_dual=True)
        cursor, _ = await self.eliminar(uuid4(), coordinador)
        self.assertIn("foro.publicaciones.q006", cursor.claves)

    async def test_another_tutor_cannot_delete_and_missing_announcements_are_404(self):
        for user, existe, estado in ((self.usuario(tutor_academico=True), True, 403), (self.usuario(coordinador_dual=True), False, 404)):
            with self.assertRaises(ApplicationError) as caught:
                await self.eliminar(uuid4(), user, existe)
            self.assertEqual(caught.exception.status_code, estado)

    def test_listing_and_reactions_hide_deleted_announcements(self):
        from app.infrastructure.database.queries.foro_publicaciones import QUERIES
        for clave in ("foro.publicaciones.q002", "foro.publicaciones.q005", "foro.publicaciones.q007"):
            self.assertIn("eliminada_en IS NULL", QUERIES[clave]["sql"], clave)
        self.assertNotIn("DELETE FROM foro_publicaciones", QUERIES["foro.publicaciones.q006"]["sql"])


class SqlContractTests(unittest.TestCase):
    def test_migration_010_protects_templates_threads_and_announcements(self):
        sql = (Path(__file__).resolve().parents[2] / "database/migrations/010_plantillas_foro.sql").read_text(encoding="utf-8")
        for fragmento in ("plantillas_inmutables", "idx_plantilla_vigente_unica", "buzon_respuesta_hilo_abierto",
                          "hilo_hilo_anterior" if False else "hilo_anterior_id", "foro_publicaciones_sin_edicion",
                          "Un anuncio eliminado no se restablece", "ENABLE ROW LEVEL SECURITY"):
            self.assertIn(fragmento, sql)

    def test_every_template_query_binds_its_parameters(self):
        from app.infrastructure.database.queries.dual_plantillas import QUERIES
        esperados = {"dual.plantillas.insertar": 10, "dual.plantillas.por_numero": 1, "dual.plantillas.vigente": 0}
        for clave, cantidad in esperados.items():
            self.assertEqual(QUERIES[clave]["sql"].count("%s"), cantidad, clave)


if __name__ == "__main__":
    unittest.main()
