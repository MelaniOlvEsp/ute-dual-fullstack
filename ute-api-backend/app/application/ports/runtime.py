from typing import Any, Awaitable, Callable, Protocol

from app.application.ports.query import DatabasePort


class SettingsPort(Protocol):
    drive_folder_dual: str


class ServicesPort(Protocol):
    validate_signature: Callable[..., None]
    sign_pdf: Callable[..., bytes]
    # Define las operaciones externas consumidas por los casos de uso.
    hash_password: Callable[..., str]
    verify_password: Callable[..., bool]
    crear_token: Callable[..., str]
    verificar_token: Callable[..., dict]
    extraer_matricula: Callable[..., str]
    upload_file: Callable[..., Any]
    get_file_bytes_async: Callable[..., Awaitable[bytes]]
    delete_file: Callable[..., Any]
    delete_folder: Callable[..., Any]
    list_folder_files: Callable[..., Any]
    find_or_create_folder: Callable[..., Any]
    upload_file_async: Callable[..., Awaitable[Any]]
    find_or_create_folder_async: Callable[..., Awaitable[Any]]
    delete_file_async: Callable[..., Awaitable[Any]]
    leer_pdf_limitado: Callable[..., Awaitable[bytes]]
    inspeccionar_pdf: Callable[..., int]
    guardar_documento: Callable[..., Awaitable[dict]]
    leer_documento: Callable[..., Awaitable[bytes]]
    eliminar_documento: Callable[..., Awaitable[Any]]
    purgar_documento: Callable[..., Awaitable[bool]]
    eliminar_pdf_local: Callable[..., Awaitable[Any]]
    obtener_pdf_bytes: Callable[..., Awaitable[bytes]]
    leer_pdf_local: Callable[..., Awaitable[bytes]]
    estampar_firma: Callable[..., tuple]
    nuevo_paquete_temporal: Callable[..., Any]
    construir_paquete: Callable[..., dict]
    leer_limitado_plantilla: Callable[..., Awaitable[bytes]]
    inspeccionar_plantilla: Callable[..., int]
    guardar_plantilla: Callable[..., Awaitable[dict]]
    leer_plantilla: Callable[..., Awaitable[bytes]]
    eliminar_plantilla: Callable[..., Awaitable[Any]]


class RuntimePort(Protocol):
    database: DatabasePort
    services: ServicesPort
    settings: SettingsPort

