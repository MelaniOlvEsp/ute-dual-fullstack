"""Adaptador de carpeta local: SOLO para desarrollo y regresión (`ALMACENAMIENTO=local`).

El piloto no guarda archivos de forma local (decisión del 2026-10-17): este adaptador existe para poder
ejecutar los smokes y las pruebas sin una cuenta de Drive y nunca es el predeterminado.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.infrastructure.storage.base import Almacenamiento, ArchivoNoEncontrado, ArchivoYaExiste, validar


class LocalAlmacenamiento(Almacenamiento):
    nombre = "local"

    def __init__(self, raiz):
        self._raiz = Path(raiz)

    def _ruta(self, espacio, clave) -> Path:
        validar(espacio, clave)
        return self._raiz / espacio / clave[:2] / clave

    def guardar(self, espacio, clave, contenido):
        ruta = self._ruta(espacio, clave)
        if ruta.exists():
            raise ArchivoYaExiste(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_name(ruta.name + ".part")
        with open(temporal, "xb") as destino:
            destino.write(contenido)
            destino.flush()
            os.fsync(destino.fileno())
        os.replace(temporal, ruta)
        return {"tamano": len(contenido), "sha256": hashlib.sha256(contenido).hexdigest()}

    def leer(self, espacio, clave):
        ruta = self._ruta(espacio, clave)
        if not ruta.is_file():
            raise ArchivoNoEncontrado(clave)
        return ruta.read_bytes()

    def eliminar(self, espacio, clave):
        ruta = self._ruta(espacio, clave)
        existia = ruta.is_file()
        ruta.unlink(missing_ok=True)
        return existia

    def existe(self, espacio, clave):
        return self._ruta(espacio, clave).is_file()

    def listar(self, espacio):
        base = self._raiz / espacio
        if not base.is_dir():
            return []
        return [{"clave": r.name, "creado": r.stat().st_mtime} for r in base.rglob("*") if r.is_file()]

    def estado(self):
        return {"tipo": self.nombre, "estado": "ok"}
