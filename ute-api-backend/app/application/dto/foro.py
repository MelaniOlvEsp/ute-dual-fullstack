# app/modulos/foro/schemas/foro_schemas.py
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal

# Catalogo de reacciones estilo Facebook que puede usar un alumno
TIPOS_REACCION = ("like", "love", "haha", "wow", "sad", "angry")


# Publicacion: texto plano (con emojis) que crea personal para dar avisos
class PublicacionCreate(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=2000)

    @field_validator("contenido")
    @classmethod
    def limpiar_contenido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El contenido de la publicación no puede estar ",
                             "vacío")
        return v


class PublicacionOut(BaseModel):
    id: UUID
    autor_id: UUID
    autor_nombre: str
    autor_rol: str
    contenido: str
    created_at: datetime
    reacciones: dict[str, int] = Field(default_factory=dict)
    total_reacciones: int = 0
    mi_reaccion: Optional[str] = None


# Reaccion: solo alumnos (dual o normal)
class ReaccionInput(BaseModel):
    tipo: Literal["like", "love", "haha", "wow", "sad", "angry"]


# Buzón: mensaje de un alumno hacia Dual
class BuzonMensajeCreate(BaseModel):
    area: Literal["dual"]
    asunto: str = Field(..., min_length=3, max_length=150)
    mensaje: str = Field(..., min_length=1, max_length=500)
    # C09 (D1): el alumno que necesita seguir un hilo cerrado abre uno nuevo y lo enlaza.
    hilo_anterior_id: Optional[UUID] = None

    @field_validator("asunto", "mensaje")
    @classmethod
    def limpiar_texto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo no puede estar vacío")
        return v


class BuzonMensajeOut(BaseModel):
    id: UUID
    correo: str
    area: str
    asunto: str
    mensaje: str
    estado: Literal["Enviado", "Leido", "Cerrado"]
    created_at: datetime
    hilo_anterior_id: Optional[UUID] = None


# Respuesta dentro del hilo de un mensaje de buzón (alumno o coordinador)
class BuzonRespuestaCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=1000)

    @field_validator("texto")
    @classmethod
    def limpiar_texto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La respuesta no puede estar vacía")
        return v


class BuzonRespuestaOut(BaseModel):
    id: UUID
    mensaje_id: UUID
    autor_id: UUID
    autor_rol: str
    texto: str
    created_at: datetime


# Detalle de un mensaje con su hilo completo de respuestas
class BuzonMensajeDetalle(BuzonMensajeOut):
    respuestas: list[BuzonRespuestaOut] = Field(default_factory=list)
