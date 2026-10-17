import ast
import json
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError

from app.application.dto.foro import BuzonMensajeCreate
from app.application.errors import ApplicationError
from app.application.use_cases.auth import login
from app.application.use_cases.foro import buzon
from app.domain.roles import active_roles
from app.application.dto.auth import UserRoles


ROOT = Path(__file__).resolve().parents[1]


class RemovedModuleTests(unittest.TestCase):
    # Comprueba que los componentes exclusivos no permanezcan en el proyecto.
    def test_exclusive_modules_are_absent(self):
        paths = (
            'app/application/use_cases/becas',
            'app/presentation/api/routers/becas',
            'app/application/dto/solicitudes.py',
            'app/infrastructure/documents/scholarship_dossier.py',
            'app/infrastructure/database/queries/becas_admin.py',
            'app/infrastructure/database/queries/becas_alumnos.py',
            'app/infrastructure/database/queries/becas_convocatoria.py',
            'app/infrastructure/database/queries/becas_solicitudes.py',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())

    # Asegura que el registro de rutas solo contenga módulos activos.
    def test_removed_routes_are_not_registered(self):
        source = (ROOT / 'app/main.py').read_text(encoding='utf-8')
        self.assertNotIn('presentation.api.routers.becas', source)
        self.assertNotIn("prefix='/solicitudes'", source)
        self.assertNotIn("prefix='/admin'", source)
        self.assertNotIn("prefix='/alumnos'", source)
        self.assertNotIn("prefix='/admin/becas'", source)
        routes = json.loads((ROOT / 'tests/route_contract.json').read_text())
        self.assertEqual(sum(map(len, routes.values())), 68)

    # Evita exponer privilegios anteriores en los roles de sesión.
    def test_roles_are_filtered(self):
        result = active_roles({
            'admin': False,
            'alumno': False,
            'coordinador_dual': True,
            'coordinador_becas': True,
        })
        self.assertNotIn('coordinador_becas', result)
        self.assertTrue(result['coordinador_dual'])

    # Rechaza asignaciones de roles eliminados al crear personal.
    def test_legacy_role_cannot_be_assigned(self):
        with self.assertRaises(ValidationError):
            UserRoles(coordinador_becas=True)

    # Restringe el contrato del buzón al área vigente.
    def test_inbox_schema_only_accepts_dual(self):
        self.assertEqual(
            BuzonMensajeCreate(
                area='dual', asunto='Consulta', mensaje='Hola'
            ).area,
            'dual',
        )
        with self.assertRaises(ValidationError):
            BuzonMensajeCreate(
                area='becas', asunto='Consulta', mensaje='Hola'
            )

    # Confirma que las consultas a mensajes excluyan las áreas retiradas.
    def test_historic_messages_not_exposed(self):
        path = ROOT / 'app/infrastructure/database/queries/foro_buzon.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        statements = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'QUERIES'
                    for target in node.targets)
        )
        for key in ('foro.buzon.q000', 'foro.buzon.q003',
                    'foro.buzon.q004'):
            with self.subTest(key=key):
                self.assertIn("area = 'dual'", statements[key]['sql'])


class RemovedModuleUseCaseTests(unittest.IsolatedAsyncioTestCase):
    # Deniega la inserción de mensajes en un área deshabilitada.
    async def test_cannot_insert_removed_area(self):
        data = SimpleNamespace(area='becas')
        with self.assertRaises(ApplicationError) as caught:
            await buzon.enviar_mensaje(data, {}, runtime=SimpleNamespace())
        self.assertEqual(caught.exception.status_code, 422)

    # Deniega la consulta al área deshabilitada sin acceder a datos.
    async def test_cannot_list_removed_area(self):
        with self.assertRaises(ApplicationError) as caught:
            await buzon.listar_mensajes(
                'becas', {'roles': {'admin': True}},
                runtime=SimpleNamespace(),
            )
        self.assertEqual(caught.exception.status_code, 422)

    # Evita incluir permisos heredados en los JWT emitidos al iniciar sesión.
    async def test_login_only_emits_supported_roles(self):
        claims = {}

        class Cursor:
            # Emula la consulta del usuario registrado.
            async def execute(self, query, params=None):
                return None

            # Devuelve roles actuales y antiguos almacenados en JSONB.
            async def fetchone(self):
                return {
                    'id': 'user-1',
                    'email': 'user@ute.edu.mx',
                    'password_hash': 'hash',
                    'email_verificado': True,
                    'roles': {'alumno': False, 'coordinador_dual': True,
                              'coordinador_becas': True},
                    'login_locked_until': None,
                    'login_attempts': 0,
                    'matricula': None,
                    'must_change_password': False,
                    'credential_version': 0,
                }

        class Database:
            # Simula una transacción exitosa sin servicios externos.
            @asynccontextmanager
            async def transaction(self):
                yield Cursor()

        def make_token(payload):
            # Registra el payload emitido para verificar su contenido.
            claims.update(payload)
            return 'token'

        runtime = SimpleNamespace(
            database=Database(),
            services=SimpleNamespace(
                verify_password=lambda *_: True,
                crear_token=make_token,
            ),
        )
        data = SimpleNamespace(email='user@ute.edu.mx', password='pass')
        result = await login(data, None, runtime=runtime)
        self.assertEqual(result['access_token'], 'token')
        self.assertTrue(claims['roles']['coordinador_dual'])
        self.assertNotIn('coordinador_becas', claims['roles'])


if __name__ == '__main__':
    unittest.main()
