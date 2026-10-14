from dataclasses import dataclass
from functools import lru_cache

from app.infrastructure.config.settings import settings
from app.infrastructure.database.repository import PostgresGateway
from app.infrastructure.documents import dual_reports, signatures
from app.infrastructure.integrations import drive
from app.infrastructure.security import jwt_passwords


class ServiceAdapter:
    validate_signature = staticmethod(signatures.validate_signature)
    sign_pdf = staticmethod(signatures.sign_pdf)
    hash_password = staticmethod(jwt_passwords.hash_password)
    verify_password = staticmethod(jwt_passwords.verify_password)
    crear_token = staticmethod(jwt_passwords.crear_token)
    verificar_token = staticmethod(jwt_passwords.verificar_token)
    extraer_matricula = staticmethod(jwt_passwords.extraer_matricula)
    upload_file = staticmethod(drive.upload_file)
    get_file_bytes_async = staticmethod(drive.get_file_bytes_async)
    delete_file = staticmethod(drive.delete_file)
    delete_folder = staticmethod(drive.delete_folder)
    list_folder_files = staticmethod(drive.list_folder_files)
    find_or_create_folder = staticmethod(drive.find_or_create_folder)
    upload_file_async = staticmethod(drive.upload_file_async)
    find_or_create_folder_async = staticmethod(drive.find_or_create_folder_async)
    delete_file_async = staticmethod(drive.delete_file_async)
    procesar_y_subir_pdf_reporte = staticmethod(
        dual_reports.procesar_y_subir_pdf_reporte
    )
    eliminar_pdf_local = staticmethod(dual_reports.eliminar_pdf_local)
    obtener_pdf_bytes = staticmethod(dual_reports.obtener_pdf_bytes)
    subir_pdf_a_drive_desde_local = staticmethod(
        dual_reports.subir_pdf_a_drive_desde_local
    )
    leer_pdf_local = staticmethod(dual_reports.leer_pdf_local)


@dataclass(frozen=True)
class Runtime:
    database: PostgresGateway
    services: ServiceAdapter
    settings: object


# Construye las dependencias una vez, sin abrir conexiones anticipadamente.
@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    return Runtime(PostgresGateway(), ServiceAdapter(), settings)

