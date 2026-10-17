from typing import Literal
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from app.application.use_cases.dual import plantillas as use_cases
from app.bootstrap import get_runtime
from app.presentation.api.response import to_http_response
from app.presentation.api.routers.auth import get_coordinator, get_current_user


router = APIRouter()


# Metadatos de la versión vigente (cualquier rol autenticado, MP-13).
@router.get("/vigente")
async def plantilla_vigente(user=Depends(get_current_user)):
    return to_http_response(await use_cases.vigente(user=user, runtime=get_runtime()))


# Historial de versiones (solo coordinador, MP-12).
@router.get("/")
async def listar_plantillas(user=Depends(get_coordinator)):
    return to_http_response(await use_cases.listar(user=user, runtime=get_runtime()))


# Publica una pareja Word + PDF nueva; todo o nada (solo coordinador, MP-12, RN-26).
@router.post("/", status_code=status.HTTP_201_CREATED)
async def publicar_plantilla(
    word: UploadFile = File(...),
    pdf: UploadFile = File(...),
    nota: str | None = Form(default=None),
    user=Depends(get_coordinator),
):
    return to_http_response(
        await use_cases.publicar(word=word, pdf=pdf, nota=nota, user=user, runtime=get_runtime()))


# Descarga de un archivo de una versión; cualquier rol autenticado, sin URL pública.
@router.get("/{numero}/{tipo}")
async def descargar_plantilla(numero: int, tipo: Literal["word", "pdf"], user=Depends(get_current_user)):
    return to_http_response(
        await use_cases.descargar(numero=numero, tipo=tipo, user=user, runtime=get_runtime()))