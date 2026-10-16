# app/modulos/dual/schemas/reporte_schemas.py
from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from typing_extensions import Literal

from app.domain.calendar import hoy as _hoy
from app.domain.periods import validar_periodo as _validar_periodo


# Base: Lo que comparten los reportes
class ReporteDualBase(BaseModel):
    cuatrimestre: str
    # Ordinal continuo de la obligación (C04/C05): sin techo de 18 semanas (RN-07).
    semana: int = Field(
        ..., ge=1, description="Ordinal de la semana de la incorporación"
    )
    calificacion_alumno: float = Field(..., ge=1, le=10)
    archivo_pdf_url: Optional[str] = None


# Alumno: Datos que el alumno puede actualizar de su perfil
class PerfilDualUpdate(BaseModel):
    carrera: str
    grupo: str


# Create: Cuando el alumno sube el reporte
class ReporteDualCreate(ReporteDualBase):
    matricula: str


# C06: decisión del tutor sobre una versión. La nota corregida es un entero (sin decimales ni
# booleanos); la validación de rango y de fechas es de dominio (`app.domain.reviews`).
class RevisionIn(BaseModel):
    decision: Literal['Aprobada', 'Rechazada']
    observacion: Optional[str] = None
    calificacion: Optional[StrictInt] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


# Respuesta completa de un reporte dual incluyendo metadatos de BD
class ReporteDualResponse(ReporteDualBase):
    id: UUID
    matricula: str
    estado: str
    nota_agente: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    created_at: datetime
    updated_at: datetime


# Empresa
class EmpresaCreate(BaseModel):
    nombre: str


class EmpresaOut(BaseModel):
    id: UUID
    nombre: str
    created_at: datetime


# Asignación alumno-empresa
class AsignacionCreate(BaseModel):
    matricula: str
    empresa_id: UUID
    fecha_inicio: date


class AsignacionOut(BaseModel):
    id: UUID
    matricula: str
    cuatrimestre: str | None = None
    empresa_id: UUID
    activo: bool
    fecha_inicio: date
    fecha_baja: date | None = None
    created_at: datetime


class CuatrimestreAbrir(BaseModel):
    periodo_label: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Etiqueta legible del periodo, ej. Septiembre–Diciembre "
        "2026",
    )
    fecha_inicio: date
    fecha_fin: date

    # Valida los periodos permitidos para cada cuatrimestre.
    @field_validator("periodo_label")
    @classmethod
    def validar_periodo_permitido(cls, v: str) -> str:
        error = _validar_periodo(v)
        if error:
            raise ValueError(error)
        return v

    @field_validator("fecha_fin")
    @classmethod
    def fecha_fin_posterior(cls, v: date, info) -> date:
        inicio = info.data.get("fecha_inicio")
        if inicio:
            if v <= inicio:
                raise ValueError(
                    "La fecha de fin debe ser posterior a la fecha de inicio."
                )
            dias = (v - inicio).days
            if dias < 110:  # ~3.7 meses, tolera meses de 28-31 días
                raise ValueError(
                    f"El cuatrimestre debe durar al menos 4 meses. "
                    f"Las fechas dadas solo cubren {dias} días."
                )
        return v

    # El período puede estar en curso (inicio anterior a hoy, p. ej. al arrancar a
    # mitad de cuatrimestre) pero no haber terminado; fecha de hoy en America/Mexico_City.
    @model_validator(mode="after")
    def periodo_no_terminado(self):
        hoy = _hoy()
        if self.fecha_fin < hoy:
            raise ValueError(
                f"El período terminó el {self.fecha_fin} y hoy es {hoy}; "
                "solo se pueden abrir períodos en curso o futuros."
            )
        return self


# Datos requeridos para cerrar formalmente un cuatrimestre activo
class CuatrimestreCerrar(BaseModel):
    periodo_label: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Etiqueta del periodo que se cierra, ej. Mayo–Agosto 2026",
    )

    @field_validator("periodo_label")
    @classmethod
    def validar_periodo_permitido(cls, v: str) -> str:
        error = _validar_periodo(v)
        if error:
            raise ValueError(error)
        return v


# Estado actual del ciclo dual: abierto, cerrado o sin ciclo configurado
class CuatrimestreActualOut(BaseModel):
    cuatrimestre: Optional[str] = None
    periodo_label: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    abierto: bool = False
    cerrado: bool = False
    cerrado_at: Optional[datetime] = None
