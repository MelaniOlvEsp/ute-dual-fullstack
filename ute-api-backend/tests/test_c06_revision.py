import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import fitz
from PIL import Image

from app.application.errors import ApplicationError
from app.application.use_cases.dual import revisiones
from app.domain import reviews
from app.infrastructure.documents import signatures

ROOT = Path(__file__).resolve().parents[2]


# --- PDF sintético con la tabla de firmas del reporte semanal (réplica del formato) -----------

def firma_png(color=(20, 40, 160)):
    imagen = Image.new("RGB", (300, 100), (255, 255, 255))
    for x in range(20, 280):
        imagen.putpixel((x, 50 + int(20 * ((x % 40) / 40))), color)
    salida = BytesIO()
    imagen.save(salida, "PNG")
    return salida.getvalue()


def tabla_firmas(pagina, y=640, rellena=False):
    """Tabla Nombre | Firma | Calificación con tres filas; la del tutor es la última."""
    x = [52, 194, 328, 435, 560]
    filas = [y, y + 15, y + 48, y + 81, y + 114]
    for yy in filas:
        pagina.draw_line((x[0], yy), (x[-1], yy), width=1)
    for xx in x:
        pagina.draw_line((xx, filas[0]), (xx, filas[-1]), width=1)
    pagina.insert_text((250, y + 11), "Nombre", fontsize=9)
    pagina.insert_text((370, y + 11), "Firma", fontsize=9)
    pagina.insert_text((470, y + 11), "Calificación", fontsize=9)
    pagina.insert_text((60, y + 38), "Instructor", fontsize=9)
    pagina.insert_text((60, y + 71), "Formador", fontsize=9)
    pagina.insert_text((60, y + 104), "Tutor académico", fontsize=9)
    pagina.insert_text((200, y + 104), "Persona Sintetica", fontsize=9)
    if rellena:
        pagina.insert_text((340, y + 104), "ocupada", fontsize=9)
    return fitz.Rect(x[2], filas[3], x[3], filas[4])


def reporte_pdf(paginas=1, con_tabla=True, en_pagina=None, rellena=False, rotar=0):
    documento = fitz.open()
    celda = None
    for numero in range(paginas):
        pagina = documento.new_page()
        pagina.insert_text((72, 72), f"Reporte semanal {numero + 1}", fontsize=12)
        if con_tabla and numero == (paginas - 1 if en_pagina is None else en_pagina):
            celda = tabla_firmas(pagina, rellena=rellena)
        if rotar:
            pagina.set_rotation(rotar)
    contenido = documento.tobytes()
    documento.close()
    return contenido, celda


