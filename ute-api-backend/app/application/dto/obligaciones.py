from datetime import date
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class ObligacionOut(BaseModel):
    """Semana lunes-domingo de una incorporación. El período se resuelve por el domingo."""
    id: UUID
    incorporacion_id: UUID
    ordinal: int
    semana_inicio: date
    semana_fin: date
    inicio_efectivo: date
    fin_efectivo: date
    parcial: bool
    periodo: Optional[str] = None
    periodo_label: Optional[str] = None
    empresa: Optional[str] = None
    estado: Literal["PENDIENTE", "ATRASADA", "RECIBIDA"]
    # C05: entrega real ligada a la obligación.
    reporte_id: Optional[UUID] = None
    entrega: Optional[Literal["Pendiente", "Aprobada", "Rechazada"]] = None
    version: Optional[int] = None
    observacion: Optional[str] = None
    puede_entregar: bool = False
    motivo_bloqueo: Optional[str] = None
