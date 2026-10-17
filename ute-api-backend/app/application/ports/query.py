from dataclasses import dataclass
from typing import Any, AsyncContextManager, Protocol


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