class CeldaDeFirmaTests(unittest.TestCase):
    def test_signature_is_stamped_inside_the_tutor_cell_without_touching_the_rest(self):  # C06-AC8
        original, celda = reporte_pdf()
        firmado, modo = signatures.estampar_firma(original, firma_png(), "Tutor Sintetico")
        self.assertEqual(modo, "celda")
        with fitz.open(stream=original, filetype="pdf") as antes, \
                fitz.open(stream=firmado, filetype="pdf") as despues:
            self.assertEqual(despues.page_count, antes.page_count)  # sin hoja adicional
            self.assertEqual(despues[0].get_text(), antes[0].get_text())  # ni un texto cambia
            imagenes = despues[0].get_image_info()
            self.assertEqual(len(imagenes), 1)
            caja = fitz.Rect(imagenes[0]["bbox"])
            self.assertTrue(celda.contains(caja), f"{caja} fuera de {celda}")
            self.assertGreater(caja.width, celda.width * 0.5)  # aprovecha la celda, legible

    def test_multi_page_report_is_stamped_on_the_page_that_has_the_table(self):
        original, celda = reporte_pdf(paginas=3, en_pagina=1)
        firmado, modo = signatures.estampar_firma(original, firma_png(), "Tutor")
        self.assertEqual(modo, "celda")
        with fitz.open(stream=firmado, filetype="pdf") as despues:
            self.assertEqual(despues.page_count, 3)
            self.assertEqual([len(p.get_image_info()) for p in despues], [0, 1, 0])

    def test_unrecognised_format_falls_back_to_an_extra_sheet(self):  # respaldo DP-07
        original, _ = reporte_pdf(paginas=2, con_tabla=False)
        firmado, modo = signatures.estampar_firma(original, firma_png(), "Tutor")
        self.assertEqual(modo, "hoja_adicional")
        with fitz.open(stream=firmado, filetype="pdf") as despues:
            self.assertEqual(despues.page_count, 3)

    def test_occupied_cell_is_never_stamped_over(self):
        original, _ = reporte_pdf(rellena=True)
        with fitz.open(stream=original, filetype="pdf") as documento:
            self.assertIsNone(signatures.localizar_celda_firma(documento[0]))
        _, modo = signatures.estampar_firma(original, firma_png(), "Tutor")
        self.assertEqual(modo, "hoja_adicional")

    def test_rotated_pages_use_the_fallback(self):
        original, _ = reporte_pdf(rotar=90)
        self.assertEqual(signatures.estampar_firma(original, firma_png(), "Tutor")[1], "hoja_adicional")

    def test_invalid_signature_image_is_rejected(self):
        original, _ = reporte_pdf()
        with self.assertRaises(ApplicationError):
            signatures.estampar_firma(original, b"no es una imagen", "Tutor")

    def test_original_bytes_are_not_modified(self):
        original, _ = reporte_pdf()
        copia = bytes(original)
        signatures.estampar_firma(original, firma_png(), "Tutor")
        self.assertEqual(original, copia)


# --- Reglas de dominio ------------------------------------------------------------------------

class DominioTests(unittest.TestCase):
    VERSION = {"nota": 8, "fecha_inicio": date(2026, 10, 12), "fecha_fin": date(2026, 10, 16)}

    def test_rejection_requires_an_observation(self):  # RN-14
        for texto in (None, "", "   "):
            with self.assertRaises(reviews.RevisionInvalida):
                reviews.validar_decision("Rechazada", texto)
        self.assertEqual(reviews.validar_decision("Rechazada", "  Falta la firma  "), "Falta la firma")
        self.assertIsNone(reviews.validar_decision("Aprobada", None))
        with self.assertRaises(reviews.RevisionInvalida):
            reviews.validar_decision("Pendiente", "x")
        with self.assertRaises(reviews.RevisionInvalida):
            reviews.validar_decision("Aprobada", "x" * 1001)

    def test_corrected_values_default_to_the_declared_ones(self):
        self.assertEqual(reviews.valores_validados(self.VERSION),
                         (8, date(2026, 10, 12), date(2026, 10, 16)))
        self.assertEqual(reviews.correcciones(self.VERSION, 8, date(2026, 10, 12), date(2026, 10, 16)), [])

    def test_note_and_dates_follow_the_same_rules_as_delivery(self):  # AC-12
        for nota in (0, 11, "8.5", True):
            with self.assertRaises(reviews.RevisionInvalida, msg=repr(nota)):
                reviews.valores_validados(self.VERSION, nota=nota)
        with self.assertRaises(reviews.RevisionInvalida):
            reviews.valores_validados(self.VERSION, fecha_inicio=date(2026, 10, 17))
        self.assertEqual(reviews.valores_validados(self.VERSION, nota=10)[0], 10)

    def test_corrections_keep_previous_and_new_values(self):  # RN-15
        cambios = reviews.correcciones(self.VERSION, 9, date(2026, 10, 13), date(2026, 10, 16))
        self.assertEqual(cambios, [("fecha_inicio", "2026-10-12", "2026-10-13"), ("nota", "8", "9")])


# --- Casos de uso con dobles ------------------------------------------------------------------

class ScriptCursor:
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
        return list(self.guion.get(self._ultimo, []))

    @property
    def claves(self):
        return [c[0] for c in self.calls]


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


TUTOR = {"id": uuid4(), "sub": "tutor@example.test"}
REPORTE_ID = uuid4()
OBLIGACION_ID = uuid4()


