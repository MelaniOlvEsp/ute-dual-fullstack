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
    procesar_y_subir_pdf_reporte: Callable[..., Awaitable[Any]]
    eliminar_pdf_local: Callable[..., Awaitable[Any]]
    obtener_pdf_bytes: Callable[..., Awaitable[bytes]]
    subir_pdf_a_drive_desde_local: Callable[..., Awaitable[Any]]
    leer_pdf_local: Callable[..., Awaitable[bytes]]


class RuntimePort(Protocol):
    database: DatabasePort
    services: ServicesPort
    settings: SettingsPort

