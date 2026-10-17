from dataclasses import dataclass
from functools import lru_cache

from app.infrastructure.config.settings import settings
from app.infrastructure.database.repository import PostgresGateway
from app.infrastructure.documents import dual_reports, paquetes, plantillas, signatures
from app.infrastructure.security import jwt_passwords


class ServiceAdapter:
    validate_signature = staticmethod(signatures.validate_signature)
    sign_pdf = staticmethod(signatures.sign_pdf)
    hash_password = staticmethod(jwt_passwords.hash_password)
    verify_password = staticmethod(jwt_passwords.verify_password)
    crear_token = staticmethod(jwt_passwords.crear_token)
    verificar_token = staticmethod(jwt_passwords.verificar_token)
    extraer_matricula = staticmethod(jwt_passwords.extraer_matricula)
    # C05: entrega de reportes con documentos privados.
    leer_pdf_limitado = staticmethod(dual_reports.leer_pdf_limitado)
    inspeccionar_pdf = staticmethod(dual_reports.inspeccionar_pdf)
    guardar_documento = staticmethod(dual_reports.guardar_documento)
    leer_documento = staticmethod(dual_reports.leer_documento)
    eliminar_documento = staticmethod(dual_reports.eliminar_documento)
    purgar_documento = staticmethod(dual_reports.purgar_documento)
    # C06: firma estampada en la celda del tutor (respaldo: hoja adicional).
    estampar_firma = staticmethod(signatures.estampar_firma)
    # C08: paquete de archivo (ZIP) con verificación de hashes.
    nuevo_paquete_temporal = staticmethod(paquetes.nuevo_temporal)
    construir_paquete = staticmethod(paquetes.construir_zip)
    # C09: plantilla común Word + PDF.
    leer_limitado_plantilla = staticmethod(plantillas.leer_limitado)
    inspeccionar_plantilla = staticmethod(plantillas.inspeccionar)
    guardar_plantilla = staticmethod(plantillas.guardar_plantilla)
    leer_plantilla = staticmethod(plantillas.leer_plantilla)
    eliminar_plantilla = staticmethod(plantillas.eliminar_plantilla)


@dataclass(frozen=True)
class Runtime:
    database: PostgresGateway
    services: ServiceAdapter
    settings: object


# Construye las dependencias una vez, sin abrir conexiones anticipadamente.
@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    return Runtime(PostgresGateway(), ServiceAdapter(), settings)

