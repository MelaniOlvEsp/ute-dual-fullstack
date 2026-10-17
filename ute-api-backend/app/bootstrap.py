from dataclasses import dataclass
from functools import lru_cache

from app.infrastructure.config.settings import settings
from app.infrastructure.database.repository import PostgresGateway
from app.infrastructure.documents import dual_reports, paquetes, signatures
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
    # C05: entrega de reportes con documentos privados.
    leer_pdf_limitado = staticmethod(dual_reports.leer_pdf_limitado)
    inspeccionar_pdf = staticmethod(dual_reports.inspeccionar_pdf)
    guardar_documento = staticmethod(dual_reports.guardar_documento)
    leer_documento = staticmethod(dual_reports.leer_documento)
    eliminar_documento = staticmethod(dual_reports.eliminar_documento)
    purgar_documento = staticmethod(dual_reports.purgar_documento)
    eliminar_pdf_local = staticmethod(dual_reports.eliminar_pdf_local)
    obtener_pdf_bytes = staticmethod(dual_reports.obtener_pdf_bytes)
    leer_pdf_local = staticmethod(dual_reports.leer_pdf_local)
    # C06: firma estampada en la celda del tutor (respaldo: hoja adicional).
    estampar_firma = staticmethod(signatures.estampar_firma)
    # C08: paquete de archivo (ZIP) con verificación de hashes.
    nuevo_paquete_temporal = staticmethod(paquetes.nuevo_temporal)
    construir_paquete = staticmethod(paquetes.construir_zip)


@dataclass(frozen=True)
class Runtime:
    database: PostgresGateway
    services: ServiceAdapter
    settings: object


# Construye las dependencias una vez, sin abrir conexiones anticipadamente.
@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    return Runtime(PostgresGateway(), ServiceAdapter(), settings)

