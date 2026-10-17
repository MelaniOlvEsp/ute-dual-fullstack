from __future__ import annotations

from uuid import UUID
from loguru import logger
from app.application.dto.foro import PublicacionCreate, ReaccionInput
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
    if roles.get("tutor_academico"):
        return "Tutor académico"
    return "Personal UTE"


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def crear_publicacion(data, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        # Se consulta el nombre real en BD porque el token no siempre trae
        # el nombre de cuentas de personal (queda vacio al hacer login).
        await cur.execute(
            'foro.publicaciones.q000', (user["id"],)
        )
        row = await cur.fetchone()
        info = dict(row) if row else {}
        autor_nombre = info.get("nombre") or user.get("sub")
        autor_rol = _rol_label(info.get("roles") or user.get("roles"))

        await cur.execute(
            'foro.publicaciones.q001',
            (user["id"], autor_nombre, autor_rol, data.contenido),
        )
        nueva = dict(await cur.fetchone())

    logger.info(f"Publicación de foro creada por {user['sub']}")
    nueva["reacciones"] = {}
    nueva["total_reacciones"] = 0
    nueva["mi_reaccion"] = None
    return nueva


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_publicaciones(limit, user, *, runtime: RuntimePort):
    limit = max(1, min(limit, 100))
    async with runtime.database.read() as cur:
        await cur.execute(
            'foro.publicaciones.q002',
            (limit,),
        )
        posts = [dict(r) for r in await cur.fetchall()]
        if not posts:
            return []

        ids = [p["id"] for p in posts]

        await cur.execute(
            'foro.publicaciones.q003',
            (ids,),
        )
        conteos: dict[str, dict[str, int]] = {}
        for r in await cur.fetchall():
            r = dict(r)
            pid = str(r["publicacion_id"])
            conteos.setdefault(pid, {})[r["tipo"]] = r["total"]

        await cur.execute(
            'foro.publicaciones.q004',
            (ids, user["id"]),
        )
        mias = {
            str(dict(r)["publicacion_id"]): dict(r)["tipo"]
            for r in await cur.fetchall()
        }

        for p in posts:
            pid = str(p["id"])
            p["reacciones"] = conteos.get(pid, {})
            p["total_reacciones"] = sum(p["reacciones"].values())
            p["mi_reaccion"] = mias.get(pid)

        return posts


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def eliminar_publicacion(publicacion_id, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        await cur.execute(
            'foro.publicaciones.q005',
            (publicacion_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=404,
                detail="Publicación no encontrada",
            )

        # C09 (D2): el autor elimina lo suyo y el coordinador puede moderar cualquier anuncio.
        autor_id = dict(row)["autor_id"]
        es_moderador = bool((user.get("roles") or {}).get("coordinador_dual"))
        if str(autor_id) != str(user["id"]) and not es_moderador:
            raise ApplicationError(
                status_code=403,
                detail="Solo el autor o el coordinador pueden eliminar este anuncio",
            )

        # Eliminación lógica: el anuncio se conserva con quién y cuándo lo eliminó y deja de mostrarse.
        await cur.execute(
            'foro.publicaciones.q006', (user["id"], publicacion_id)
        )

    logger.info(f"Anuncio {publicacion_id} eliminado por {user['sub']}")
    return {"mensaje": "Publicación eliminada"}


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def reaccionar(publicacion_id, data, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        await cur.execute(
            'foro.publicaciones.q007',
            (publicacion_id,),
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Publicación no encontrada",
            )

        await cur.execute(
            'foro.publicaciones.q008',
            (publicacion_id, user["id"]),
        )
        existente = await cur.fetchone()

        if existente and dict(existente)["tipo"] == data.tipo:
            await cur.execute(
                'foro.publicaciones.q009',
                (publicacion_id, user["id"]),
            )
            return {"mensaje": "Reacción removida", "mi_reaccion": None}

        await cur.execute(
            'foro.publicaciones.q010',
            (publicacion_id, user["id"], data.tipo),
        )

    return {"mensaje": "Reacción registrada", "mi_reaccion": data.tipo}