def reporte(ultima=1, estado="Pendiente"):
    return {"id": REPORTE_ID, "obligacion_id": OBLIGACION_ID, "matricula": "123456789",
            "estado": estado, "semana": 3, "ultima": ultima}


def version(numero=1, revisada=None, **extra):
    fila = {"id": uuid4(), "numero": numero, "fecha_inicio": date(2026, 10, 12),
            "fecha_fin": date(2026, 10, 16), "nota": 8, "clave_original": "a" * 32 + ".pdf",
            "revision_id": None, "tutor_id": None, "decision": None, "observacion": None,
            "rev_inicio": None, "rev_fin": None, "rev_nota": None}
    if revisada:
        fila.update(revision_id=uuid4(), **revisada)
    fila.update(extra)
    return fila


def runtime_con(cursor, falla=None, modo="celda"):
    servicios = SimpleNamespace(
        leer_documento=AsyncMock(return_value=b"%PDF-original"),
        estampar_firma=lambda pdf, firma, nombre: (b"%PDF-firmado", modo),
        inspeccionar_pdf=lambda contenido: 2,
        guardar_documento=AsyncMock(return_value={
            "clave": "b" * 32 + ".pdf", "tamano": 12, "sha256": "e" * 64}),
        eliminar_documento=AsyncMock(),
    )
    return SimpleNamespace(database=Database(cursor, falla), services=servicios)


def guion(**extra):
    base = {
        "dual.revisiones.reporte": [reporte()],
        "dual.revisiones.reporte_bloqueado": [reporte()],
        "dual.revisiones.version": [version(), version()],
        "dual.tutor.get_signature": [{"imagen": b"png"}],
        "dual.tutor.identity": [{"nombre": "Tutor Sintetico"}],
        "dual.revisiones.insert_firmado": [{"id": uuid4()}],
        "dual.revisiones.insert_revision": [{"id": uuid4(), "revisado_en": datetime(2026, 10, 16, 9, 0)}],
    }
    base.update(extra)
    return base


async def revisar(runtime, decision="Aprobada", observacion=None, nota=None, inicio=None, fin=None, numero=1):
    return await revisiones.revisar(REPORTE_ID, numero, decision, observacion, nota, inicio, fin,
                                    TUTOR, runtime=runtime)


class RevisionTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejection_without_observation_is_422_and_touches_nothing(self):  # RN-14 / C06-AC3
        cursor = ScriptCursor(guion())
        runtime = runtime_con(cursor)
        with self.assertRaises(ApplicationError) as caught:
            await revisar(runtime, "Rechazada", "  ")
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(cursor.calls, [])

    async def test_rejection_records_revision_decision_and_legacy_columns_without_a_signed_file(self):  # AC3
        cursor = ScriptCursor(guion())
        runtime = runtime_con(cursor)
        resultado = await revisar(runtime, "Rechazada", "Falta la firma de la empresa")
        self.assertEqual((resultado["estado"], resultado["repetido"], resultado["firma"]),
                         ("Rechazada", False, None))
        self.assertIn("dual.revisiones.insert_revision", cursor.claves)
        self.assertIn("dual.revisiones.decidir_version", cursor.claves)
        self.assertNotIn("dual.revisiones.insert_firmado", cursor.claves)
        runtime.services.guardar_documento.assert_not_awaited()
        legado = next(c[1] for c in cursor.calls if c[0] == "dual.revisiones.actualizar_reporte")
        self.assertEqual(legado[:2], ("Rechazada", "Falta la firma de la empresa"))
        self.assertEqual(legado[7:9], (None, None))  # el original no se reemplaza

    async def test_approval_stamps_a_new_signed_document_and_keeps_the_original(self):  # C06-AC4
        cursor = ScriptCursor(guion())
        runtime = runtime_con(cursor)
        resultado = await revisar(runtime, "Aprobada", "Buen trabajo")
        self.assertEqual((resultado["estado"], resultado["firma"]), ("Aprobada", "celda"))
        runtime.services.leer_documento.assert_awaited_once_with("a" * 32 + ".pdf", None)
        runtime.services.guardar_documento.assert_awaited_once_with(b"%PDF-firmado")
        claves = cursor.claves
        self.assertLess(claves.index("dual.revisiones.insert_firmado"), claves.index("dual.revisiones.insert_revision"))
        legado = next(c[1] for c in cursor.calls if c[0] == "dual.revisiones.actualizar_reporte")
        self.assertEqual(legado[7:9], (None, None))  # el puntero heredado ya no apunta a ninguna ruta (C10A)
        runtime.services.eliminar_documento.assert_not_awaited()

    async def test_approval_without_a_registered_signature_is_409_and_stores_nothing(self):  # AC7
        cursor = ScriptCursor(guion(**{"dual.tutor.get_signature": []}))
        runtime = runtime_con(cursor)
        with self.assertRaises(ApplicationError) as caught:
            await revisar(runtime)
        self.assertEqual(caught.exception.status_code, 409)
        runtime.services.guardar_documento.assert_not_awaited()
        self.assertNotIn("dual.revisiones.insert_revision", cursor.claves)

    async def test_corrections_keep_previous_and_new_values_and_never_move_the_week(self):  # AC1 / AC2, DP-02
        cursor = ScriptCursor(guion())
        runtime = runtime_con(cursor)
        await revisar(runtime, "Aprobada", None, nota=9, inicio=date(2026, 10, 13))
        correcciones = [c[1][1:] for c in cursor.calls if c[0] == "dual.revisiones.insert_correccion"]
        self.assertCountEqual(correcciones, [("fecha_inicio", "2026-10-12", "2026-10-13"), ("nota", "8", "9")])
        revision = next(c[1] for c in cursor.calls if c[0] == "dual.revisiones.insert_revision")
        self.assertEqual(revision[4:7], (date(2026, 10, 13), date(2026, 10, 16), 9))
        # Ninguna consulta toca obligaciones ni períodos: la revisión no puede moverlos.
        for clave, _ in cursor.calls:
            self.assertTrue(clave.startswith(("dual.revisiones.", "dual.tutor.", "dual.entregas.lock")), clave)

    async def test_invalid_corrections_are_422_before_any_file_is_stored(self):  # AC1
        for nota, inicio in ((0, None), (11, None), (None, date(2026, 10, 20))):
            runtime = runtime_con(ScriptCursor(guion()))
            with self.assertRaises(ApplicationError) as caught:
                await revisar(runtime, nota=nota, inicio=inicio)
            self.assertEqual(caught.exception.status_code, 422)
            runtime.services.guardar_documento.assert_not_awaited()

    async def test_review_of_an_obsolete_version_is_409(self):  # AC3
        cursor = ScriptCursor(guion(**{"dual.revisiones.reporte": [reporte(ultima=2)],
                                       "dual.revisiones.reporte_bloqueado": [reporte(ultima=2)]}))
        runtime = runtime_con(cursor)
        with self.assertRaises(ApplicationError) as caught:
            await revisar(runtime, "Rechazada", "x", numero=1)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertNotIn("dual.revisiones.insert_revision", cursor.claves)
        runtime.services.guardar_documento.assert_not_awaited()

    async def test_already_decided_version_is_409_and_identical_retry_is_stable(self):  # AC6
        previa = {"tutor_id": TUTOR["id"], "decision": "Rechazada", "observacion": "Falta firma",
                  "rev_inicio": date(2026, 10, 12), "rev_fin": date(2026, 10, 16), "rev_nota": 8}
        ya = guion(**{"dual.revisiones.version": [version(revisada=previa), version(revisada=previa)]})
        cursor = ScriptCursor(ya)
        resultado = await revisar(runtime_con(cursor), "Rechazada", "Falta firma")
        self.assertTrue(resultado["repetido"])
        self.assertNotIn("dual.revisiones.insert_revision", cursor.claves)

        distinta = ScriptCursor(guion(**{"dual.revisiones.version": [version(revisada=previa)] * 2}))
        with self.assertRaises(ApplicationError) as caught:
            await revisar(runtime_con(distinta), "Aprobada")
        self.assertEqual(caught.exception.status_code, 409)

    async def test_review_does_not_depend_on_the_period_being_open(self):  # RN-18/RN-19
        cursor = ScriptCursor(guion())
        await revisar(runtime_con(cursor), "Rechazada", "Observación")
        self.assertFalse(any("ciclos" in str(c[0]) or "periodo" in str(c[0]) for c in cursor.calls))

    async def test_database_failure_discards_only_the_new_signed_file(self):  # AC5
        runtime = runtime_con(ScriptCursor(guion()), falla=RuntimeError("fallo al confirmar"))
        with self.assertRaises(RuntimeError):
            await revisar(runtime)
        runtime.services.eliminar_documento.assert_awaited_once_with("b" * 32 + ".pdf")
        runtime.services.leer_documento.assert_awaited_once()  # el original solo se leyó

    async def test_stamping_failure_stores_nothing_and_leaves_the_report_pending(self):  # AC5
        runtime = runtime_con(ScriptCursor(guion()))
        runtime.services.estampar_firma = lambda *a: (_ for _ in ()).throw(ApplicationError(400, "firma ilegible"))
        with self.assertRaises(ApplicationError):
            await revisar(runtime)
        runtime.services.guardar_documento.assert_not_awaited()

    async def test_unreadable_signed_output_is_not_stored(self):  # AC5
        runtime = runtime_con(ScriptCursor(guion()))
        runtime.services.inspeccionar_pdf = lambda c: (_ for _ in ()).throw(ApplicationError(422, "dañado"))
        with self.assertRaises(ApplicationError) as caught:
            await revisar(runtime)
        self.assertEqual(caught.exception.status_code, 500)
        runtime.services.guardar_documento.assert_not_awaited()

    async def test_lock_is_the_delivery_lock_of_the_same_obligation(self):  # AC6
        cursor = ScriptCursor(guion())
        await revisar(runtime_con(cursor), "Rechazada", "Observación")
        bloqueo = next(c for c in cursor.calls if c[0] == "dual.entregas.lock")
        self.assertEqual(bloqueo[1], (str(OBLIGACION_ID),))
        claves = cursor.claves
        self.assertLess(claves.index("dual.entregas.lock"), claves.index("dual.revisiones.reporte_bloqueado"))


