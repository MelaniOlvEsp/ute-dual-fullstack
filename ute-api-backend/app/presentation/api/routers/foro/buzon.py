
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from typing_extensions import Literal
from app.presentation.api.routers.auth import get_current_user
from app.application.dto.foro import BuzonMensajeCreate, BuzonRespuestaCreate
from app.application.use_cases.foro import buzon as use_cases
from app.bootstrap import get_runtime
from app.presentation.api.response import to_http_response


router = APIRouter()


def get_remitente(user=Depends(get_current_user)):
    roles = user.get("roles", {}) or {}
    if not roles.get("alumno"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los alumnos pueden enviar mensajes al buzón.",
        )
    return user


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/", status_code=status.HTTP_201_CREATED)
async def enviar_mensaje(
    data: BuzonMensajeCreate, user=Depends(get_remitente)
):
    return to_http_response(
        await use_cases.enviar_mensaje(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/")
async def listar_mensajes(
    area: Literal["dual"], user=Depends(get_current_user)
):
    return to_http_response(
        await use_cases.listar_mensajes(
            area=area,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/mios")
async def listar_mios(user=Depends(get_remitente)):
    return to_http_response(
        await use_cases.listar_mios(
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/{mensaje_id}")
async def obtener_mensaje(mensaje_id: UUID, user=Depends(get_current_user)):
    return to_http_response(
        await use_cases.obtener_mensaje(
            mensaje_id=mensaje_id,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/{mensaje_id}/respuestas", status_code=status.HTTP_201_CREATED)
async def responder_mensaje(
    mensaje_id: UUID,
    data: BuzonRespuestaCreate,
    user=Depends(get_current_user),
):
    return to_http_response(
        await use_cases.responder_mensaje(
            mensaje_id=mensaje_id,
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.patch("/{mensaje_id}/leido")
async def marcar_leido(mensaje_id: UUID, user=Depends(get_current_user)):
    return to_http_response(
        await use_cases.marcar_leido(
            mensaje_id=mensaje_id,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.patch("/{mensaje_id}/cerrar")
async def cerrar_mensaje(mensaje_id: UUID, user=Depends(get_current_user)):
    return to_http_response(
        await use_cases.cerrar_mensaje(
            mensaje_id=mensaje_id,
            user=user,
            runtime=get_runtime(),
        )
    )

# C09 (D1): reapertura explícita del hilo cerrado, solo personal.
@router.patch("/{mensaje_id}/reabrir")
async def reabrir_mensaje(mensaje_id: UUID, user=Depends(get_current_user)):
    return to_http_response(
        await use_cases.reabrir_mensaje(
            mensaje_id=mensaje_id,
            user=user,
            runtime=get_runtime(),
        )
    )
