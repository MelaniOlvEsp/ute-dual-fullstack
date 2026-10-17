import hashlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError

from app.infrastructure.storage import registro
from app.infrastructure.storage.base import (
    AlmacenamientoNoDisponible, ArchivoNoEncontrado, ArchivoYaExiste, validar)
from app.infrastructure.storage.drive import DriveAlmacenamiento
from app.infrastructure.storage.local import LocalAlmacenamiento
from app.infrastructure.storage.memoria import MemoriaAlmacenamiento

CLAVE = "a" * 32 + ".pdf"


def error_http(estado, razon=""):
    contenido = json.dumps({"error": {"errors": [{"reason": razon}]}}).encode()
    return HttpError(MagicMock(status=estado, reason=razon), contenido)


class ContratoComun:
    """Pruebas que debe pasar cualquier adaptador del contrato."""

    def adaptador(self):
        raise NotImplementedError

    def test_save_read_exists_and_permanent_delete(self):
        a = self.adaptador()
        guardado = a.guardar("documentos", CLAVE, b"%PDF-contenido")
        self.assertEqual(guardado, {"tamano": 14, "sha256": hashlib.sha256(b"%PDF-contenido").hexdigest()})
        self.assertTrue(a.existe("documentos", CLAVE))
        self.assertEqual(a.leer("documentos", CLAVE), b"%PDF-contenido")
        self.assertFalse(a.existe("plantillas", CLAVE), "Los espacios son independientes")
        self.assertTrue(a.eliminar("documentos", CLAVE))
        self.assertFalse(a.eliminar("documentos", CLAVE), "Eliminar es idempotente")
        self.assertFalse(a.existe("documentos", CLAVE))
        with self.assertRaises(ArchivoNoEncontrado):
            a.leer("documentos", CLAVE)

    def test_keys_are_write_once_and_names_are_validated(self):
        a = self.adaptador()
        a.guardar("documentos", CLAVE, b"uno")
        with self.assertRaises(ArchivoYaExiste):
            a.guardar("documentos", CLAVE, b"otro")
        self.assertEqual(a.leer("documentos", CLAVE), b"uno")
        for espacio, clave in (("otro", CLAVE), ("documentos", "../x.pdf"), ("documentos", "a/b.pdf"), ("documentos", "")):
            with self.assertRaises(ValueError):
                validar(espacio, clave)
            with self.assertRaises(ValueError):
                a.leer(espacio, clave)

    def test_listing_returns_keys_with_creation_time(self):
        a = self.adaptador()
        a.guardar("documentos", CLAVE, b"x")
        a.guardar("documentos", "b" * 32 + ".pdf", b"y")
        self.assertEqual({f["clave"] for f in a.listar("documentos")}, {CLAVE, "b" * 32 + ".pdf"})
        self.assertTrue(all(isinstance(f["creado"], float) for f in a.listar("documentos")))
        self.assertEqual(a.listar("plantillas"), [])


class MemoriaTests(ContratoComun, unittest.TestCase):
    def adaptador(self):
        return MemoriaAlmacenamiento()


