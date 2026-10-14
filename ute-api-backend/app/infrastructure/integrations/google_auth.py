# Google Auth compartido (Drive), soporta modo local y produccion
# (Render)

import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from loguru import logger

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]


def _load_credentials_from_env() -> Credentials | None:
    # Intenta cargar credenciales desde variables de entorno (modo producción).
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if not token_json:
        return None

    try:
        token_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # persistir el token refrescado como env var no es posible en
            # runtime;
            # el refresh_token sigue siendo válido así que funcionará la
            # próxima vez.
            return creds
    except Exception as e:
        logger.warning(f"No se pudieron cargar credenciales desde env: {e}")

    return None


def _load_credentials_from_file(credentials_path: str) -> Credentials:
    # Modo desarrollo: carga desde archivo o ejecuta OAuth flow interactivo.
    creds_dir = os.path.dirname(credentials_path)
    token_path = os.path.join(creds_dir, "token.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


def get_google_credentials(credentials_path: str) -> Credentials:
    # Obtiene credenciales de Google. Prueba env vars primero, luego archivos
    # locales.
    creds = _load_credentials_from_env()
    if creds:
        logger.debug(
            "Google Auth: usando credenciales desde GOOGLE_TOKEN_JSON"
        )
        return creds

    logger.debug("Google Auth: usando archivos locales (modo desarrollo)")
    return _load_credentials_from_file(credentials_path)
