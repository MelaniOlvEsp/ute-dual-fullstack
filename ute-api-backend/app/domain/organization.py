from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Career:
    code: str
    name: str


# Catálogo institucional cerrado. La nomenclatura conserva la fórmula heredada
# de la base: plan+código-zona-modalidad-grado+letra.
CAREERS = (
    Career("TII", "ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL"),
    Career("LOG", "ING. NME LOGISTICA"),
    Career("MER", "LIC. NME MERCADOTECNIA"),
)
CAREER_BY_NAME = {career.name: career for career in CAREERS}
CAREER_BY_CODE = {career.code: career for career in CAREERS}


def canonical_career(value: str) -> Career:
    normalized = value.strip().upper()
    career = CAREER_BY_CODE.get(normalized) or CAREER_BY_NAME.get(value.strip())
    if not career:
        raise ValueError("La carrera debe ser TII, LOG o MER")
    return career

