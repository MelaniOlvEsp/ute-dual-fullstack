import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from psycopg import Error as DatabaseError
from psycopg_pool import PoolTimeout

from app.application.errors import ApplicationError
from app.application.use_cases.dual import purgas as purgas_cases
from app.bootstrap import get_runtime
from app.infrastructure import tareas_purga
from app.infrastructure.storage.registro import estado_cacheado
from app.infrastructure.config.settings import settings
from app.infrastructure.database.postgres import init_pool, close_pool, get_cursor
from app.presentation.middleware.security import (
    SecurityHeadersMiddleware, RateLimitMiddleware,
    generic_error_handler, configure_logging,
)
from app.presentation.api.routers import auth
from app.presentation.api.routers.dual import (
    alumno_dual, coordinador_dual, coordinador_carrera, plantillas,
)
from app.presentation.api.routers.foro import publicaciones, buzon


# Gestiona la vida del pool de PostgreSQL y el monitoreo.
@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.secret_key) < 32:
        raise RuntimeError('Configura SECRET_KEY con al menos 32 caracteres')
    configure_logging(json_format=settings.log_format == 'json')
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0.1,
                environment='production',
            )
        except ImportError:
            logger.warning('Sentry SDK no instalado')
        except Exception as exc:
            logger.warning(f'No se pudo iniciar Sentry: {exc}')
    await init_pool()
    # C08B: ejecuta las depuraciones de archivos cuya gracia venció.
    tarea_purgas = asyncio.create_task(tareas_purga.ciclo(
        purgas_cases.ejecutar_vencidas, get_runtime(), tareas_purga.intervalo_configurado()))
    try:
        yield
    finally:
        tarea_purgas.cancel()
        try:
            await tarea_purgas
        except asyncio.CancelledError:
            pass
        await close_pool()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(',')],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type'],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)


# Traduce los errores previstos de aplicación al contrato HTTP existente.
@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError):
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})


app.add_exception_handler(Exception, generic_error_handler)
app.include_router(auth.router, prefix='/auth', tags=['Auth'])
app.include_router(alumno_dual.router, prefix='/dual/alumno', tags=['Dual - Alumno'])
app.include_router(
    coordinador_dual.router, prefix='/dual/tutor',
    tags=['Dual - Coordinador'],
)
app.include_router(
    coordinador_carrera.router, prefix='/dual/carrera',
    tags=['Dual - Carrera'],
)
app.include_router(plantillas.router, prefix='/dual/plantillas', tags=['Dual - Plantillas'])
app.include_router(publicaciones.router, prefix='/foro', tags=['Foro'])
app.include_router(buzon.router, prefix='/foro/buzon', tags=['Foro - Buzón'])


# Mantiene el health check para monitoreo.
@app.get('/health')
async def health():
    try:
        async with get_cursor() as cur:
            await cur.execute('SELECT 1')
    except (DatabaseError, PoolTimeout):
        return JSONResponse(status_code=503, content={'status': 'database_unavailable'})
    # C10A: el estado del almacenamiento se informa sin secretos y no tumba la API (consulta cacheada).
    return {'status': 'ok', 'app': settings.app_name, 'almacenamiento': estado_cacheado()}
