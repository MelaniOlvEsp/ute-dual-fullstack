"""C16: fallos por identidad; el agregado por IP/proxies vive en SecurityMiddleware."""
import hashlib
import math
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from fastapi import HTTPException
from app.application.errors import ApplicationError


class LoginFailureLimiter:
    def __init__(self, limit=8, window=300, max_keys=10000, clock=time.monotonic):
        self.limit, self.window, self.max_keys, self.clock = limit, window, max_keys, clock
        self.buckets = OrderedDict()

    @asynccontextmanager
    async def attempt(self, email):
        now = self.clock()
        key = hashlib.sha256(email.strip().casefold().encode()).digest()
        for old, value in list(self.buckets.items()):
            if not value['pending'] and (not value['failed'] or now - value['failed'][-1] >= self.window):
                del self.buckets[old]
        if key not in self.buckets:
            if len(self.buckets) >= self.max_keys:
                raise HTTPException(429, 'Demasiados intentos. Intenta más tarde.', headers={'Retry-After': str(self.window)})
            self.buckets[key] = {'failed': deque(), 'pending': 0}
        bucket = self.buckets[key]
        failed = bucket['failed']
        while failed and now - failed[0] >= self.window:
            failed.popleft()
        if len(failed) + bucket['pending'] >= self.limit:
            wait = max(1, math.ceil(self.window - (now - failed[0]))) if failed else 1
            raise HTTPException(429, 'Demasiados intentos. Intenta más tarde.', headers={'Retry-After': str(wait)})
        bucket['pending'] += 1
        try:
            yield
        except ApplicationError as exc:
            if exc.status_code in (401, 403, 429):
                failed.append(self.clock())
            if exc.status_code == 429:
                raise HTTPException(429, exc.detail, headers={'Retry-After': '900'}) from exc
            raise
        finally:
            bucket['pending'] -= 1
            if not failed and not bucket['pending']:
                self.buckets.pop(key, None)


login_failures = LoginFailureLimiter()
