"""Limita el cuerpo CSV antes de multipart, incluso sin Content-Length."""
import re
from starlette.responses import JSONResponse

MAX_CSV_REQUEST = 600 * 1024


class CsvBodyLimitMiddleware:
    def __init__(self, app, limit=MAX_CSV_REQUEST):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or scope['method'] != 'POST' or
                not re.fullmatch(r'/dual/carrera/grupos/[^/]+/alumnos(?:/preview)?/?', scope['path'])):
            return await self.app(scope, receive, send)
        async def reject():
            await JSONResponse({'detail': 'La solicitud CSV admite como máximo 600 KiB.'}, status_code=413)(scope, receive, send)
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            declared = 0
        if declared > self.limit:
            return await reject()
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > self.limit:
                return await reject()
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)
