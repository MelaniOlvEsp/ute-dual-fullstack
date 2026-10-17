"""Adaptador en memoria: solo para pruebas unitarias; no persiste nada."""
from __future__ import annotations

import hashlib
import threading
import time

from app.infrastructure.storage.base import Almacenamiento, ArchivoNoEncontrado, ArchivoYaExiste, validar


class MemoriaAlmacenamiento(Almacenamiento):
    nombre = "memoria"

    def __init__(self):
        self._datos: dict[tuple[str, str], tuple[bytes, float]] = {}
        self._cerrojo = threading.Lock()

    def guardar(self, espacio, clave, contenido):
        validar(espacio, clave)
        with self._cerrojo:
            if (espacio, clave) in self._datos:
                raise ArchivoYaExiste(clave)
            self._datos[(espacio, clave)] = (bytes(contenido), time.time())
        return {"tamano": len(contenido), "sha256": hashlib.sha256(contenido).hexdigest()}

    def leer(self, espacio, clave):
        validar(espacio, clave)
        try:
            return self._datos[(espacio, clave)][0]
        except KeyError as exc:
            raise ArchivoNoEncontrado(clave) from exc

    def eliminar(self, espacio, clave):
        validar(espacio, clave)
        with self._cerrojo:
            return self._datos.pop((espacio, clave), None) is not None

    def existe(self, espacio, clave):
        validar(espacio, clave)
        return (espacio, clave) in self._datos

    def listar(self, espacio):
        return [{"clave": c, "creado": t} for (e, c), (_, t) in list(self._datos.items()) if e == espacio]

    def estado(self):
        return {"tipo": self.nombre, "estado": "ok"}
