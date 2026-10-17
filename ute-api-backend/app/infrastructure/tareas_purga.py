"""Tarea de fondo de la depuración (C08B, D3): ejecuta las depuraciones cuya gracia venció.

Sin cola ni servicio nuevo: un ciclo asyncio dentro de la API que consulta las purgas vencidas con
bloqueo no bloqueante (`SKIP LOCKED`), de modo que varios procesos no repiten el trabajo.
"""
from __future__ import annotations

import asyncio
import os

from loguru import logger

INTERVALO_POR_OMISION = 60
ARRANQUE_SEGUNDOS = 5


def intervalo_configurado() -> int:
    try:
        return max(5, int(os.environ.get("PURGA_INTERVALO_SEGUNDOS", INTERVALO_POR_OMISION)))
    except ValueError:
        return INTERVALO_POR_OMISION


async def ciclo(ejecutar_vencidas, runtime, intervalo: int, espera_inicial: int = ARRANQUE_SEGUNDOS):
    await asyncio.sleep(espera_inicial)
    while True:
        try:
            ejecutadas = await ejecutar_vencidas(runtime)
            if ejecutadas:
                logger.info("Depuraciones ejecutadas: {}", ejecutadas)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Fallo en el ciclo de depuración: {}", exc)
        await asyncio.sleep(intervalo)
