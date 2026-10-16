
from uuid import UUID
from datetime import date
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from pydantic import BaseModel, model_validator
from app.presentation.api.routers.auth import get_current_user, get_coordinator
from typing import Literal
from app.application.use_cases.dual import revisiones as revisiones_cases
from app.application.dto.reportes import RevisionIn, EmpresaCreate, EmpresaOut, AsignacionCreate, AsignacionOut, CuatrimestreCerrar, CuatrimestreAbrir, CuatrimestreActualOut
from app.application.dto.obligaciones import ObligacionOut
from app.application.use_cases.dual import coordinador_dual as use_cases
from app.application.use_cases.dual import obligaciones as obligaciones_cases
from app.bootstrap import get_runtime
from app.application.use_cases.dual import firmas as firma_cases
from app.presentation.api.response import to_http_response


router = APIRouter()


def get_coordinador_dual(user=Depends(get_current_user)):
    roles = user.get("roles", {})
    if not roles.get("tutor_academico"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido para este rol",
        )
    return user


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/reportes")
async def listar_reportes(
    estado: str | None = None,
    cuatrimestre: str | None = None,
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await use_cases.listar_reportes(
            estado=estado,
            cuatrimestre=cuatrimestre,
            user=user,
            runtime=get_runtime(),
        )
    )


# C06: revisión por versión (tutor). Detalle, decisión y descarga del original o del firmado.
@router.get("/reportes/{reporte_id}")
async def detalle_reporte(reporte_id: UUID, user=Depends(get_coordinador_dual)):
    return to_http_response(
        await revisiones_cases.detalle(reporte_id=reporte_id, user=user, runtime=get_runtime())
    )


@router.post("/reportes/{reporte_id}/versiones/{numero}/revision", status_code=status.HTTP_200_OK)
async def revisar_version(
    reporte_id: UUID,
    numero: int,
    data: RevisionIn,
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await revisiones_cases.revisar(
            reporte_id=reporte_id,
            numero=numero,
            decision=data.decision,
            observacion=data.observacion,
            calificacion=data.calificacion,
            fecha_inicio=data.fecha_inicio,
            fecha_fin=data.fecha_fin,
            user=user,
            runtime=get_runtime(),
        )
    )


@router.get("/reportes/{reporte_id}/versiones/{numero}/pdf")
async def descargar_version_pdf_tutor(
    reporte_id: UUID,
    numero: int,
    documento: Literal["original", "firmado"] = "original",
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await revisiones_cases.descargar(
            reporte_id=reporte_id, numero=numero, documento=documento, user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/empresas", response_model=list[EmpresaOut])
async def listar_empresas(user=Depends(get_coordinador_dual)):
    return to_http_response(
        await use_cases.listar_empresas(
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post(
    "/empresas", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED
)
# Registra una nueva empresa en el catalogo
async def crear_empresa(
    data: EmpresaCreate, user=Depends(get_coordinador_dual)
):
    return to_http_response(
        await use_cases.crear_empresa(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/asignaciones", response_model=list[AsignacionOut])
async def listar_asignaciones(
    cuatrimestre: str | None = None, user=Depends(get_coordinador_dual)
):
    return to_http_response(
        await use_cases.listar_asignaciones(
            cuatrimestre=cuatrimestre,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post(
    "/asignaciones",
    response_model=AsignacionOut,
    status_code=status.HTTP_201_CREATED,
)
# Vincula (o actualiza la vinculacion) de un alumno con una empresa
async def asignar_alumno_empresa(
    data: AsignacionCreate, user=Depends(get_coordinador_dual)
):
    return to_http_response(
        await use_cases.asignar_alumno_empresa(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/alumnos/{matricula}")
async def buscar_alumno(matricula: str, user=Depends(get_coordinador_dual)):
    return to_http_response(
        await use_cases.buscar_alumno(
            matricula=matricula,
            user=user,
            runtime=get_runtime(),
        )
    )


class ActualizarAlumnoDualInput(BaseModel):
    alumno_dual: bool
    empresa_id: UUID | None = None
    fecha_inicio: date | None = None
    fecha_baja: date | None = None

    @model_validator(mode="after")
    @classmethod
    def fechas_requeridas(cls, value):
        if value.alumno_dual and (value.empresa_id is None or value.fecha_inicio is None):
            raise ValueError("Se requieren empresa_id y fecha_inicio al activar alumno dual")
        if not value.alumno_dual and value.fecha_baja is None:
            raise ValueError("Se requiere fecha_baja al terminar la incorporación")
        return value


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.patch("/alumnos/{matricula}")
async def actualizar_alumno_dual(
    matricula: str,
    body: ActualizarAlumnoDualInput,
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await use_cases.actualizar_alumno_dual(
            matricula=matricula,
            body=body,
            user=user,
            runtime=get_runtime(),
        )
    )


@router.get("/alumnos/{matricula}/incorporaciones")
async def historial_incorporaciones(
    matricula: str,
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await use_cases.historial_incorporaciones(
            matricula=matricula, user=user, runtime=get_runtime()
        )
    )


@router.get("/alumnos/{matricula}/obligaciones", response_model=list[ObligacionOut])
async def obligaciones_alumno(
    matricula: str,
    periodo: str | None = None,
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await obligaciones_cases.obligaciones_de_alumno(
            matricula=matricula, periodo=periodo, user=user, runtime=get_runtime()
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/alumnos-sin-reporte")
async def alumnos_sin_reporte(
    cuatrimestre: str, semana: int, user=Depends(get_coordinador_dual)
):
    return to_http_response(
        await use_cases.alumnos_sin_reporte(
            cuatrimestre=cuatrimestre,
            semana=semana,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/alumnos-atrasados")
async def alumnos_atrasados(user=Depends(get_coordinador_dual)):
    return to_http_response(
        await use_cases.alumnos_atrasados(
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/cuatrimestre-actual", response_model=CuatrimestreActualOut)
async def cuatrimestre_actual(user=Depends(get_coordinator)):
    return to_http_response(
        await use_cases.cuatrimestre_actual(
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/abrir-cuatrimestre", status_code=status.HTTP_200_OK)
async def abrir_cuatrimestre(
    data: CuatrimestreAbrir, user=Depends(get_coordinator)
):
    return to_http_response(
        await use_cases.abrir_cuatrimestre(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/cierre", status_code=status.HTTP_200_OK)
async def cerrar_cuatrimestre(
    data: CuatrimestreCerrar, user=Depends(get_coordinator)
):
    return to_http_response(
        await use_cases.cerrar_cuatrimestre(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/reporte/{reporte_id}/pdf")
async def descargar_reporte_pdf_coordinador(
    reporte_id: UUID,
    user=Depends(get_coordinador_dual),
):
    return to_http_response(
        await use_cases.descargar_reporte_pdf_coordinador(
            reporte_id=reporte_id,
            user=user,
            runtime=get_runtime(),
        )
    )


@router.post('/firma')
async def cargar_firma(
    imagen: UploadFile = File(...), user=Depends(get_coordinador_dual),
):
    # La imagen solo puede ser cargada por el tutor titular.
    data = await imagen.read(1024 * 1024 + 1)
    return await firma_cases.subir_firma(user, data,
                                        imagen.content_type or '',
                                        runtime=get_runtime())


@router.get('/firma')
async def consultar_firma(user=Depends(get_coordinador_dual)):
    # Informa si existe una firma, sin divulgar sus bytes.
    return await firma_cases.estado_firma(user, runtime=get_runtime())
