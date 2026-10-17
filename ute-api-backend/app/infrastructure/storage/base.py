"""Contrato de almacenamiento privado de archivos (C10A, ADR-03).

Los casos de uso solo ven este contrato: guardar, leer, eliminar de forma definitiva, comprobar la existencia
y listar sobre claves que genera el servidor. Ninguna ruta, ningún identificador de Drive y ninguna URL
salen del adaptador. Los adaptadores son síncronos; los llamadores los ejecutan en un hilo.
"""
from __future__ import annotations

import re

ESPACIOS = ("documentos", "plantillas", "respaldos")
_NOMBRE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class ArchivoNoEncontrado(Exception):
    """La clave no existe en el espacio indicado."""


class ArchivoYaExiste(Exception):
    """Las claves son de solo escritura: nunca se sobrescribe un archivo."""


class AlmacenamientoNoDisponible(Exception):
    """El almacenamiento no puede atender la operación (red, cuota, credenciales, carpeta).

    `codigo` es un texto corto para registros y para `/health`: `sin_configurar`, `token_caducado`,
    `cuota`, `carpeta`, `red` o `no_disponible`. Nunca contiene secretos ni identificadores de Drive.
    """

    def __init__(self, motivo: str, codigo: str = "no_disponible"):
        super().__init__(motivo)
        self.motivo, self.codigo = motivo, codigo


def validar(espacio: str, clave: str) -> None:
    if espacio not in ESPACIOS:
        raise ValueError(f"Espacio de almacenamiento no válido: {espacio}")
    if not _NOMBRE.fullmatch(clave or ""):
        raise ValueError("Clave de almacenamiento no válida")


class Almacenamiento:
    """Interfaz que implementan los adaptadores (`drive`, `local` solo para pruebas y `memoria`)."""

    nombre = "abstracto"

    def guardar(self, espacio: str, clave: str, contenido: bytes) -> dict:  # {"tamano", "sha256"}
        raise NotImplementedError

    def leer(self, espacio: str, clave: str) -> bytes:
        raise NotImplementedError

    def eliminar(self, espacio: str, clave: str) -> bool:
        """Elimina de forma definitiva; devuelve False si la clave ya no existía (idempotente)."""
        raise NotImplementedError

    def existe(self, espacio: str, clave: str) -> bool:
        raise NotImplementedError

    def listar(self, espacio: str) -> list[dict]:  # [{"clave", "creado"}] con `creado` en segundos epoch
        raise NotImplementedError

    def estado(self) -> dict:  # {"tipo", "estado"} sin secretos
        raise NotImplementedError
