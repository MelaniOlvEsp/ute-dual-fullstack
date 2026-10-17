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
    leer_pdf_limitado: Callable[..., Awaitable[bytes]]
    inspeccionar_pdf: Callable[..., int]
    guardar_documento: Callable[..., Awaitable[dict]]
    leer_documento: Callable[..., Awaitable[bytes]]
    eliminar_documento: Callable[..., Awaitable[Any]]
    purgar_documento: Callable[..., Awaitable[bool]]
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

