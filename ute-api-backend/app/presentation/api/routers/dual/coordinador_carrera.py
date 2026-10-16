
from fastapi import APIRouter, HTTPException, status, Depends
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from fastapi import UploadFile, File, Form
from app.presentation.api.routers.auth import get_current_user
from app.application.dto.reportes import ReporteDualResponse
from app.application.use_cases.dual import coordinador_carrera as use_cases
from app.application.use_cases.dual import organization as organization_cases
from app.domain.organization import canonical_career
from app.bootstrap import get_runtime
from app.presentation.api.response import to_http_response


router = APIRouter()
CAMPOS_CSV = ["semana", "calificacion_alumno"]


def get_coordinador_carrera(user=Depends(get_current_user)):
    # Tutor y coordinador pueden consultar expedientes.
    roles = user.get('roles', {})
    if not (roles.get('tutor_academico') or roles.get('coordinador_dual')):
        raise HTTPException(403, detail='Acceso restringido')
    return user


def get_tutor_academico(user=Depends(get_coordinador_carrera)):
    # La edición de expedientes está reservada al tutor.
    if not user.get('roles', {}).get('tutor_academico'):
        raise HTTPException(403, detail='Solo un tutor académico puede editar')
    return user


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/periodos")
async def listar_periodos(user=Depends(get_coordinador_carrera)):
    return to_http_response(
        await use_cases.listar_periodos(
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/alumnos")
async def listar_alumnos(
    cuatrimestre: str | None = None,
    grupo: str | None = None,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await use_cases.listar_alumnos(
            cuatrimestre=cuatrimestre,
            grupo=grupo,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get(
    "/alumnos/{matricula}/reportes", response_model=list[ReporteDualResponse]
)
# Devuelve el expediente completo (datos y reportes) de un alumno dual
async def expediente_alumno(
    matricula: str,
    cuatrimestre: str | None = None,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await use_cases.expediente_alumno(
            matricula=matricula,
            cuatrimestre=cuatrimestre,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/reporte/{reporte_id}/pdf")
async def descargar_reporte_pdf_carrera(
    reporte_id: UUID,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await use_cases.descargar_reporte_pdf_carrera(
            reporte_id=reporte_id,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/alumnos/{matricula}/exportar-csv")
async def exportar_csv(
    matricula: str,
    cuatrimestre: str | None = None,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await use_cases.exportar_csv(
            matricula=matricula,
            cuatrimestre=cuatrimestre,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/alumnos/{matricula}/exportar-zip")
async def exportar_zip(
    matricula: str,
    cuatrimestre: str | None = None,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await use_cases.exportar_zip(
            matricula=matricula,
            cuatrimestre=cuatrimestre,
            user=user,
            runtime=get_runtime(),
        )
    )


class GrupoCreate(BaseModel):
    carrera: str
    cuatrimestre: int = Field(ge=1, le=12)
    modalidad: str
    letra: str = Field(max_length=1)
    turno: str
    plan: str = "24"
    zona: int = 1

    @field_validator("carrera")
    @classmethod
    def carrera_institucional(cls, value):
        try:
            return canonical_career(value).name
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


@router.get("/carreras")
async def listar_carreras(user=Depends(get_coordinador_carrera)):
    return to_http_response(
        await organization_cases.list_careers(user=user, runtime=get_runtime())
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.get("/grupos")
async def listar_grupos(
    carrera: str | None = None, user=Depends(get_tutor_academico)
):
    return to_http_response(
        await use_cases.listar_grupos(
            carrera=carrera,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/grupos", status_code=status.HTTP_201_CREATED)
async def crear_grupo(
    data: GrupoCreate, user=Depends(get_tutor_academico)
):
    return to_http_response(
        await use_cases.crear_grupo(
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post("/grupos/{grupo_id}/alumnos")
async def cargar_alumnos_csv(
    grupo_id: UUID,
    periodo_id: UUID = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_tutor_academico),
):
    return to_http_response(
        await organization_cases.apply_csv(
            group_id=grupo_id,
            period_id=periodo_id,
            file=file,
            user=user,
            runtime=get_runtime(),
        )
    )


class AlumnoIndividualCreate(BaseModel):
    matricula: str = Field(min_length=9, max_length=9)
    nombre: str
    periodo_id: UUID


@router.post("/grupos/{grupo_id}/alumnos/preview")
async def preview_alumnos_csv(
    grupo_id: UUID,
    periodo_id: UUID = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_tutor_academico),
):
    return to_http_response(
        await organization_cases.preview_csv(
            group_id=grupo_id,
            period_id=periodo_id,
            file=file,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.post(
    "/grupos/{grupo_id}/alumnos/individual",
    status_code=status.HTTP_201_CREATED,
)
# Agrega un alumno individual a un grupo (sin usar CSV)
async def agregar_alumno_individual(
    grupo_id: UUID,
    data: AlumnoIndividualCreate,
    user=Depends(get_tutor_academico),
):
    return to_http_response(
        await organization_cases.add_student(
            group_id=grupo_id,
            data=data,
            user=user,
            runtime=get_runtime(),
        )
    )


@router.get("/alumnos/{matricula}/grupos")
async def historial_grupos(
    matricula: str,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await organization_cases.membership_history(
            matricula=matricula, user=user, runtime=get_runtime()
        )
    )


class PromocionInput(BaseModel):
    grupo_origen_id: UUID
    periodo_origen_id: UUID
    grupo_destino_id: UUID
    periodo_destino_id: UUID
    matriculas: list[str] | None = None


@router.post("/grupos/promociones/preview")
async def preview_promocion(
    data: PromocionInput,
    user=Depends(get_tutor_academico),
):
    return to_http_response(
        await organization_cases.preview_promotion(
            data=data, user=user, runtime=get_runtime()
        )
    )


@router.post("/grupos/promociones")
async def aplicar_promocion(
    data: PromocionInput,
    user=Depends(get_tutor_academico),
):
    return to_http_response(
        await organization_cases.apply_promotion(
            data=data, user=user, runtime=get_runtime()
        )
    )


class AlumnoUpdate(BaseModel):
    nombre: str | None = None


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.patch("/alumnos/{matricula}")
async def actualizar_alumno(
    matricula: str, body: AlumnoUpdate, user=Depends(get_tutor_academico)
):
    return to_http_response(
        await use_cases.actualizar_alumno(
            matricula=matricula,
            body=body,
            user=user,
            runtime=get_runtime(),
        )
    )


# Delega el caso de uso sin mezclar lógica de negocio con HTTP.
@router.delete("/alumnos/{matricula}")
async def eliminar_alumno(
    matricula: str, user=Depends(get_tutor_academico)
):
    return to_http_response(
        await use_cases.eliminar_alumno(
            matricula=matricula,
            user=user,
            runtime=get_runtime(),
        )
    )
