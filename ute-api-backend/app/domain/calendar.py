"""Calendario semanal de incorporaciones (C04). Dominio puro: sin base de datos ni framework.

Reglas confirmadas: semanas lunes-domingo; la primera semana es parcial desde la fecha real
de inicio; la baja es inclusiva y la última semana es parcial hasta esa fecha; el período de
una semana es el que contiene su domingo (DP-01); "hoy" y el corte del lunes se evalúan en la
zona operativa America/Mexico_City.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ZONA_OPERATIVA = "America/Mexico_City"
_ZONA = ZoneInfo(ZONA_OPERATIVA)

PENDIENTE = "PENDIENTE"
ATRASADA = "ATRASADA"
RECIBIDA = "RECIBIDA"


def ahora() -> datetime:
    return datetime.now(_ZONA)


def hoy(instante: datetime | None = None) -> date:
    """Fecha civil en la zona operativa; rechaza instantes sin zona para no adivinarla."""
    instante = instante or ahora()
    if instante.tzinfo is None:
        raise ValueError("El instante debe incluir zona horaria")
    return instante.astimezone(_ZONA).date()


def lunes_de(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


def domingo_de(fecha: date) -> date:
    return lunes_de(fecha) + timedelta(days=6)


@dataclass(frozen=True)
class Semana:
    ordinal: int
    semana_inicio: date
    semana_fin: date
    inicio_efectivo: date
    fin_efectivo: date
    parcial: bool


def semanas_incorporacion(fecha_inicio: date, fecha_baja: date | None, hasta: date) -> list[Semana]:
    """Obligaciones de una incorporación hasta la semana que contiene `hasta`.

    No genera semanas futuras ni posteriores a la baja. El ordinal es continuo desde el
    inicio de la incorporación; no es identidad (la identidad son las fechas).
    """
    if fecha_baja is not None and fecha_baja < fecha_inicio:
        raise ValueError("La baja no puede ser anterior al inicio")
    limite = min(hasta, fecha_baja) if fecha_baja is not None else hasta
    if limite < fecha_inicio:
        return []
    semanas: list[Semana] = []
    lunes = lunes_de(fecha_inicio)
    ultimo = lunes_de(limite)
    ordinal = 1
    while lunes <= ultimo:
        domingo = lunes + timedelta(days=6)
        inicio = max(fecha_inicio, lunes)
        fin = min(fecha_baja, domingo) if fecha_baja is not None else domingo
        semanas.append(Semana(ordinal, lunes, domingo, inicio, fin,
                              inicio != lunes or fin != domingo))
        lunes += timedelta(days=7)
        ordinal += 1
    return semanas


def estado_obligacion(semana_fin: date, hasta: date, recibida: bool) -> str:
    """Estado derivado: se puede entregar hasta el domingo; desde el lunes es atraso."""
    if recibida:
        return RECIBIDA
    return ATRASADA if hasta > semana_fin else PENDIENTE
