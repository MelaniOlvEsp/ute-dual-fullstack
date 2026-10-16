from contextlib import asynccontextmanager

from psycopg import sql

from app.application.ports.query import QueryRef
from app.infrastructure.database.postgres import get_cursor, get_transaction
from app.infrastructure.database.queries.catalog import QUERIES


# Fragmentos permitidos para composición controlada de filtros.
FILTERS = {
    'dual.coordinador_carrera.q003': frozenset({
        'ad.activo = TRUE', 'g.cuatrimestre::text = %s',
        'g.nomenclatura = %s',
    }),
    'dual.coordinador_carrera.q014': frozenset({'g.carrera = %s'}),
    'dual.coordinador_dual.q000': frozenset({
        'r.estado = %s', 'r.cuatrimestre = %s',
    }),
}

ASSIGNMENTS = {
    'dual.coordinador_carrera.update_student': frozenset({
        'nombre = %s',
    }),
}


# Evita que parámetros externos construyan identificadores o sentencias SQL.
def resolve_query(query: str | QueryRef):
    key = query.key if isinstance(query, QueryRef) else query
    if key not in QUERIES:
        raise ValueError(f'Consulta no registrada: {key}')
    entry = QUERIES[key]
    if not isinstance(query, QueryRef):
        if entry['dynamic']:
            raise ValueError(f'La consulta requiere filtros: {key}')
        return entry['sql']
    if entry['dynamic'] == 'where':
        expression = query.where
        if expression:
            if not expression.startswith('WHERE '):
                raise ValueError('Cláusula WHERE inválida')
            clauses = expression[6:].split(' AND ')
            if not all(clause in FILTERS.get(key, ()) for clause in clauses):
                raise ValueError('Filtro no permitido')
        return sql.SQL(entry['sql']).format(where=sql.SQL(expression))
    if entry['dynamic'] == 'assignments':
        fields = query.assignments
        if not fields or any(field not in ASSIGNMENTS[key] for field in fields):
            raise ValueError('Campos de actualización no permitidos')
        return sql.SQL(entry['sql']).format(
            assignments=sql.SQL(', ').join(sql.SQL(f) for f in fields)
        )
    raise ValueError(f'Consulta estática no requiere QueryRef: {key}')


class QueryCursorAdapter:
    # Encapsula psycopg y resuelve SQL nombrado sin exponer el motor.
    def __init__(self, cursor):
        self._cursor = cursor

    # Ejecuta sentencias parametrizadas usando el cursor subyacente.
    async def execute(self, query, params=None):
        return await self._cursor.execute(resolve_query(query), params)

    # Recupera una fila del resultado.
    async def fetchone(self):
        return await self._cursor.fetchone()

    # Recupera todas las filas del resultado.
    async def fetchall(self):
        return await self._cursor.fetchall()


class PostgresGateway:
    # Expone lecturas a los casos de uso como puerto de base de datos.
    @asynccontextmanager
    async def read(self):
        async with get_cursor() as cursor:
            yield QueryCursorAdapter(cursor)

    # Expone operaciones atómicas con commit o rollback.
    @asynccontextmanager
    async def transaction(self):
        async with get_transaction() as cursor:
            yield QueryCursorAdapter(cursor)
