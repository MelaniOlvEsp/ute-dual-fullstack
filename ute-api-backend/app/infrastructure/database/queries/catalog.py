# Registro de consultas organizado por módulo.
from app.infrastructure.database.queries.auth import QUERIES as AUTH
from app.infrastructure.database.queries.dual_alumno_dual import QUERIES as DUAL_ALUMNO_DUAL
from app.infrastructure.database.queries.dual_coordinador_carrera import QUERIES as DUAL_COORDINADOR_CARRERA
from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES as DUAL_COORDINADOR_DUAL
from app.infrastructure.database.queries.foro_buzon import QUERIES as FORO_BUZON
from app.infrastructure.database.queries.foro_publicaciones import QUERIES as FORO_PUBLICACIONES

from app.infrastructure.database.queries.dual_tutor import QUERIES as DUAL_TUTOR
from app.infrastructure.database.queries.dual_organization import QUERIES as DUAL_ORGANIZATION
from app.infrastructure.database.queries.dual_obligaciones import QUERIES as DUAL_OBLIGACIONES
from app.infrastructure.database.queries.dual_entregas import QUERIES as DUAL_ENTREGAS
from app.infrastructure.database.queries.dual_revisiones import QUERIES as DUAL_REVISIONES

QUERIES = {
    **DUAL_REVISIONES,
    **DUAL_TUTOR,
    **DUAL_ORGANIZATION,
    **DUAL_OBLIGACIONES,
    **DUAL_ENTREGAS,
    **AUTH,
    **DUAL_ALUMNO_DUAL,
    **DUAL_COORDINADOR_CARRERA,
    **DUAL_COORDINADOR_DUAL,
    **FORO_BUZON,
    **FORO_PUBLICACIONES,
}
