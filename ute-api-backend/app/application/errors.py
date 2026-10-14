from dataclasses import dataclass
from typing import Any
from typing import Any


@dataclass
class ApplicationError(Exception):
    status_code: int
    detail: Any

    # Conserva un error de negocio independiente del framework web.
    def __str__(self) -> str:
        return str(self.detail)
