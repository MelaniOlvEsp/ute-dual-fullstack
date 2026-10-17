"""Autoriza Drive para el piloto (C10A, D1): OAuth de usuario con el alcance `drive.file`.

Requisitos (una sola vez): en Google Cloud crea un cliente OAuth de tipo «Aplicación de escritorio», descarga
su JSON y guárdalo como `.secretos/client_secret.json` (carpeta ignorada por git). Después ejecuta:

    docker compose --profile drive run --rm --service-ports drive-autorizar

Abre en el navegador la dirección que se imprime, acepta con la cuenta de pruebas y el script guarda el token
en `.secretos/drive_token.json` y crea la carpeta raíz «Formación Dual (piloto)» en esa cuenta, anotando su
identificador en `.secretos/drive_config.json`. No imprime ni registra ningún secreto. Con la aplicación en
modo de prueba el token caduca a los 7 días: repite este comando para volver a autorizar.
"""
import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
NOMBRE_CARPETA = "Formación Dual (piloto)"


def main() -> int:
    cliente = Path(os.environ.get("DRIVE_CLIENTE_FILE", "/secretos/client_secret.json"))
    token = Path(os.environ.get("DRIVE_TOKEN_FILE", "/secretos/drive_token.json"))
    if not cliente.is_file():
        print(f"Falta {cliente.name}: descarga el JSON del cliente OAuth (aplicación de escritorio) en .secretos/")
        return 1
    flujo = InstalledAppFlow.from_client_secrets_file(str(cliente), SCOPES)
    credenciales = flujo.run_local_server(host="localhost", bind_addr="0.0.0.0", port=8085, open_browser=False,
                                          authorization_prompt_message="Abre esta dirección en el navegador:\n{url}\n")
    token.write_text(credenciales.to_json(), encoding="utf-8")
    drive = build("drive", "v3", credentials=credenciales, cache_discovery=False)
    config = token.with_name("drive_config.json")
    carpeta_id = ""
    if config.is_file():
        try:
            carpeta_id = json.loads(config.read_text(encoding="utf-8")).get("carpeta_id", "")
        except ValueError:
            carpeta_id = ""
    if carpeta_id:
        try:
            if not drive.files().get(fileId=carpeta_id, fields="id,trashed").execute().get("trashed"):
                print("Autorización renovada; se conserva la carpeta raíz existente.")
                return 0
        except Exception:
            carpeta_id = ""
    carpeta = drive.files().create(body={"name": NOMBRE_CARPETA, "mimeType": "application/vnd.google-apps.folder"},
                                   fields="id").execute()
    config.write_text(json.dumps({"carpeta_id": carpeta["id"]}), encoding="utf-8")
    print("Drive autorizado y carpeta raíz creada. Reinicia la API para que lo use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())