from dataclasses import dataclass
from typing import Any, AsyncContextManager, Protocol


# Filtro del directorio de alumnos por período (C07): alumnos con semanas en ese período. No debe
# contener « AND »: `resolve_query` separa la cláusula WHERE por ese texto y compara cada trozo con
# la lista de filtros permitidos. Una sola definición para el caso de uso y para la lista permitida.
FILTRO_PERIODO_DIRECTORIO = (
    "a.matricula IN (SELECT x.matricula FROM obligaciones_semanales o "
    "JOIN alumnos_dual x ON x.id = o.incorporacion_id "
    "JOIN ciclos_dual p ON p.id = o.periodo_id WHERE p.cuatrimestre = %s)"
)


@dataclass(frozen=True)
class QueryRef:
    key: str
    where: str = ""
    assignments: tuple[str, ...] = ()


class QueryCursor(Protocol):
    # Ejecuta una consulta nombrada y sus parámetros por separado.
    async def execute(self, query: str | QueryRef, params: Any = None) -> Any:
        ...

    # Retorna una fila de la consulta ejecutada.
    async def fetchone(self) -> Any:
        ...

    # Retorna todas las filas de la consulta ejecutada.
    async def fetchall(self) -> Any:
        ...


class DatabasePort(Protocol):
    # Crea un contexto de lectura del repositorio.
    def read(self) -> AsyncContextManager[QueryCursor]:
        ...

    # Crea un contexto transaccional con commit o rollback.
    def transaction(self) -> AsyncContextManager[QueryCursor]:
        ...
