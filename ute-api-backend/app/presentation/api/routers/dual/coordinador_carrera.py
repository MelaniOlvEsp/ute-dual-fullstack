
from typing import Literal
from fastapi import APIRouter, HTTPException, status, Depends
from uuid import UUID
from pydantic import BaseModel, Field, StrictBool, field_validator
from fastapi import UploadFile, File, Form
from app.presentation.api.routers.auth import get_current_user
from app.application.use_cases.dual import coordinador_carrera as use_cases
from app.application.use_cases.dual import organization as organization_cases
from app.application.use_cases.dual import expediente as expediente_cases
from app.application.use_cases.dual import paquetes as paquetes_cases
from app.application.use_cases.dual import purgas as purgas_cases
from app.domain.organization import canonical_career
from app.bootstrap import get_runtime
from app.presentation.api.response import to_http_response


router = APIRouter()


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


# C08: directorio paginado por servidor; incluye a los dados de baja (RN-29) y filtra por período,
# grupo, situación y búsqueda.
@router.get("/alumnos")
async def listar_alumnos(
    cuatrimestre: str | None = None,
    grupo: str | None = None,
    q: str | None = None,
    situacion: str = "todos",
    limite: int = 50,
    desplazamiento: int = 0,
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await expediente_cases.directorio(
            cuatrimestre=cuatrimestre, grupo=grupo, busqueda=q, situacion=situacion,
            limite=limite, desplazamiento=desplazamiento, user=user, runtime=get_runtime(),
        )
    )


# Expediente por período del alumno para el personal (tutor y coordinador, las tres carreras; MP-10).
@router.get("/alumnos/{matricula}/expediente")
async def expediente_alumno(matricula: str, user=Depends(get_coordinador_carrera)):
    return to_http_response(
        await expediente_cases.expediente(matricula=matricula, user=user, runtime=get_runtime())
    )


# Original o firmado de un reporte aprobado, por documento versionado; una versión no aprobada es 404.
@router.get("/reportes/{reporte_id}/versiones/{numero}/pdf")
async def descargar_aprobado_pdf(
    reporte_id: UUID,
    numero: int,
    documento: Literal["original", "firmado"] = "firmado",
    user=Depends(get_coordinador_carrera),
):
    return to_http_response(
        await expediente_cases.descargar_aprobado(
            reporte_id=reporte_id, numero=numero, documento=documento, user=user, runtime=get_runtime(),
        )
    )


# Paquete de archivo (ZIP) por alumno o por carrera y período finalizado; solo el tutor (DP-14).
@router.get("/paquetes/alumno/{matricula}")
async def paquete_alumno(matricula: str, periodo_id: UUID, user=Depends(get_tutor_academico)):
    return to_http_response(
        await paquetes_cases.paquete_de_alumno(
            matricula=matricula, periodo_id=periodo_id, user=user, runtime=get_runtime())
    )


@router.get("/paquetes/carrera/{codigo}")
async def paquete_carrera(codigo: str, periodo_id: UUID, user=Depends(get_tutor_academico)):
    return to_http_response(
        await paquetes_cases.paquete_de_carrera(
            codigo=codigo, periodo_id=periodo_id, user=user, runtime=get_runtime())
    )


# C08B: depuración de los archivos de un período (tutor y coordinador, D2). Elimina solo los PDF, con
# gracia de 7 días y cancelación; el alumno no tiene acceso.
class PurgaCreate(BaseModel):
    carrera: str | None = Field(default=None, max_length=10)
    matricula: str | None = Field(default=None, max_length=30)
    confirmar: StrictBool
    frase: str = Field(max_length=200)


@router.get("/periodos/{periodo_id}/archivo")
async def archivo_periodo(periodo_id: UUID, user=Depends(get_coordinador_carrera)):
    return to_http_response(await purgas_cases.resumen(periodo_id=periodo_id, user=user, runtime=get_runtime()))


@router.post("/periodos/{periodo_id}/purgas")
async def programar_purga(periodo_id: UUID, body: PurgaCreate, user=Depends(get_coordinador_carrera)):
    return to_http_response(
        await purgas_cases.programar(
            periodo_id=periodo_id, carrera=body.carrera, matricula=body.matricula, confirmar=body.confirmar,
            frase=body.frase, user=user, runtime=get_runtime()))


@router.post("/periodos/{periodo_id}/purgas/{purga_id}/cancelacion")
async def cancelar_purga(periodo_id: UUID, purga_id: UUID, user=Depends(get_coordinador_carrera)):
    return to_http_response(
        await purgas_cases.cancelar(periodo_id=periodo_id, purga_id=purga_id, user=user, runtime=get_runtime()))


@router.post("/periodos/{periodo_id}/purgas/{purga_id}/ejecucion")
async def ejecutar_purga(periodo_id: UUID, purga_id: UUID, user=Depends(get_coordinador_carrera)):
    return to_http_response(
        await purgas_cases.ejecutar_manual(periodo_id=periodo_id, purga_id=purga_id, user=user, runtime=get_runtime()))


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
