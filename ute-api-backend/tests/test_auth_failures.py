import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.application.errors import ApplicationError
from app.application.use_cases.auth import login, register


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.queries = []

    async def execute(self, query, params=None):
        self.queries.append((query, params))

    async def fetchone(self):
        return self.rows.pop(0) if self.rows else None


class CommittingDatabase:
    def __init__(self, cursor):
        self.cursor = cursor
        self.committed = False
        self.rolled_back = False

    @asynccontextmanager
    async def transaction(self):
        try:
            yield self.cursor
        except Exception:
            self.rolled_back = True
            raise
        else:
            self.committed = True


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_wrong_password_is_committed(self):
        cursor = Cursor([{
            'id': 'id1', 'email': 'alumno@ute.edu.mx',
            'roles': {'alumno': True}, 'password_hash': 'hash',
            'login_attempts': 2, 'login_locked_until': None,
        }])
        database = CommittingDatabase(cursor)
        runtime = SimpleNamespace(database=database, services=SimpleNamespace(
            verify_password=lambda *_: False
        ))
        with self.assertRaises(ApplicationError) as caught:
            await login(SimpleNamespace(email='alumno@ute.edu.mx',
                                        password='incorrecta'), None,
                        runtime=runtime)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(cursor.queries[-1][0], 'auth.login_failed')
        self.assertTrue(database.committed)

    async def test_unapproved_student_cannot_register(self):
        cursor = Cursor([None])
        database = CommittingDatabase(cursor)
        runtime = SimpleNamespace(database=database, services=SimpleNamespace(
            extraer_matricula=lambda value: value.split('@')[0]
        ))
        with self.assertRaises(ApplicationError) as caught:
            await register(SimpleNamespace(email='123456789@ute.edu.mx',
                                           password='SecurePassword123'),
                           runtime=runtime)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(cursor.queries[0][0], 'auth.student_allowed')
        self.assertFalse(database.committed)
