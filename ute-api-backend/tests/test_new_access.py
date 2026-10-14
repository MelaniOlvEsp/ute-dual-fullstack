import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.application.errors import ApplicationError
from app.application.use_cases import auth
from app.domain.roles import active_roles, has_role
from app.domain.passwords import validate_password


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    async def execute(self, query, params=None):
        self.calls.append((query, params))

    async def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    async def fetchall(self):
        return self.rows


class Database:
    def __init__(self, cursor):
        self.cursor = cursor

    @asynccontextmanager
    async def read(self):
        yield self.cursor

    @asynccontextmanager
    async def transaction(self):
        yield self.cursor


class NewPermissionsTests(unittest.TestCase):
    def test_only_three_roles_exist(self):
        roles = active_roles({'admin': True, 'coordinador_carrera': True,
                              'alumno': True})
        self.assertEqual(set(roles), {'alumno', 'tutor_academico',
                                      'coordinador_dual'})
        self.assertFalse(has_role({'roles': {'admin': True}}, 'tutor_academico'))

    def test_password_policy(self):
        validate_password('SecurePassword123')
        with self.assertRaises(ValueError):
            validate_password('Weak123')


class NewProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_registration_of_authorized_student(self):
        cur = Cursor([{'matricula': '123456789'}, None])
        runtime = SimpleNamespace(database=Database(cur), services=SimpleNamespace(
            extraer_matricula=lambda email: email.split('@')[0],
            hash_password=lambda plain: 'hash:' + plain,
        ))
        result = await auth.register(SimpleNamespace(
            email='123456789@ute.edu.mx', password='SecurePassword123'),
            runtime=runtime)
        self.assertIn('Cuenta creada', result['mensaje'])
        self.assertEqual(cur.calls[-1][0], 'auth.insert_student')
        self.assertTrue(any(call[0] == 'auth.student_allowed'
                            for call in cur.calls))

    async def test_reset_only_authorized_student_and_invalidate_sessions(self):
        cur = Cursor([{'id': 'id1', 'email': '123456789@ute.edu.mx'}])
        runtime = SimpleNamespace(database=Database(cur), services=SimpleNamespace(
            hash_password=lambda _: 'hash'
        ))
        result = await auth.reset_password_alumno(
            '123456789', {'id': 'tutor'}, runtime=runtime)
        self.assertGreaterEqual(len(result['password_temporal']), 20)
        self.assertEqual(cur.calls[-1][0], 'auth.password_temp')

    async def test_old_token_rejected_when_version_changes(self):
        cur = Cursor([{'roles': {'alumno': True},
                       'must_change_password': True,
                       'credential_version': 2}])
        runtime = SimpleNamespace(database=Database(cur))
        with self.assertRaises(ApplicationError) as caught:
            await auth.security_state({'id': 'id1', 'sub': 'student@ute.edu.mx',
                                       'credential_version': 1},
                                      runtime=runtime)
        self.assertEqual(caught.exception.status_code, 401)
