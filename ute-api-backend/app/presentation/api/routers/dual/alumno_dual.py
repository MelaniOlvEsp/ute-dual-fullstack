
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from datetime import date
from app.presentation.api.routers.auth import get_current_user
from app.application.dto.reportes import ReporteDualResponse
from app.application.use_cases.dual import alumno_dual as use_cases
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
@router.post("/", status_code=status.HTTP_201_CREATED)
async def subir_reporte(
    semana: int = Form(...),
    calificacion_alumno: float = Form(...),
    fecha_inicio: date = Form(...),
    fecha_fin: date = Form(...),
    archivo: UploadFile = File(...),
    user=Depends(get_alumno_dual),
):
    return to_http_response(
        await use_cases.subir_reporte(
            semana=semana,
            calificacion_alumno=calificacion_alumno,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            archivo=archivo,
            user=user,
            runtime=get_runtime(),
        )
    )


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


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/semana-actual")
async def obtener_semana_actual(user=Depends(get_alumno_dual)):
    return to_http_response(
        await use_cases.obtener_semana_actual(
            user=user,
            runtime=get_runtime(),
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
