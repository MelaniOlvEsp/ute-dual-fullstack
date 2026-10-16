"""Reglas de revisión de reportes semanales (C06). Dominio puro.

RN-14: el rechazo exige observación. RN-15: el tutor puede corregir fechas y nota conservando el
valor previo y el nuevo; la corrección nunca mueve la obligación ni el período (DP-02, DP-01).
"""
from __future__ import annotations

from datetime import date

from app.domain import reports

DECISIONES = ("Aprobada", "Rechazada")
OBSERVACION_MAX = 1000


class RevisionInvalida(ValueError):
    """Dato de revisión rechazado con un mensaje claro para el tutor."""


def validar_decision(decision, observacion):
    """Devuelve la observación limpia (o None); el rechazo la exige."""
    if decision not in DECISIONES:
        raise RevisionInvalida("La decisión debe ser Aprobada o Rechazada.")
    texto = (observacion or "").strip() or None
    if texto and len(texto) > OBSERVACION_MAX:
        raise RevisionInvalida(f"La observación no puede pasar de {OBSERVACION_MAX} caracteres.")
    if decision == "Rechazada" and not texto:
        raise RevisionInvalida("Escribe la observación del rechazo para que el alumno sepa qué corregir.")
    return texto


def valores_validados(version, nota=None, fecha_inicio=None, fecha_fin=None):
    """Valores que quedan tras la revisión: los corregidos o, si no se envían, los declarados.

    Devuelve (nota, inicio, fin). La nota debe ser entera 1–10 y inicio ≤ fin, igual que en la
    entrega; la correspondencia con la semana la juzga el tutor y no se impone aquí (DP-12).
    """
    try:
        valida = reports.parse_nota(nota) if nota is not None else version["nota"]
        inicio = fecha_inicio if fecha_inicio is not None else version["fecha_inicio"]
        fin = fecha_fin if fecha_fin is not None else version["fecha_fin"]
        reports.validar_fechas(inicio, fin)
    except reports.EntregaInvalida as exc:
        raise RevisionInvalida(str(exc)) from exc
    return valida, inicio, fin


def correcciones(version, nota, inicio, fin):
    """Lista (campo, valor previo, valor nuevo) de lo que el tutor cambió respecto de lo declarado."""
    cambios = []
    for campo, previo, nuevo in (
        ("fecha_inicio", version["fecha_inicio"], inicio),
        ("fecha_fin", version["fecha_fin"], fin),
        ("nota", version["nota"], nota),
    ):
        if previo != nuevo:
            cambios.append((campo, _texto(previo), _texto(nuevo)))
    return cambios


def _texto(valor):
    return valor.isoformat() if isinstance(valor, date) else str(valor)
