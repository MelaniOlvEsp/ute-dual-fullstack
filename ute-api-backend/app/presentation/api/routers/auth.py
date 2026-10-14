"""Endpoints de identidad y acceso con permisos independientes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.application.dto.auth import (
    RegisterSchema, LoginSchema, TokenSchema, UsuarioOut,
    CambiarPasswordInput, CrearTutorInput,
)
from app.application.use_cases import auth as use_cases
from app.bootstrap import get_runtime
from app.domain.roles import has_role
from app.infrastructure.security.jwt_passwords import verificar_token
from app.presentation.middleware.rate_limit import limitar_intentos

router = APIRouter()
bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    # El estado de la cuenta se obtiene de BD en cada solicitud protegida.
    try:
        claims = verificar_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(401, detail=str(exc)) from exc
    try:
        user = await use_cases.security_state(claims, runtime=get_runtime())
    except Exception as exc:
        from app.application.errors import ApplicationError
        if isinstance(exc, ApplicationError):
            raise HTTPException(exc.status_code, detail=exc.detail) from exc
        raise
    if user['must_change_password']:
        raise HTTPException(403, detail='Cambia tu contraseña provisional')
    return user


async def get_change_password_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    # Solo esta operación puede usarse con la contraseña provisional.
    try:
        claims = verificar_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(401, detail=str(exc)) from exc
    from app.application.errors import ApplicationError
    try:
        return await use_cases.security_state(claims, runtime=get_runtime())
    except ApplicationError as exc:
        raise HTTPException(exc.status_code, detail=exc.detail) from exc


async def get_coordinator(user=Depends(get_current_user)):
    # Coordina cuentas de tutores sin acceso a revisar reportes.
    if not has_role(user, 'coordinador_dual'):
        raise HTTPException(403, detail='Acceso solo para Coordinación Dual')
    return user


async def get_tutor(user=Depends(get_current_user)):
    # Solo el tutor administra la recuperación del alumno.
    if not has_role(user, 'tutor_academico'):
        raise HTTPException(403, detail='Acceso solo para tutor académico')
    return user


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(data: RegisterSchema):
    # Registra al alumno previamente cargado por un tutor.
    return await use_cases.register(data, runtime=get_runtime())


@router.post('/login', response_model=TokenSchema)
async def login(
    data: LoginSchema,
    _rl=Depends(limitar_intentos('login', max_intentos=8,
                                ventana_segundos=300)),
):
    # Inicia sesión sin verificación por correo.
    return await use_cases.login(data, _rl, runtime=get_runtime())


@router.get('/me', response_model=UsuarioOut)
async def me(user=Depends(get_current_user)):
    # Devuelve el perfil personal.
    return await use_cases.me(user, runtime=get_runtime())


@router.post('/cambiar-password')
async def cambiar_password(
    data: CambiarPasswordInput, user=Depends(get_change_password_user),
):
    # Actualiza y revoca los tokens emitidos con la contraseña anterior.
    return await use_cases.cambiar_password(data, user,
                                            runtime=get_runtime())


@router.post('/tutores', status_code=201)
async def crear_tutor(data: CrearTutorInput, user=Depends(get_coordinator)):
    # El coordinador registra solo tutores académicos.
    return await use_cases.crear_tutor(data, user, runtime=get_runtime())


@router.get('/tutores')
async def listar_tutores(user=Depends(get_coordinator)):
    # Lista el personal académico.
    return await use_cases.listar_tutores(user, runtime=get_runtime())


@router.delete('/tutores/{usuario_id}')
async def eliminar_tutor(usuario_id: UUID, user=Depends(get_coordinator)):
    # Revoca el acceso de un tutor.
    return await use_cases.eliminar_tutor(usuario_id, user,
                                         runtime=get_runtime())


@router.post('/alumnos/{matricula}/password-provisional')
async def password_provisional(matricula: str, user=Depends(get_tutor)):
    # Restablece la cuenta del alumno; devuelve la clave una sola vez.
    return await use_cases.reset_password_alumno(matricula, user,
                                                 runtime=get_runtime())