class SqlContractTests(unittest.TestCase):
    def test_migration_006_makes_reviews_immutable_and_requires_rejection_notes(self):
        sql = (ROOT / "database/migrations/006_revisiones.sql").read_text(encoding="utf-8")
        for fragmento in ("revisiones_inmutables", "BEFORE UPDATE OR DELETE", "revisiones_rechazo_con_observacion",
                          "revisiones_firmado_solo_si_aprobada", "reporte_correcciones_unica",
                          "version_id uuid NOT NULL UNIQUE", "documentos_rol_valido"):
            self.assertIn(fragmento, sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_legacy_patch_review_route_and_drive_dependency_are_gone(self):
        router = (ROOT / "ute-api-backend/app/presentation/api/routers/dual/coordinador_dual.py").read_text(encoding="utf-8")
        self.assertNotIn("@router.patch(\"/reportes", router)
        for ruta in ("use_cases/dual/revisiones.py", "use_cases/dual/coordinador_dual.py"):
            texto = (ROOT / "ute-api-backend/app/application" / ruta).read_text(encoding="utf-8")
            self.assertNotIn("upload_file_async", texto)
            self.assertNotIn("revisar_reporte", texto)

    def test_tutor_queries_expose_the_current_version(self):
        from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES
        self.assertIn("AS version", " ".join(QUERIES["dual.coordinador_dual.q000"]["sql"].split()))
        self.assertNotIn("dual.coordinador_dual.update_report", QUERIES)


if __name__ == "__main__":
    unittest.main()
