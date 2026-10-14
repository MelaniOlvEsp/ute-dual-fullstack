from typing import Protocol


class FileUpload(Protocol):
    filename: str | None

    # Devuelve los bytes de un archivo recibido por el adaptador HTTP.
    async def read(self, size: int = -1) -> bytes:
        ...
