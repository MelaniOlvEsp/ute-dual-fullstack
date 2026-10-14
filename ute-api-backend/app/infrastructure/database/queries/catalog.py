# Registro de consultas organizado por módulo.
from app.infrastructure.database.queries.auth import QUERIES as AUTH
from app.infrastructure.database.queries.dual_alumno_dual import QUERIES as DUAL_ALUMNO_DUAL
from app.infrastructure.database.queries.dual_coordinador_carrera import QUERIES as DUAL_COORDINADOR_CARRERA
from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES as DUAL_COORDINADOR_DUAL
from app.infrastructure.database.queries.foro_buzon import QUERIES as FORO_BUZON
from app.infrastructure.database.queries.foro_publicaciones import QUERIES as FORO_PUBLICACIONES

from app.infrastructure.database.queries.dual_tutor import QUERIES as DUAL_TUTOR

QUERIES = {
    **DUAL_TUTOR,
    **AUTH,
    **DUAL_ALUMNO_DUAL,
    **DUAL_COORDINADOR_CARRERA,
    **DUAL_COORDINADOR_DUAL,
    **FORO_BUZON,
    **FORO_PUBLICACIONES,
}
