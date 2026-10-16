"""Contratos HTTP de identidad para el portal Dual."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserRoles(BaseModel):
    alumno: bool = False
    tutor_academico: bool = False
    coordinador_dual: bool = False
    model_config = ConfigDict(extra="forbid")


class RegisterSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def solo_correo_institucional(cls, value: str) -> str:
        # El identificador del alumno es su matrícula institucional.
        email = value.strip().lower()
        if not email.endswith("@ute.edu.mx"):
            raise ValueError("Utiliza tu correo institucional @ute.edu.mx")
        return email


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class CambiarPasswordInput(BaseModel):
    password_actual: str
    password_nueva: str


class UsuarioOut(BaseModel):
    id: UUID
    email: str
    roles: UserRoles
    matricula: str | None = None
    must_change_password: bool = False
    nombre: str | None = None
    turno: str | None = None
    grupo_id: UUID | None = None
    nomenclatura: str | None = None
    cuatrimestre: int | None = None
    carrera: str | None = None
    modalidad: str | None = None
    empresa: str | None = None
    dual_activo: bool | None = None
    model_config = ConfigDict(from_attributes=True)


class CrearTutorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str
    email: EmailStr
