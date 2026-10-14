
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from app.presentation.api.routers.auth import get_current_user
from app.application.dto.foro import PublicacionCreate, ReaccionInput
from app.application.use_cases.foro import publicaciones as use_cases
from app.bootstrap import get_runtime
from app.presentation.api.response import to_http_response


router = APIRouter()


def get_publicador(user=Depends(get_current_user)):
    roles = user.get("roles", {}) or {}
    if not any(roles.get(role) for role in (
        "tutor_academico", "coordinador_dual"
    )):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el personal autorizado puede publicar en el foro.",
        )
    return user


def get_reactor(user=Depends(get_current_user)):
    roles = user.get("roles", {}) or {}
    if not roles.get("alumno"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los alumnos pueden reaccionar a las publicaciones.",
        )
    return user


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/publicaciones", status_code=status.HTTP_201_CREATED)
async def crear_publicacion(
    data: PublicacionCreate, user=Depends(get_publicador)
):
    return to_http_response(
        await use_cases.crear_publicacion(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/publicaciones")
async def listar_publicaciones(
    limit: int = 50, user=Depends(get_current_user)
):
    return to_http_response(
        await use_cases.listar_publicaciones(
            limit=limit,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.delete("/publicaciones/{publicacion_id}")
async def eliminar_publicacion(
    publicacion_id: UUID, user=Depends(get_publicador)
):
    return to_http_response(
        await use_cases.eliminar_publicacion(
            publicacion_id=publicacion_id,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/publicaciones/{publicacion_id}/reaccion")
async def reaccionar(
    publicacion_id: UUID, data: ReaccionInput, user=Depends(get_reactor)
):
    return to_http_response(
        await use_cases.reaccionar(
            publicacion_id=publicacion_id,
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )
