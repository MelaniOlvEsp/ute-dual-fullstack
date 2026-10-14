from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileResult:
    content: Any
    media_type: str
    headers: dict[str, str] = field(default_factory=dict)
