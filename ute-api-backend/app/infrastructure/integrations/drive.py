import asyncio
import io

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from loguru import logger

from app.infrastructure.config.settings import settings
from app.infrastructure.integrations.google_auth import get_google_credentials


# Autentica y retorna el servicio Drive v3
def _get_drive_service():
    creds = get_google_credentials(settings.gmail_creds_resolved)
    return build("drive", "v3", credentials=creds)


# Sube un archivo a una carpeta de Drive
def upload_file(
    file_bytes: bytes, filename: str, mimetype: str, folder_id: str
) -> str:
    try:
        service = _get_drive_service()
        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes), mimetype=mimetype, resumable=True
        )
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = file.get("id")
        logger.info(f"Drive upload: {filename} → {file_id}")
        return file_id
    except Exception as e:
        logger.error(f"Error subiendo a Drive ({filename}): {e}")
        raise


# Elimina un archivo de Drive por su ID
def delete_file(file_id: str) -> None:
    try:
        service = _get_drive_service()
        service.files().delete(fileId=file_id).execute()
        logger.info(f"Drive delete: {file_id}")
    except Exception as e:
        logger.warning(f"No se pudo eliminar archivo Drive {file_id}: {e}")


# Crea una carpeta nueva en Drive
def create_folder(name: str, parent_id: str) -> str:
    try:
        service = _get_drive_service()
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = (
            service.files().create(body=file_metadata, fields="id").execute()
        )
        folder_id = folder.get("id")
        logger.info(f"Drive folder created: {name} → {folder_id}")
        return folder_id
    except Exception as e:
        logger.error(f"Error creando carpeta Drive ({name}): {e}")
        raise


# Busca una carpeta por nombre, la crea si no existe
def find_or_create_folder(name: str, parent_id: str) -> str:
    try:
        service = _get_drive_service()
        query = (
            f"'{parent_id}' in parents"
            f" and mimeType = 'application/vnd.google-apps.folder'"
            f" and name = '{name}'"
            f" and trashed = false"
        )
        results = (
            service.files()
            .list(q=query, fields="files(id, name)", pageSize=1)
            .execute()
        )
        existing = results.get("files", [])
        if existing:
            folder_id = existing[0]["id"]
            logger.info(f"Drive folder found: {name} → {folder_id}")
            return folder_id
        return create_folder(name, parent_id)
    except Exception as e:
        logger.error(f"Error buscando/creando carpeta Drive ({name}): {e}")
        raise


# Descarga el contenido de un archivo de Drive
def get_file_bytes(file_id: str) -> bytes:
    try:
        service = _get_drive_service()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        logger.info(f"Drive download: {file_id}")
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error descargando de Drive ({file_id}): {e}")
        raise


# Elimina una carpeta de Drive por su ID
def delete_folder(folder_id: str) -> None:
    try:
        service = _get_drive_service()
        service.files().delete(fileId=folder_id).execute()
        logger.info(f"Drive folder deleted: {folder_id}")
    except Exception as e:
        logger.warning(f"No se pudo eliminar carpeta Drive {folder_id}: {e}")


# Renombra una carpeta de Drive
def rename_folder(folder_id: str, new_name: str) -> str:
    try:
        service = _get_drive_service()
        service.files().update(
            fileId=folder_id,
            body={"name": new_name},
        ).execute()
        logger.info(f"Drive folder renamed: {folder_id} → {new_name}")
        return folder_id
    except Exception as e:
        logger.error(f"Error renombrando carpeta Drive ({folder_id}): {e}")
        raise


# Mueve un archivo a otra carpeta de Drive
def move_file(file_id: str, new_parent_id: str) -> str:
    try:
        service = _get_drive_service()
        file = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))
        service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()
        logger.info(f"Drive file moved: {file_id} → folder {new_parent_id}")
        return file_id
    except Exception as e:
        logger.error(f"Error moviendo archivo Drive ({file_id}): {e}")
        raise


# Lista las subcarpetas dentro de una carpeta
def list_folders(parent_id: str) -> list[dict]:
    try:
        service = _get_drive_service()
        results = (
            service.files()
            .list(
                q=(
                    f"'{parent_id}' in parents"
                    f" and mimeType = 'application/vnd.google-apps.folder'"
                    f" and trashed = false"
                ),
                fields="files(id, name)",
            )
            .execute()
        )
        return results.get("files", [])
    except Exception as e:
        logger.error(f"Error listando carpetas Drive bajo {parent_id}: {e}")
        raise


# Lista los archivos dentro de una carpeta
def list_folder_files(folder_id: str) -> list[str]:
    try:
        service = _get_drive_service()
        results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name)",
            )
            .execute()
        )
        files = results.get("files", [])
        return [f["id"] for f in files]
    except Exception as e:
        logger.error(f"Error listando carpeta Drive {folder_id}: {e}")
        raise


# async wrappers

# Version async de upload_file
async def upload_file_async(
    file_bytes: bytes, filename: str, mimetype: str, folder_id: str,
) -> str:
    return await asyncio.to_thread(
        upload_file, file_bytes, filename, mimetype, folder_id,
    )


# Version async de get_file_bytes
async def get_file_bytes_async(file_id: str) -> bytes:
    return await asyncio.to_thread(get_file_bytes, file_id)


# Version async de find_or_create_folder
async def find_or_create_folder_async(name: str, parent_id: str) -> str:
    return await asyncio.to_thread(find_or_create_folder, name, parent_id)


# Version async de create_folder
async def create_folder_async(name: str, parent_id: str) -> str:
    return await asyncio.to_thread(create_folder, name, parent_id)


# Version async de delete_file
async def delete_file_async(file_id: str) -> None:
    return await asyncio.to_thread(delete_file, file_id)


# Version async de delete_folder
async def delete_folder_async(folder_id: str) -> None:
    return await asyncio.to_thread(delete_folder, folder_id)


# Version async de list_folder_files
async def list_folder_files_async(folder_id: str) -> list[str]:
    return await asyncio.to_thread(list_folder_files, folder_id)
