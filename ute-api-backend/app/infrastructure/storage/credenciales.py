"""Credenciales de Drive del piloto (C10A, D1): OAuth de usuario con el alcance `drive.file`.

El token de actualización vive en un archivo de configuración local ignorado por git (`.secretos/`), nunca en
el repositorio, en el chat ni en los registros. Una aplicación de Google en modo de prueba caduca el token a
los 7 días: ese caso se informa como `token_caducado` y se resuelve con la orden de autorización.
"""
from __future__ import annotations

import json
from pathlib import Path

from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.infrastructure.config.settings import settings
from app.infrastructure.storage.base import AlmacenamientoNoDisponible

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def carpeta_raiz_id() -> str:
    """Identificador de la carpeta raíz del piloto: variable de entorno o archivo junto al token."""
    if settings.drive_carpeta_id.strip():
        return settings.drive_carpeta_id.strip()
    config = Path(settings.drive_token_file).with_name("drive_config.json")
    if config.is_file():
        try:
            return str(json.loads(config.read_text(encoding="utf-8")).get("carpeta_id", "")).strip()
        except (OSError, ValueError):
            return ""
    return ""


def cargar_credenciales() -> Credentials:
    ruta = Path(settings.drive_token_file)
    if not ruta.is_file():
        raise AlmacenamientoNoDisponible("Drive no está autorizado; ejecuta la autorización.", "sin_configurar")
    try:
        credenciales = Credentials.from_authorized_user_info(json.loads(ruta.read_text(encoding="utf-8")), SCOPES)
    except (OSError, ValueError, KeyError) as error:
        raise AlmacenamientoNoDisponible("El archivo de autorización de Drive no es válido.", "sin_configurar") from error
    if not credenciales.valid:
        try:
            credenciales.refresh(Request())
        except RefreshError as error:
            raise AlmacenamientoNoDisponible(
                "La autorización de Drive caducó o fue revocada; vuelve a autorizar.", "token_caducado") from error
        except TransportError as error:
            raise AlmacenamientoNoDisponible("No hay conexión con Google.", "red") from error
    return credenciales


def fabrica_servicio():
    return build("drive", "v3", credentials=cargar_credenciales(), cache_discovery=False)