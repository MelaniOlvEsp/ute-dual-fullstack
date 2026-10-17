"""Adaptador de Drive del contrato de almacenamiento (C10A).

Una carpeta raíz privada (creada por la propia aplicación con el alcance `drive.file`) con una subcarpeta por
espacio y un archivo de Drive por clave, nombrado con la clave y con el tipo y el SHA-256 como propiedades de
la aplicación. La subida comprueba tamaño y MD5 que devuelve Drive; la eliminación es definitiva (no va a la
papelera) para que la depuración de C08B elimine de verdad; los 403 de cuota, 429 y 5xx se reintentan con
espera exponencial y variación aleatoria. Nunca devuelve identificadores de Drive ni URL.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import socket
import threading
import time
from datetime import datetime

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from loguru import logger

from app.infrastructure.storage.base import (
    Almacenamiento, AlmacenamientoNoDisponible, ArchivoNoEncontrado, ArchivoYaExiste, validar)

MIME_CARPETA = "application/vnd.google-apps.folder"
UMBRAL_REANUDABLE = 5 * 1024 * 1024
ESTADOS_REINTENTABLES = {429, 500, 502, 503, 504}
RAZONES_DE_TASA = {"rateLimitExceeded", "userRateLimitExceeded", "backendError", "internalError"}
NOMBRES_DE_ESPACIO = {"documentos": "documentos", "plantillas": "plantillas", "respaldos": "respaldos"}


def _razon(error: HttpError) -> str:
    try:
        return json.loads(error.content.decode("utf-8"))["error"]["errors"][0]["reason"]
    except Exception:
        return ""


class DriveAlmacenamiento(Almacenamiento):
    nombre = "drive"

    def __init__(self, fabrica_servicio, carpeta_raiz_id: str, *, max_intentos: int = 5, espera_inicial: float = 1.0,
                 dormir=time.sleep, aleatorio=random.random):
        self._fabrica = fabrica_servicio
        self._raiz = carpeta_raiz_id
        self._max, self._espera0 = max_intentos, espera_inicial
        self._dormir, self._aleatorio = dormir, aleatorio
        self._hilo = threading.local()
        self._carpetas: dict[str, str] = {}
        self._cerrojo = threading.Lock()
        self._cerrojos_espacio: dict[str, threading.Lock] = {}

    # --- infraestructura ------------------------------------------------------------------------
    def _servicio(self):
        servicio = getattr(self._hilo, "servicio", None)
        if servicio is None:
            servicio = self._hilo.servicio = self._fabrica()
        return servicio

    def _ejecutar(self, operacion):
        """Ejecuta una operación con reintentos; todo fallo se traduce a `AlmacenamientoNoDisponible`."""
        espera = self._espera0
        for intento in range(1, self._max + 1):
            try:
                return operacion(self._servicio())
            except AlmacenamientoNoDisponible:
                self._hilo.servicio = None
                raise
            except HttpError as error:
                estado, razon = error.resp.status, _razon(error)
                if estado in ESTADOS_REINTENTABLES or (estado == 403 and razon in RAZONES_DE_TASA):
                    if intento == self._max:
                        raise AlmacenamientoNoDisponible("Drive no respondió a tiempo.", "red") from error
                    logger.warning("Drive respondió {} ({}); reintento {}/{}", estado, razon or "sin razón", intento, self._max)
                    self._dormir(espera + self._aleatorio())
                    espera *= 2
                    continue
                if estado == 401:
                    self._hilo.servicio = None
                    raise AlmacenamientoNoDisponible("Las credenciales de Drive no son válidas.", "token_caducado") from error
                if estado == 403 and razon in {"storageQuotaExceeded", "quotaExceeded"}:
                    raise AlmacenamientoNoDisponible("La cuota de almacenamiento de Drive está llena.", "cuota") from error
                if estado == 404:
                    raise AlmacenamientoNoDisponible("La carpeta de Drive no existe o no es accesible.", "carpeta") from error
                raise AlmacenamientoNoDisponible(f"Drive rechazó la operación ({estado}).", "no_disponible") from error
            except Exception as error:  # errores de red y de autenticación de la biblioteca de Google
                nombre = type(error).__name__
                if nombre == "RefreshError":
                    self._hilo.servicio = None
                    raise AlmacenamientoNoDisponible(
                        "La autorización de Drive caducó o fue revocada; vuelve a autorizar.", "token_caducado") from error
                if isinstance(error, (OSError, socket.timeout, TimeoutError)) or nombre.startswith(("HttpLib2", "ServerNotFound")):
                    if intento == self._max:
                        raise AlmacenamientoNoDisponible("No hay conexión con Drive.", "red") from error
                    self._dormir(espera + self._aleatorio())
                    espera *= 2
                    continue
                raise
        raise AlmacenamientoNoDisponible("Drive no respondió.", "red")

    def _cerrojo_de(self, espacio: str) -> threading.Lock:
        with self._cerrojo:
            return self._cerrojos_espacio.setdefault(espacio, threading.Lock())

    def _carpeta(self, espacio: str) -> str:
        if not self._raiz:
            raise AlmacenamientoNoDisponible("Falta la carpeta de Drive del piloto; ejecuta la autorización.", "sin_configurar")
        with self._cerrojo:
            if espacio in self._carpetas:
                return self._carpetas[espacio]
        nombre = NOMBRES_DE_ESPACIO[espacio]

        def mas_antigua(drive):
            # Drive permite nombres repetidos: siempre se usa la carpeta más antigua, también tras un reinicio
            # o cuando otro proceso la creó al mismo tiempo.
            q = (f"name = '{nombre}' and mimeType = '{MIME_CARPETA}' and '{self._raiz}' in parents and trashed = false")
            return drive.files().list(q=q, fields="files(id)", orderBy="createdTime", pageSize=10).execute().get("files", [])

        def buscar_o_crear(drive):
            hallados = mas_antigua(drive)
            if hallados:
                return hallados[0]["id"]
            propia = drive.files().create(
                body={"name": nombre, "mimeType": MIME_CARPETA, "parents": [self._raiz]}, fields="id").execute()["id"]
            hallados = mas_antigua(drive)  # otro proceso pudo crearla a la vez
            if hallados and hallados[0]["id"] != propia:
                drive.files().delete(fileId=propia).execute()  # la nuestra está vacía: se descarta
                return hallados[0]["id"]
            return propia

        # El candado por espacio evita que dos hilos del proceso creen la misma subcarpeta a la vez.
        with self._cerrojo_de(espacio):
            with self._cerrojo:
                if espacio in self._carpetas:
                    return self._carpetas[espacio]
            identificador = self._ejecutar(buscar_o_crear)
            with self._cerrojo:
                self._carpetas[espacio] = identificador
            return identificador
    def _buscar_todos(self, espacio: str, clave: str) -> list[dict]:
        carpeta = self._carpeta(espacio)
        q = f"name = '{clave}' and '{carpeta}' in parents and trashed = false"
        return self._ejecutar(lambda d: d.files().list(
            q=q, fields="files(id,size,md5Checksum,appProperties)", orderBy="createdTime", pageSize=10).execute()).get("files", [])

    def _buscar(self, espacio: str, clave: str) -> dict | None:
        hallados = self._buscar_todos(espacio, clave)
        if len(hallados) > 1:
            logger.error("Hay más de un archivo de Drive con la misma clave en {}; se usa el más antiguo.", espacio)
        return hallados[0] if hallados else None
    # --- contrato -------------------------------------------------------------------------------
    def guardar(self, espacio, clave, contenido):
        validar(espacio, clave)
        sha = hashlib.sha256(contenido).hexdigest()
        md5 = hashlib.md5(contenido).hexdigest()  # noqa: S324 - Drive devuelve MD5 como suma de comprobación
        existente = self._buscar(espacio, clave)
        if existente:
            if (existente.get("appProperties") or {}).get("sha256") == sha:
                return {"tamano": len(contenido), "sha256": sha}  # reintento tras un tiempo de espera
            raise ArchivoYaExiste(clave)
        carpeta = self._carpeta(espacio)
        tipo = "application/pdf" if clave.endswith(".pdf") else "application/octet-stream"

        def subir(drive):
            # Cada intento (también los reintentos tras un tiempo de espera) comprueba primero si una subida
            # anterior ya creó el archivo: Drive permite nombres repetidos y un reintento ciego lo duplicaría.
            previos = drive.files().list(
                q=f"name = '{clave}' and '{carpeta}' in parents and trashed = false",
                fields="files(id,size,md5Checksum,appProperties)", orderBy="createdTime", pageSize=10).execute().get("files", [])
            if previos:
                if (previos[0].get("appProperties") or {}).get("sha256") == sha:
                    return previos[0]
                raise ArchivoYaExiste(clave)
            medio = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=tipo, resumable=len(contenido) > UMBRAL_REANUDABLE)
            solicitud = drive.files().create(
                body={"name": clave, "parents": [carpeta], "appProperties": {"sha256": sha, "espacio": espacio}},
                media_body=medio, fields="id,size,md5Checksum")
            if len(contenido) > UMBRAL_REANUDABLE:
                respuesta = None
                while respuesta is None:
                    _, respuesta = solicitud.next_chunk()
                return respuesta
            return solicitud.execute()

        creado = self._ejecutar(subir)
        if str(creado.get("size")) != str(len(contenido)) or creado.get("md5Checksum") != md5:
            self._ejecutar(lambda d: d.files().delete(fileId=creado["id"]).execute())
            raise AlmacenamientoNoDisponible("Drive guardó un archivo que no coincide con el original.", "no_disponible")
        return {"tamano": len(contenido), "sha256": sha}

    def leer(self, espacio, clave):
        validar(espacio, clave)
        archivo = self._buscar(espacio, clave)
        if not archivo:
            raise ArchivoNoEncontrado(clave)

        def descargar(drive):
            destino = io.BytesIO()
            descarga = MediaIoBaseDownload(destino, drive.files().get_media(fileId=archivo["id"]), chunksize=5 * 1024 * 1024)
            terminado = False
            while not terminado:
                _, terminado = descarga.next_chunk()
            return destino.getvalue()

        try:
            return self._ejecutar(descargar)
        except AlmacenamientoNoDisponible as error:
            if error.codigo == "carpeta":  # el archivo desapareció entre la búsqueda y la lectura
                raise ArchivoNoEncontrado(clave) from error
            raise

    def eliminar(self, espacio, clave):
        validar(espacio, clave)
        archivos = self._buscar_todos(espacio, clave)
        if not archivos:
            return False
        eliminado = False
        for archivo in archivos:  # normalmente uno; si hubiera duplicados, no puede quedar ninguna copia
            try:
                # `files.delete` elimina de forma definitiva; no usa la papelera.
                self._ejecutar(lambda d, i=archivo["id"]: d.files().delete(fileId=i).execute())
                eliminado = True
            except AlmacenamientoNoDisponible as error:
                if error.codigo != "carpeta":
                    raise
        return eliminado
    def existe(self, espacio, clave):
        validar(espacio, clave)
        return self._buscar(espacio, clave) is not None

    def listar(self, espacio):
        carpeta = self._carpeta(espacio)
        resultado, pagina = [], None
        while True:
            respuesta = self._ejecutar(lambda d: d.files().list(
                q=f"'{carpeta}' in parents and trashed = false", fields="nextPageToken,files(name,createdTime)",
                pageSize=200, pageToken=pagina).execute())
            for f in respuesta.get("files", []):
                creado = datetime.fromisoformat(f["createdTime"].replace("Z", "+00:00")).timestamp()
                resultado.append({"clave": f["name"], "creado": creado})
            pagina = respuesta.get("nextPageToken")
            if not pagina:
                return resultado

    def estado(self):
        try:
            if not self._raiz:
                raise AlmacenamientoNoDisponible("Falta la carpeta de Drive del piloto.", "sin_configurar")
            self._ejecutar(lambda d: d.files().get(fileId=self._raiz, fields="id,trashed").execute())
            return {"tipo": self.nombre, "estado": "ok"}
        except AlmacenamientoNoDisponible as error:
            return {"tipo": self.nombre, "estado": error.codigo}
