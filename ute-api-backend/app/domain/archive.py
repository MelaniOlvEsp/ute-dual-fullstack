"""Paquete de archivo del expediente (C08). Dominio puro: sin base de datos ni framework.

DP-14: el tutor genera un ZIP por alumno o por carrera y período con la evaluación finalizada; el
alumno descarga solo el suyo durante una semana desde la finalización. Los nombres dentro del ZIP los
produce el servidor, nunca el texto del cliente, y las celdas del CSV se protegen de las fórmulas.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import date, datetime, timedelta

from app.domain import calendar

VENTANA_ALUMNO_DIAS = 7
_PELIGROSAS = ("=", "+", "-", "@", "\t", "\r", "\n")
_NO_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


def ventana_alumno(finalizada_en: datetime | None, ahora: datetime | None = None) -> dict:
    """Disponibilidad del paquete propio del alumno (semana desde la finalización de la evaluación)."""
    if finalizada_en is None:
        return {"disponible": False, "hasta": None,
                "motivo": "El paquete estará disponible cuando se finalice la evaluación del período."}
    ahora = ahora or calendar.ahora()
    limite = finalizada_en + timedelta(days=VENTANA_ALUMNO_DIAS)
    hasta = calendar.hoy(limite)
    if ahora <= limite:
        return {"disponible": True, "hasta": hasta, "motivo": None}
    return {"disponible": False, "hasta": hasta,
            "motivo": f"El paquete estuvo disponible hasta el {hasta.isoformat()}."}


def nombre_seguro(texto, respaldo: str = "sin-nombre") -> str:
    """Segmento de ruta seguro: sin separadores, acentos ni `..`; vacío cae al respaldo."""
    normal = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    limpio = re.sub(r"\.{2,}", ".", _NO_SEGURO.sub("-", normal)).strip("-._")
    return limpio[:80] or respaldo


def ruta_documento_en_paquete(carrera, periodo, grupo, matricula, ordinal, version, tipo) -> str:
    if tipo not in ("firmado", "original"):
        raise ValueError("Tipo de documento inválido")
    return "/".join((
        nombre_seguro(carrera, "carrera"), nombre_seguro(periodo, "periodo"), nombre_seguro(grupo, "sin-grupo"),
        nombre_seguro(matricula, "matricula"),
        f"S{int(ordinal)}-v{int(version)}-{tipo}.pdf"))


def celda_csv_segura(valor) -> str:
    """Protege los valores que una hoja de cálculo interpretaría como fórmula (OWASP CSV Injection)."""
    texto = "" if valor is None else str(valor)
    if texto.startswith(_PELIGROSAS):
        return "'" + texto
    return texto


def construir_csv(encabezados: list[str], filas: list[list]) -> bytes:
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow([celda_csv_segura(h) for h in encabezados])
    for fila in filas:
        escritor.writerow([celda_csv_segura(c) for c in fila])
    return salida.getvalue().encode("utf-8-sig")


def manifiesto_bytes(manifiesto: dict) -> bytes:
    """Serialización estable del manifiesto: el mismo contenido da siempre el mismo hash."""
    return json.dumps(manifiesto, ensure_ascii=False, sort_keys=True, indent=2, default=_json).encode("utf-8")


def sha256_hex(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _json(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)
