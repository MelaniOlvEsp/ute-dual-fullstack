"""Casos de uso del archivo de firma del tutor académico."""
from app.application.errors import ApplicationError


async def subir_firma(tutor, data: bytes, content_type: str, *, runtime):
    # La firma solo pertenece a la cuenta del tutor autenticado.
    runtime.services.validate_signature(data, content_type)
    async with runtime.database.transaction() as cur:
        await cur.execute('dual.tutor.save_signature', (
            tutor['id'], data, content_type,
        ))
    return {'mensaje': 'Firma guardada correctamente'}


async def estado_firma(tutor, *, runtime):
    # No expone los bytes de la firma a terceros.
    async with runtime.database.read() as cur:
        await cur.execute('dual.tutor.signature_exists', (tutor['id'],))
        row = await cur.fetchone()
    return {'registrada': bool(row)}
