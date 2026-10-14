import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.application.errors import ApplicationError
from app.application.responses import FileResult
from app.application.use_cases.foro.publicaciones import (
    crear_publicacion,
    eliminar_publicacion,
)


class FakeCursor:
    # Devuelve filas programadas y registra las consultas invocadas.
    def __init__(self, rows):
        self._rows = list(rows)
        self.calls = []

    # Guarda la sentencia y los argumentos sin ejecutar SQL real.
    async def execute(self, query, params=None):
        self.calls.append((query, params))

    # Obtiene la siguiente respuesta del repositorio falso.
    async def fetchone(self):
        return self._rows.pop(0)

    # Simula el resultado completo de una consulta.
    async def fetchall(self):
        return []


class FakeDatabase:
    # Expone el puerto de base de datos para pruebas aisladas.
    def __init__(self, cursor):
        self.cursor = cursor

    # Simula un contexto de lectura.
    @asynccontextmanager
    async def read(self):
        yield self.cursor

    # Simula una transacción sin conectarse a PostgreSQL.
    @asynccontextmanager
    async def transaction(self):
        yield self.cursor


class UseCasesTest(unittest.IsolatedAsyncioTestCase):
    # Verifica que el caso de uso utilice los IDs de consultas y no SQL.
    async def test_create_publication_uses_database_port(self):
        cursor = FakeCursor([
            {"nombre": "Coordinación", "roles": {"coordinador_dual": True}},
            {"id": "post-1", "contenido": "Comunicado"},
        ])
        runtime = SimpleNamespace(database=FakeDatabase(cursor))
        data = SimpleNamespace(contenido="Comunicado")
        user = {"id": "user-1", "sub": "correo@ute.mx", "roles": {}}
        result = await crear_publicacion(data, user, runtime=runtime)
        self.assertEqual(result["mi_reaccion"], None)
        self.assertEqual(cursor.calls[0][0], "foro.publicaciones.q000")
        self.assertEqual(cursor.calls[1][0], "foro.publicaciones.q001")
        self.assertEqual(cursor.calls[1][1][1], "Coordinación")
        self.assertEqual(cursor.calls[1][1][2], "Coordinación Dual")

    # Comprueba la validación de permisos sin FastAPI ni conexión real.
    async def test_delete_publication_denies_unrelated_user(self):
        cursor = FakeCursor([{"autor_id": "otro"}])
        runtime = SimpleNamespace(database=FakeDatabase(cursor))
        with self.assertRaises(ApplicationError) as caught:
            await eliminar_publicacion(
                "post-1", {"id": "actual", "roles": {}}, runtime=runtime,
            )
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(len(cursor.calls), 1)

    # Conserva las propiedades independientes de la respuesta HTTP.
    def test_binary_result(self):
        result = FileResult(b"content", "application/pdf")
        self.assertEqual(result.media_type, "application/pdf")
