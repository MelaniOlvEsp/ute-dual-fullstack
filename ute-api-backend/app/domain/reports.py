"""Reglas de entrega de reportes semanales (C05). Dominio puro: sin base de datos ni framework.

RN-12: nota entera 1–10 y fechas declaradas con inicio ≤ fin. DP-12: no se exige que el rango
coincida con la semana (lo verifica el tutor) y las fechas nunca reasignan semana ni período.
DP-08: límite único de PDF de 10 MB en cliente y API.
"""
from __future__ import annotations

import re
from datetime import date

MAX_PDF_BYTES = 10 * 1024 * 1024
NOTA_MIN = 1
NOTA_MAX = 10

_ENTERO = re.compile(r"[0-9]{1,2}")


class EntregaInvalida(ValueError):
    """Dato de entrega rechazado con un mensaje claro para el alumno."""


def parse_nota(valor) -> int:
    """Acepta un entero 1–10 como número o como texto de dígitos ASCII; rechaza 8.5, 0 y 11."""
    if isinstance(valor, bool):
        raise EntregaInvalida("La calificación debe ser un número entero entre 1 y 10.")
    if isinstance(valor, int):
        nota = valor
    else:
        texto = str(valor).strip()
        if not _ENTERO.fullmatch(texto):
            raise EntregaInvalida("La calificación debe ser un número entero entre 1 y 10.")
        nota = int(texto)
    if not NOTA_MIN <= nota <= NOTA_MAX:
        raise EntregaInvalida("La calificación debe ser un número entero entre 1 y 10.")
    return nota


def validar_fechas(inicio: date, fin: date) -> None:
    if inicio > fin:
        raise EntregaInvalida("La fecha de inicio debe ser anterior o igual a la de fin.")
