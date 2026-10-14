# app/core/db/database.py
from contextlib import asynccontextmanager

import psycopg_pool
from psycopg.rows import dict_row
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.infrastructure.config.settings import settings

pool: psycopg_pool.AsyncConnectionPool | None = None


# Abre el pool con reintento por si la BD (Render) tarda en despertar
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    before_sleep=before_sleep_log(logger, "WARNING"),
    reraise=True,
)
async def init_pool() -> None:
    global pool
    logger.info("Inicializando pool de conexiones a PostgreSQL...")

    pool = psycopg_pool.AsyncConnectionPool(
        conninfo=settings.db.db_dsn,
        min_size=settings.db.min_size,
        max_size=settings.db.max_size,
        timeout=settings.db.timeout_conn,
        max_idle=30,
        max_lifetime=1800,
        kwargs={
            "row_factory": dict_row,
            "application_name": settings.db.appname,
            "connect_timeout": settings.db.timeout_conn,
        },
        open=False,
    )

    try:
        await pool.open(wait=True, timeout=settings.db.timeout_conn)
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
    except Exception:
        await pool.close()
        pool = None
        raise
    logger.success("Pool de conexiones listo.")


# Cierra el pool de conexiones de forma segura al apagar el servidor
async def close_pool() -> None:
    if pool:
        logger.info("Cerrando pool de conexiones...")
        await pool.close()
        logger.success("Pool cerrado.")


# Proporciona un cursor de BD con row_factory dict_row. Libera al salir del
# contexto
@asynccontextmanager
async def get_cursor():
    assert pool is not None, "El pool no está inicializado"

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            yield cur


@asynccontextmanager
async def get_transaction():
    # cursor dentro de una transaccion. Commit al salir, rollback si hay error.
    # usar para operaciones multi-statement atomicas (folio + INSERT, DELETEs,
    # etc.)
    assert pool is not None, "El pool no está inicializado"

    async with pool.connection() as conn:
        await conn.set_autocommit(False)
        async with conn.cursor(row_factory=dict_row) as cur:
            try:
                yield cur
            except Exception:
                await conn.rollback()
                raise
            else:
                await conn.commit()


# Proporciona una conexion directa al pool sin cursor. Para operaciones
# avanzadas
@asynccontextmanager
async def get_conn():
    assert pool is not None, "El pool no está inicializado"

    async with pool.connection() as conn:
        yield conn