class LocalTests(ContratoComun, unittest.TestCase):
    def adaptador(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return LocalAlmacenamiento(self.tmp.name)


class SimuladorDrive:
    """Servicio de Drive en memoria con la forma que usa el adaptador (SIMULADA)."""

    def __init__(self, fallos=None):
        self.archivos, self.carpetas, self.llamadas, self.fallos = {}, {}, [], list(fallos or [])
        self.siguiente = 0

    def _id(self):
        self.siguiente += 1
        return f"id{self.siguiente}"

    def files(self):
        return self

    def _solicitud(self, operacion, funcion):
        simulador = self

        class Solicitud:
            def execute(self_):
                simulador.llamadas.append(operacion)
                if simulador.fallos:
                    fallo = simulador.fallos.pop(0)
                    if fallo:
                        raise fallo
                return funcion()

            def next_chunk(self_):
                return None, self_.execute()

        return Solicitud()

    def list(self, q="", fields="", pageSize=None, pageToken=None, orderBy=None):
        def listar():
            nombre = q.split("name = '")[1].split("'")[0] if "name = '" in q else None
            padre = q.split("'")[-2] if "in parents" in q else None
            if "mimeType" in q:
                if getattr(self, "barrera", None) is not None:
                    try:  # dos hilos que llegan juntos sin encontrar la carpeta (carrera real)
                        self.barrera.wait()
                    except threading.BrokenBarrierError:
                        pass
                hallados = sorted((i for i, a in self.carpetas.items() if a["name"] == nombre), key=lambda i: self.carpetas[i]["orden"])
                return {"files": [{"id": i} for i in hallados]}
            if nombre:
                hallados = sorted((i for i, a in self.archivos.items() if a["name"] == nombre and a["padre"] == padre),
                                  key=lambda i: self.archivos[i]["orden"])
                return {"files": [dict(self.archivos[i], id=i) for i in hallados]}
            return {"files": [{"name": a["name"], "createdTime": "2026-10-17T12:00:00Z"}
                              for a in self.archivos.values() if a["padre"] == padre]}
        return self._solicitud("list", listar)

    def create(self, body=None, media_body=None, fields=None):
        def crear():
            identificador = self._id()
            if body.get("mimeType") == "application/vnd.google-apps.folder":
                self.carpetas[identificador] = {"name": body["name"], "orden": self.siguiente}
                return {"id": identificador}
            contenido = media_body._fd.getvalue()
            self.archivos[identificador] = {
                "name": body["name"], "padre": body["parents"][0], "datos": contenido, "orden": self.siguiente,
                "appProperties": body.get("appProperties", {}), "size": str(len(contenido)),
                "md5Checksum": hashlib.md5(contenido).hexdigest() if not getattr(self, "md5_malo", False) else "0" * 32}
            return {"id": identificador, "size": self.archivos[identificador]["size"],
                    "md5Checksum": self.archivos[identificador]["md5Checksum"]}
        return self._solicitud("create", crear)

    def delete(self, fileId=None):
        def borrar():
            self.archivos.pop(fileId, None)
            self.carpetas.pop(fileId, None)
        return self._solicitud("delete", borrar)

    def get(self, fileId=None, fields=None):
        return self._solicitud("get", lambda: {"id": fileId, "trashed": False})

    def get_media(self, fileId=None):
        return SimpleNamespaceMedia(self.archivos[fileId]["datos"])


class SimpleNamespaceMedia:
    def __init__(self, datos):
        self.datos = datos


class DriveTests(ContratoComun, unittest.TestCase):
    def adaptador(self, fallos=None):
        self.simulador = SimuladorDrive(fallos)
        self.simulador.carpetas["raiz"] = {"name": "raiz", "orden": 0}
        self.esperas = []
        return DriveAlmacenamiento(lambda: self.simulador, "raiz", dormir=self.esperas.append, aleatorio=lambda: 0.0)

    def setUp(self):
        # La descarga usa MediaIoBaseDownload: se sustituye por una lectura directa del simulador.
        import app.infrastructure.storage.drive as modulo
        self._original = modulo.MediaIoBaseDownload

        class Descarga:
            def __init__(self, destino, solicitud, chunksize=None):
                self.destino, self.solicitud = destino, solicitud

            def next_chunk(self):
                self.destino.write(self.solicitud.datos)
                return None, True

        modulo.MediaIoBaseDownload = Descarga
        self.addCleanup(lambda: setattr(modulo, "MediaIoBaseDownload", self._original))

    def test_the_file_is_named_with_the_key_and_carries_the_hash_as_a_property(self):
        a = self.adaptador()
        a.guardar("documentos", CLAVE, b"%PDF-x")
        (archivo,) = self.simulador.archivos.values()
        self.assertEqual(archivo["name"], CLAVE)
        self.assertEqual(archivo["appProperties"]["sha256"], hashlib.sha256(b"%PDF-x").hexdigest())
        self.assertEqual({c["name"] for c in self.simulador.carpetas.values()}, {"raiz", "documentos"})

    def test_a_save_whose_md5_does_not_match_is_deleted_and_reported(self):
        a = self.adaptador()
        self.simulador.md5_malo = True
        with self.assertRaises(AlmacenamientoNoDisponible):
            a.guardar("documentos", CLAVE, b"%PDF-x")
        self.assertEqual(self.simulador.archivos, {}, "Nada queda guardado")

    def test_a_retry_after_a_timeout_does_not_duplicate_or_fail(self):
        a = self.adaptador()
        a.guardar("documentos", CLAVE, b"igual")
        self.assertEqual(a.guardar("documentos", CLAVE, b"igual")["tamano"], 5)
        self.assertEqual(len(self.simulador.archivos), 1)

    def test_rate_limits_are_retried_with_growing_waits_and_a_limit(self):
        a = self.adaptador([error_http(403, "userRateLimitExceeded"), error_http(429), error_http(503), None, None])
        a.existe("documentos", CLAVE)
        self.assertEqual(self.esperas, [1.0, 2.0, 4.0])
        a = self.adaptador([error_http(429)] * 10)
        with self.assertRaises(AlmacenamientoNoDisponible) as caught:
            a.existe("documentos", CLAVE)
        self.assertEqual(caught.exception.codigo, "red")
        self.assertEqual(len(self.esperas), 4, "Cinco intentos y cuatro esperas, no más")

    def test_permanent_errors_are_not_retried_and_have_their_own_code(self):
        for estado, razon, codigo in ((401, "", "token_caducado"), (403, "storageQuotaExceeded", "cuota"), (404, "", "carpeta"),
                                      (400, "badRequest", "no_disponible")):
            a = self.adaptador([error_http(estado, razon)])
            with self.assertRaises(AlmacenamientoNoDisponible) as caught:
                a.existe("documentos", CLAVE)
            self.assertEqual((caught.exception.codigo, self.esperas), (codigo, []), (estado, razon))

    def test_a_revoked_authorization_is_reported_as_expired_token(self):
        class RefreshError(Exception):
            pass

        a = self.adaptador([RefreshError("invalid_grant")])
        with self.assertRaises(AlmacenamientoNoDisponible) as caught:
            a.existe("documentos", CLAVE)
        self.assertEqual(caught.exception.codigo, "token_caducado")

    def test_network_failures_are_retried_and_then_reported(self):
        a = self.adaptador([ConnectionError("x"), None, None])
        a.existe("documentos", CLAVE)
        self.assertEqual(self.esperas, [1.0])
        a = self.adaptador([TimeoutError("x")] * 10)
        with self.assertRaises(AlmacenamientoNoDisponible) as caught:
            a.existe("documentos", CLAVE)
        self.assertEqual(caught.exception.codigo, "red")

    def test_without_a_root_folder_the_adapter_reports_not_configured_and_health_does_not_leak(self):
        a = DriveAlmacenamiento(lambda: SimuladorDrive(), "")
        with self.assertRaises(AlmacenamientoNoDisponible) as caught:
            a.guardar("documentos", CLAVE, b"x")
        self.assertEqual(caught.exception.codigo, "sin_configurar")
        self.assertEqual(a.estado(), {"tipo": "drive", "estado": "sin_configurar"})
        self.assertEqual(self.adaptador().estado(), {"tipo": "drive", "estado": "ok"})

    def test_delete_uses_the_permanent_delete_call(self):
        a = self.adaptador()
        a.guardar("documentos", CLAVE, b"x")
        a.eliminar("documentos", CLAVE)
        self.assertIn("delete", self.simulador.llamadas)
        self.assertEqual(self.simulador.archivos, {})

    # --- revisión C10A (M1 y M2) ---------------------------------------------------------------
    def test_two_threads_first_using_a_space_create_one_subfolder_not_two(self):  # M1
        a = self.adaptador()
        self.simulador.barrera = threading.Barrier(2, timeout=0.5)
        identificadores, errores = [], []

        def usar():
            try:
                identificadores.append(a._carpeta("documentos"))
            except Exception as error:  # pragma: no cover - solo para diagnosticar
                errores.append(error)

        hilos = [threading.Thread(target=usar) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(5)
        self.assertEqual(errores, [])
        self.assertEqual(len(set(identificadores)), 1, "Ambos hilos usan la misma carpeta")
        self.assertEqual(sum(1 for c in self.simulador.carpetas.values() if c["name"] == "documentos"), 1)

    def test_with_duplicate_folders_the_oldest_is_always_used_and_a_late_duplicate_is_discarded(self):  # M1
        a = self.adaptador()
        self.simulador.carpetas["vieja"] = {"name": "documentos", "orden": 1}
        self.simulador.carpetas["nueva"] = {"name": "documentos", "orden": 2}
        self.assertEqual(a._carpeta("documentos"), "vieja")
        # Otro proceso crea la carpeta entre nuestra búsqueda y nuestra creación: se adopta la más antigua.
        b = self.adaptador()
        original = self.simulador.create

        def crear_con_competencia(body=None, media_body=None, fields=None):
            if body and body.get("name") == "plantillas":
                self.simulador.carpetas["ajena"] = {"name": "plantillas", "orden": -1}
            return original(body=body, media_body=media_body, fields=fields)

        self.simulador.create = crear_con_competencia
        self.assertEqual(b._carpeta("plantillas"), "ajena")
        self.assertEqual([c for c in self.simulador.carpetas.values() if c["name"] == "plantillas"], [{"name": "plantillas", "orden": -1}],
                         "La carpeta propia, vacía, se descarta")

    def test_a_retry_after_a_lost_response_does_not_duplicate_the_upload(self):  # M2
        a = self.adaptador()
        original = self.simulador.create
        llamadas = {"n": 0}

        def crear_y_perder_la_respuesta(body=None, media_body=None, fields=None):
            solicitud = original(body=body, media_body=media_body, fields=fields)
            ejecutar = solicitud.execute

            def execute():
                resultado = ejecutar()
                llamadas["n"] += 1
                if llamadas["n"] == 1:
                    raise error_http(503)  # Drive creó el archivo, pero la respuesta no llegó
                return resultado

            solicitud.execute = execute
            return solicitud

        self.simulador.create = crear_y_perder_la_respuesta
        a._carpeta("documentos")
        guardado = a.guardar("documentos", CLAVE, b"%PDF-unico")
        self.assertEqual(guardado["tamano"], 10)
        self.assertEqual(len(self.simulador.archivos), 1, "El reintento reutilizó el archivo ya creado")
        self.assertEqual(self.esperas, [1.0])

    def test_a_retry_finding_a_different_file_under_the_same_key_is_never_overwritten(self):  # M2
        a = self.adaptador()
        a._carpeta("documentos")
        carpeta = next(i for i, c in self.simulador.carpetas.items() if c["name"] == "documentos")
        self.simulador.archivos["x"] = {"name": CLAVE, "padre": carpeta, "datos": b"otro", "orden": 99,
                                        "appProperties": {"sha256": "0" * 64}, "size": "4", "md5Checksum": "0" * 32}
        with self.assertRaises(ArchivoYaExiste):
            a.guardar("documentos", CLAVE, b"%PDF-distinto")

    def test_delete_leaves_no_copy_even_if_a_duplicate_exists(self):  # M2
        a = self.adaptador()
        a._carpeta("documentos")
        carpeta = next(i for i, c in self.simulador.carpetas.items() if c["name"] == "documentos")
        for n in (1, 2):
            self.simulador.archivos[f"d{n}"] = {"name": CLAVE, "padre": carpeta, "datos": b"x", "orden": n,
                                                "appProperties": {}, "size": "1", "md5Checksum": ""}
        self.assertTrue(a.eliminar("documentos", CLAVE))
        self.assertEqual(self.simulador.archivos, {})
        self.assertFalse(a.existe("documentos", CLAVE))

class ClienteRealDeGoogleTests(unittest.TestCase):
    """El adaptador arma peticiones válidas con el cliente real de Google sobre un transporte simulado (SIMULADA)."""

    def servicio(self, respuestas):
        from googleapiclient.discovery import build
        from googleapiclient.http import HttpMockSequence
        http = HttpMockSequence([({"status": "200"}, json.dumps(r)) for r in respuestas])
        return build("drive", "v3", http=http, static_discovery=True), http

    def test_save_read_and_delete_build_valid_requests_and_verify_the_checksum(self):
        contenido = b"%PDF-real"
        md5 = hashlib.md5(contenido).hexdigest()
        servicio, _ = self.servicio([
            {"files": [{"id": "carpeta-docs"}]},                      # subcarpeta documentos
            {"files": []},                                            # no existe el archivo
            {"files": []},                                            # comprobación previa a la subida
            {"id": "f1", "size": str(len(contenido)), "md5Checksum": md5},  # subida
            {"files": [{"id": "f1", "size": "9", "md5Checksum": md5}]},      # búsqueda previa a eliminar
            {},                                                       # files.delete
        ])
        a = DriveAlmacenamiento(lambda: servicio, "raiz")
        self.assertEqual(a.guardar("documentos", CLAVE, contenido)["tamano"], 9)
        self.assertTrue(a.eliminar("documentos", CLAVE))

    def test_a_wrong_checksum_from_google_is_rejected_after_deleting_the_upload(self):
        servicio, _ = self.servicio([
            {"files": [{"id": "carpeta-docs"}]}, {"files": []}, {"files": []},
            {"id": "f1", "size": "9", "md5Checksum": "0" * 32},
            {},
        ])
        a = DriveAlmacenamiento(lambda: servicio, "raiz")
        with self.assertRaises(AlmacenamientoNoDisponible):
            a.guardar("documentos", CLAVE, b"%PDF-real")

class RegistroTests(unittest.TestCase):
    def test_the_current_adapter_can_be_replaced_and_restored(self):
        original = registro.get_storage()
        memoria = MemoriaAlmacenamiento()
        with registro.usar(memoria):
            self.assertIs(registro.get_storage(), memoria)
        self.assertIs(registro.get_storage(), original)

    def test_health_status_is_cached_and_never_raises(self):
        class Roto(MemoriaAlmacenamiento):
            def estado(self):
                raise RuntimeError("secreto")

        with registro.usar(Roto()):
            estado = registro.estado_cacheado()
        self.assertEqual(estado["estado"], "no_disponible")
        self.assertNotIn("secreto", str(estado))


if __name__ == "__main__":
    unittest.main()