
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from datetime import date
from app.presentation.api.routers.auth import get_current_user
from app.application.dto.obligaciones import ObligacionOut
from app.application.dto.reportes import ReporteDualResponse
from app.application.use_cases.dual import alumno_dual as use_cases
from app.application.use_cases.dual import entregas as entregas_cases
from app.application.use_cases.dual import obligaciones as obligaciones_cases
from app.bootstrap import get_runtime
from app.presentation.api.response import to_http_response


router = APIRouter()


def get_alumno_dual(user=Depends(get_current_user)):
    roles = user.get("roles", {})
    if not (roles.get("alumno")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido para este rol",
        )
    return user


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/mis-reportes", response_model=list[ReporteDualResponse])
async def mis_reportes(
    cuatrimestre: str | None = None, user=Depends(get_alumno_dual)
):
    return to_http_response(
        await use_cases.mis_reportes(
            cuatrimestre=cuatrimestre,
            user=user,
            runtime=get_runtime(),
        )
    )


@router.get("/obligaciones", response_model=list[ObligacionOut])
async def mis_obligaciones(
    periodo: str | None = None, user=Depends(get_alumno_dual)
):
    return to_http_response(
        await obligaciones_cases.mis_obligaciones(
            matricula=user["matricula"],
            periodo=periodo,
            runtime=get_runtime(),
        )
    )


# C05: entrega o reenvío de una obligación propia (PDF, fechas declaradas y nota entera).
@router.post("/obligaciones/{obligacion_id}/entrega", status_code=status.HTTP_201_CREATED)
async def entregar_obligacion(
    obligacion_id: UUID,
    fecha_inicio: date = Form(...),
    fecha_fin: date = Form(...),
    calificacion_alumno: str = Form(...),
    archivo: UploadFile = File(...),
    user=Depends(get_alumno_dual),
):
    return to_http_response(
        await entregas_cases.entregar(
            obligacion_id=obligacion_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            calificacion=calificacion_alumno,
            archivo=archivo,
            user=user,
            runtime=get_runtime(),
        )
    )


@router.get("/reportes/{reporte_id}/versiones")
async def versiones_reporte(reporte_id: UUID, user=Depends(get_alumno_dual)):
    return to_http_response(
        await entregas_cases.versiones_de_reporte(
            reporte_id=reporte_id, user=user, runtime=get_runtime()
        )
    )


@router.get("/reportes/{reporte_id}/versiones/{numero}/pdf")
async def descargar_version_pdf(
    reporte_id: UUID, numero: int, user=Depends(get_alumno_dual)
):
    return to_http_response(
        await entregas_cases.descargar_version(
            reporte_id=reporte_id, numero=numero, user=user, runtime=get_runtime()
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/reporte/{reporte_id}/pdf")
async def descargar_reporte_pdf_alumno(
    reporte_id: UUID,
    user=Depends(get_alumno_dual),
):
    return to_http_response(
        await use_cases.descargar_reporte_pdf_alumno(
            reporte_id=reporte_id,
            user=user,
            runtime=get_runtime(),
        )
    )
