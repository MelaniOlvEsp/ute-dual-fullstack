from fastapi.responses import StreamingResponse

from app.application.responses import FileResult


# Traduce una respuesta de aplicación a una respuesta HTTP cuando corresponde.
def to_http_response(result):
    if isinstance(result, FileResult):
        return StreamingResponse(
            result.content,
            media_type=result.media_type,
            headers=result.headers,
        )
    return result
