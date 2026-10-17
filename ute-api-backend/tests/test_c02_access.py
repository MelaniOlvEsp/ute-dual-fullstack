"""C02: límites, carreras de credenciales y aislamiento (repositorio simulado)."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError
from app.application.dto.auth import RegisterSchema
from app.application.errors import ApplicationError
from app.application.use_cases import auth
from app.application.use_cases.dual import coordinador_carrera, entregas
from app.application.use_cases.foro import buzon
from app.domain.passwords import validate_password
from tests.test_new_access import Cursor, Database


class PasswordTests(unittest.TestCase):
    def test_exact_utf8_boundary(self):
        validate_password('Aa1' + 'x' * 69)
        validate_password('Aa12' + 'é' * 34)
        for password in ('Aa1' + 'x' * 70, 'Aa1' + 'é' * 35):
            with self.assertRaisesRegex(ValueError, '72 bytes'):
                validate_password(password)

    def test_registration_rejects_injected_role(self):
        with self.assertRaises(ValidationError):
            RegisterSchema(email='123456789@ute.edu.mx', password='SecurePassword123',
                           roles={'coordinador_dual': True})

    def test_unicode_digit_policy_and_no_bcrypt_truncation(self):
        validate_password('PasswordTest١')
        with self.assertRaises(ValueError):
            validate_password('PasswordTest²')
        from app.infrastructure.security.jwt_passwords import verify_password
        # Un hash inválido tampoco se consulta cuando la entrada supera bcrypt.
        self.assertFalse(verify_password('Aa1' + 'x' * 70, 'not-a-hash'))


class AccessTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, rows):
        self.cur = Cursor(rows)
        return SimpleNamespace(database=Database(self.cur), services=SimpleNamespace(
            hash_password=lambda _: 'hash', verify_password=lambda *_: True,
            extraer_matricula=lambda email: email.split('@')[0],
            obtener_pdf_bytes=AsyncMock(return_value=b'%PDF-test')))

    async def test_duplicate_registration_maps_conflict(self):
        runtime = self.runtime([{'matricula': '123456789'}, None, None])
        with self.assertRaises(ApplicationError) as caught:
            await auth.register(SimpleNamespace(email='123456789@ute.edu.mx',
                                                password='SecurePassword123'), runtime=runtime)
        self.assertEqual(caught.exception.status_code, 409)

    async def test_tutor_insert_conflict(self):
        runtime = self.runtime([None, None])
        with self.assertRaises(ApplicationError) as caught:
            await auth.crear_tutor(SimpleNamespace(email='tutor@ute.edu.mx', nombre='Tutor'), {}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 409)

    async def test_generated_temporaries_always_meet_policy(self):
        with patch.object(auth.secrets, 'token_urlsafe', return_value='_' * 24):
            result = await auth.crear_tutor(SimpleNamespace(email='tutor@ute.edu.mx', nombre='Tutor'), {},
                                           runtime=self.runtime([None, {'id': 'new'}]))
            validate_password(result['password_temporal'])
            self.assertEqual(len(result['password_temporal']), 12)
            result = await auth.reset_password_alumno('123456789', {}, runtime=self.runtime([{'id': 's'}]))
            validate_password(result['password_temporal'])
            self.assertEqual(len(result['password_temporal']), 12)

    async def test_stale_password_change_does_not_overwrite_reset(self):
        runtime = self.runtime([{'password_hash': 'hash', 'credential_version': 2}])
        with self.assertRaises(ApplicationError) as caught:
            await auth.cambiar_password(SimpleNamespace(password_actual='SecurePassword123', password_nueva='NewSecurePassword123'),
                                        {'id': 's', 'credential_version': 1}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(len(self.cur.calls), 1)

    async def test_wrong_current_password_preserves_valid_session(self):
        runtime = self.runtime([{'password_hash': 'hash', 'credential_version': 1}])
        runtime.services.verify_password = lambda *_: False
        with self.assertRaises(ApplicationError) as caught:
            await auth.cambiar_password(SimpleNamespace(password_actual='WrongPassword123', password_nueva='NewSecurePassword123'),
                                        {'id': 's', 'credential_version': 1}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(len(self.cur.calls), 1)

    async def test_foreign_pdf_denied_before_storage(self):
        # C08: la descarga del alumno consulta solo lo propio (la consulta filtra por su matrícula).
        runtime = self.runtime([None])
        runtime.services.leer_documento = AsyncMock(return_value=b'%PDF-test')
        with self.assertRaises(ApplicationError) as caught:
            await entregas.descargar_version('report-b', 1, {'matricula': 'A'}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 404)
        runtime.services.leer_documento.assert_not_awaited()
        self.assertEqual(self.cur.calls[0][1], ('report-b', 'A', 1))

    async def test_own_pdf_reaches_storage(self):
        runtime = self.runtime([{'original': 'a' * 32 + '.pdf', 'firmado': None}])
        runtime.services.leer_documento = AsyncMock(return_value=b'%PDF-test')
        result = await entregas.descargar_version('report-a', 1, {'matricula': 'A'}, runtime=runtime)
        self.assertEqual(result.media_type, 'application/pdf')
        runtime.services.leer_documento.assert_awaited_once_with('a' * 32 + '.pdf', None)

    async def test_foreign_mailbox_reply_does_not_write(self):
        runtime = self.runtime([{'alumno_id': 'B', 'area': 'dual', 'estado': 'Enviado'}])
        with self.assertRaises(ApplicationError) as caught:
            await buzon.responder_mensaje('message-b', SimpleNamespace(texto='Test'),
                                         {'id': 'A', 'roles': {'alumno': True}}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(len(self.cur.calls), 1)

    async def test_student_cannot_close_even_own_mailbox(self):
        runtime = self.runtime([])
        with self.assertRaises(ApplicationError) as caught:
            await buzon.cerrar_mensaje('own-message', {'id': 'A', 'roles': {'alumno': True}}, runtime=runtime)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(self.cur.calls, [])

    async def test_student_deactivation_preserves_academic_records(self):
        runtime = self.runtime([{'matricula': 'A'}])
        result = await coordinador_carrera.eliminar_alumno('A', {}, runtime=runtime)
        self.assertIn('conservado', result['mensaje'])
        self.assertEqual([call[0] for call in self.cur.calls], [
            'dual.coordinador_carrera.q021', 'dual.coordinador_carrera.q025', 'dual.coordinador_carrera.q022'])

if __name__ == '__main__':
    unittest.main()
