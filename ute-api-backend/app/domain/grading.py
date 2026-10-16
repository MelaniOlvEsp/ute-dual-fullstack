"""Promedio por alumno y período (C07). Dominio puro: sin base de datos ni framework.

RN-21: promedio = suma de notas vigentes aprobadas / cantidad de reportes aprobados del alumno y
período; no entregados, rechazados y pendientes no aportan cero ni entran al denominador.
RN-22 y DP-11: dos decimales con redondeo HALF_UP en el tercero (9.335 → 9.34), nunca a entero; sin
aprobados no hay promedio ("Sin calificación"), no 0.00.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, NamedTuple

NOTA_MIN, NOTA_MAX = 1, 10
_DOS_DECIMALES = Decimal("0.01")
SIN_CALIFICACION = "Sin calificación"


class Resultado(NamedTuple):
    suma: int
    cantidad: int
    promedio: Decimal | None


def promedio_de(suma: int, cantidad: int) -> Decimal | None:
    if cantidad == 0:
        return None
    return (Decimal(suma) / Decimal(cantidad)).quantize(_DOS_DECIMALES, rounding=ROUND_HALF_UP)


def calcular(notas_aprobadas: Iterable[int]) -> Resultado:
    """Resultado de un alumno a partir de las notas enteras de sus reportes aprobados."""
    notas = list(notas_aprobadas)
    for nota in notas:
        if isinstance(nota, bool) or not isinstance(nota, int) or not NOTA_MIN <= nota <= NOTA_MAX:
            raise ValueError(f"Nota fuera de 1–10: {nota!r}")
    return Resultado(sum(notas), len(notas), promedio_de(sum(notas), len(notas)))


def mostrar(promedio: Decimal | None) -> str:
    return SIN_CALIFICACION if promedio is None else f"{promedio:.2f}"
