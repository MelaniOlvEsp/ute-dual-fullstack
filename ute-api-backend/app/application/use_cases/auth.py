"""Casos de uso de acceso para tres roles Dual."""
import secrets
from datetime import datetime, timedelta, timezone

from app.application.errors import ApplicationError
from app.domain.passwords import validate_password
from app.domain.roles import active_roles


def _valid_password(value: str) -> None:
    # Convierte validaciones de dominio a respuestas de aplicación.
    try:
        validate_password(value)
    except ValueError as exc:
        raise ApplicationError(400, str(exc)) from exc


async def register(data, *, runtime):
    # Permite auto-registro solo si el tutor cargó la matrícula.
    email = data.email.lower().strip()
    matricula = runtime.services.extraer_matricula(email)
    _valid_password(data.password)
    async with runtime.database.transaction() as cur:
        await cur.execute('auth.student_allowed', (matricula, email))
        if not await cur.fetchone():
            raise ApplicationError(
                403, 'Tu matrícula debe ser autorizada por un tutor académico'
            )
        await cur.execute('auth.account_exists', (email,))
        if await cur.fetchone():
            raise ApplicationError(409, 'Ya existe una cuenta con este correo')
        await cur.execute('auth.insert_student', (
            email, runtime.services.hash_password(data.password), matricula
        ))
    return {'mensaje': 'Cuenta creada. Ya puedes iniciar sesión.'}


async def login(data, _rl, *, runtime):
    # Mantiene el límite de intentos sin depender de correos externos.
    email = data.email.lower().strip()
    error = None
    async with runtime.database.transaction() as cur:
        await cur.execute('auth.login', (email,))
        row = await cur.fetchone()
        if row is None:
            raise ApplicationError(401, 'Credenciales incorrectas')
        account = dict(row)
        roles = active_roles(account['roles'])
        if not any(roles.values()):
            raise ApplicationError(403, 'Tu cuenta no tiene un rol Dual válido')
        now = datetime.now(timezone.utc)
        locked = account.get('login_locked_until')
        if locked and locked.replace(tzinfo=locked.tzinfo or timezone.utc) > now:
            raise ApplicationError(429, 'Cuenta bloqueada temporalmente')
        if not runtime.services.verify_password(
            data.password, account['password_hash']
        ):
            attempts = (account.get('login_attempts') or 0) + 1
            until = now + timedelta(minutes=15) if attempts >= 5 else None
            await cur.execute('auth.login_failed', (attempts, until, email))
            error = ApplicationError(
                429 if until else 401,
                'Cuenta bloqueada temporalmente' if until
                else 'Credenciales incorrectas',
            )
        else:
            await cur.execute('auth.login_reset', (email,))
    if error:
        raise error
    claims = {
        'sub': account['email'], 'id': str(account['id']),
        'matricula': account['matricula'], 'roles': roles,
        'must_change_password': account['must_change_password'],
        'credential_version': account['credential_version'],
        'nombre': account.get('nombre'),
        'grupo_id': str(account['grupo_id']) if account.get('grupo_id') else None,
        'turno': account.get('turno'),
        'nomenclatura': account.get('nomenclatura'),
        'cuatrimestre': account.get('cuatrimestre'),
        'carrera': account.get('carrera'),
        'modalidad': account.get('modalidad'),
        'dual_activo': account.get('dual_activo', False),
    }
    return {
        'access_token': runtime.services.crear_token(claims),
        'token_type': 'bearer',
        'must_change_password': account['must_change_password'],
    }


async def security_state(user, *, runtime):
    # Verifica versión de credenciales y rol actual en cada petición.
    async with runtime.database.read() as cur:
        await cur.execute('auth.security_state', (user['id'], user['sub'].lower()))
        row = await cur.fetchone()
    if not row:
        raise ApplicationError(401, 'La cuenta ya no está disponible')
    row = dict(row)
    roles = active_roles(row['roles'])
    if not any(roles.values()):
        raise ApplicationError(403, 'Tu cuenta no tiene un rol Dual válido')
    if row['credential_version'] != user.get('credential_version'):
        raise ApplicationError(401, 'La sesión ha expirado; inicia de nuevo')
    return {**user, 'roles': roles,
            'must_change_password': row['must_change_password']}


async def me(user, *, runtime):
    # Devuelve el perfil de la cuenta que ya pasó autorización.
    async with runtime.database.read() as cur:
        await cur.execute('auth.me', (user['sub'].lower(),))
        row = await cur.fetchone()
    if not row:
        raise ApplicationError(404, 'Usuario no encontrado')
    return {**dict(row), 'roles': active_roles(row['roles'])}


async def cambiar_password(data, user, *, runtime):
    # Permite sustituir la clave provisional por una definitiva.
    _valid_password(data.password_nueva)
    if data.password_actual == data.password_nueva:
        raise ApplicationError(400, 'La nueva contraseña debe ser diferente')
    async with runtime.database.transaction() as cur:
        await cur.execute('auth.password_current', (user['id'],))
        row = await cur.fetchone()
        if not row or not runtime.services.verify_password(
            data.password_actual, row['password_hash']
        ):
            raise ApplicationError(401, 'Contraseña actual incorrecta')
        await cur.execute('auth.password_change', (
            runtime.services.hash_password(data.password_nueva), user['id']
        ))
    return {'mensaje': 'Contraseña actualizada. Inicia sesión nuevamente.'}


async def crear_tutor(data, coordinator, *, runtime):
    # El coordinador entrega la clave temporal una sola vez.
    email = data.email.lower().strip()
    if not email.endswith('@ute.edu.mx'):
        raise ApplicationError(400, 'Se requiere correo institucional')
    password = secrets.token_urlsafe(18)
    async with runtime.database.transaction() as cur:
        await cur.execute('auth.account_exists', (email,))
        if await cur.fetchone():
            raise ApplicationError(409, 'Este correo ya está registrado')
        await cur.execute('auth.create_tutor', (
            data.nombre.strip(), email,
            runtime.services.hash_password(password),
        ))
    return {'mensaje': 'Tutor creado', 'email': email,
            'password_temporal': password}


async def listar_tutores(user, *, runtime):
    # Solo devuelve las cuentas académicas autorizadas.
    async with runtime.database.read() as cur:
        await cur.execute('auth.list_tutors')
        return [{**dict(row), 'roles': active_roles(row['roles'])}
                for row in await cur.fetchall()]


async def eliminar_tutor(user_id, coordinator, *, runtime):
    # Impide borrar alumnos o coordinadores desde este flujo.
    async with runtime.database.transaction() as cur:
        await cur.execute('auth.delete_tutor', (user_id,))
        if not await cur.fetchone():
            raise ApplicationError(404, 'Tutor no encontrado')
    return {'mensaje': 'Tutor dado de baja'}


async def reset_password_alumno(matricula, tutor, *, runtime):
    # La clave se entrega manualmente, sin enviarla por correo.
    password = secrets.token_urlsafe(18)
    async with runtime.database.transaction() as cur:
        await cur.execute('auth.student_for_reset', (matricula,))
        student = await cur.fetchone()
        if not student:
            raise ApplicationError(404, 'No existe una cuenta Dual autorizada')
        await cur.execute('auth.password_temp', (
            runtime.services.hash_password(password), student['id']
        ))
    return {'mensaje': 'Contraseña provisional generada',
            'matricula': matricula, 'password_temporal': password}
