from __future__ import annotations

from uuid import UUID
from loguru import logger
from typing_extensions import Literal
from app.application.dto.foro import BuzonMensajeCreate, BuzonRespuestaCreate
from app.application.ports.runtime import RuntimePort
from app.application.errors import ApplicationError
from app.application.ports.query import QueryRef
from app.application.responses import FileResult


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
def _rol_label(roles: dict) -> str:
    roles = roles or {}
    if roles.get("tutor_academico"):
        return "Tutor académico"
    if roles.get("coordinador_dual"):
        return "Coordinación Dual"
    if roles.get("alumno"):
        return "Alumno"
    return "Personal UTE"


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
def _puede_leer_area(roles: dict, area: str) -> bool:
    roles = roles or {}
    if roles.get("tutor_academico"):
        return True
    if area == "dual" and (roles.get("coordinador_dual") or roles.get("tutor_academico")):
        return True
    return False


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def _obtener_mensaje(cur, mensaje_id: UUID) -> dict:
    await cur.execute(
        'foro.buzon.q000',
        (mensaje_id,),
    )
    row = await cur.fetchone()
    if not row:
        raise ApplicationError(
            status_code=404,
            detail="Mensaje no encontrado",
        )
    return dict(row)


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
def _puede_participar(roles: dict, msg: dict, user_id) -> bool:
    es_dueno = str(msg["alumno_id"]) == str(user_id)
    return msg["area"] == "dual" and (
        es_dueno or _puede_leer_area(roles, msg["area"])
    )


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def enviar_mensaje(data, user, *, runtime: RuntimePort):
    if data.area != "dual":
        raise ApplicationError(status_code=422, detail="Área no disponible")
    async with runtime.database.transaction() as cur:
        await cur.execute(
            'foro.buzon.q001',
            (
                user["id"],
                user.get("matricula"),
                user["sub"],
                data.area,
                data.asunto,
                data.mensaje,
            ),
        )
        nuevo = dict(await cur.fetchone())

    logger.info(
        f"Mensaje de buzón ({data.area}) enviado por {user['sub']}"
    )
    return nuevo


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_mensajes(area, user, *, runtime: RuntimePort):
    if area != "dual":
        raise ApplicationError(status_code=422, detail="Área no disponible")
    roles = user.get("roles", {}) or {}
    if not _puede_leer_area(roles, area):
        raise ApplicationError(
            status_code=403,
            detail="Acceso restringido para este rol",
        )

    async with runtime.database.read() as cur:
        await cur.execute(
            'foro.buzon.q002',
            (area,),
        )
        return [dict(r) for r in await cur.fetchall()]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_mios(user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        await cur.execute(
            'foro.buzon.q003',
            (user["id"],),
        )
        return [dict(r) for r in await cur.fetchall()]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def obtener_mensaje(mensaje_id, user, *, runtime: RuntimePort):
    roles = user.get("roles", {}) or {}
    async with runtime.database.read() as cur:
        await cur.execute(
            'foro.buzon.q004',
            (mensaje_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=404,
                detail="Mensaje no encontrado",
            )
        detalle = dict(row)

        msg_acceso = await _obtener_mensaje(cur, mensaje_id)
        if not _puede_participar(roles, msg_acceso, user["id"]):
            raise ApplicationError(
                status_code=404,
                detail="Mensaje no encontrado",
            )

        await cur.execute(
            'foro.buzon.q005',
            (mensaje_id,),
        )
        detalle["respuestas"] = [dict(r) for r in await cur.fetchall()]

    return detalle


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def responder_mensaje(mensaje_id, data, user, *, runtime: RuntimePort):
    roles = user.get("roles", {}) or {}
    async with runtime.database.transaction() as cur:
        msg = await _obtener_mensaje(cur, mensaje_id)
        if not _puede_participar(roles, msg, user["id"]):
            raise ApplicationError(
                status_code=404,
                detail="Mensaje no encontrado",
            )

        await cur.execute(
            'foro.buzon.q006',
            (mensaje_id, user["id"], _rol_label(roles), data.texto),
        )
        respuesta = dict(await cur.fetchone())

        # Si ya estaba cerrado y hay actividad nueva, se reabre a Enviado
        if msg["estado"] == "Cerrado":
            await cur.execute(
                'foro.buzon.q007',
                (mensaje_id,),
            )

    logger.info(f"Respuesta en mensaje {mensaje_id} por {user['sub']}")
    return respuesta


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def marcar_leido(mensaje_id, user, *, runtime: RuntimePort):
    roles = user.get("roles", {}) or {}
    async with runtime.database.transaction() as cur:
        msg = await _obtener_mensaje(cur, mensaje_id)
        if not _puede_leer_area(roles, msg["area"]):
            raise ApplicationError(
                status_code=403,
                detail="Acceso restringido para este rol",
            )

        await cur.execute(
            'foro.buzon.q008',
            (mensaje_id,),
        )

    return {"mensaje": "Marcado como leído"}


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def cerrar_mensaje(mensaje_id, user, *, runtime: RuntimePort):
    roles = user.get("roles", {}) or {}
    if not _puede_leer_area(roles, "dual"):
        raise ApplicationError(403, "Solo el personal puede cerrar mensajes")
    async with runtime.database.transaction() as cur:
        msg = await _obtener_mensaje(cur, mensaje_id)
        if not _puede_participar(roles, msg, user["id"]):
            raise ApplicationError(
                status_code=404,
                detail="Mensaje no encontrado",
            )

        await cur.execute(
            'foro.buzon.q009',
            (user["id"], mensaje_id),
        )

    return {"mensaje": "Mensaje cerrado"}
