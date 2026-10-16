from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.infrastructure.config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Encriptacion de contrasenas
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Verificacion de contrasenas de texto plano
def verify_password(plain: str, hashed: str) -> bool:
    # Rechazar sufijos que bcrypt truncaría, también durante login.
    if len(plain.encode("utf-8")) > 72:
        return False
    return pwd_context.verify(plain, hashed)


# Creacion de tokens de acceso JWT
def crear_token(data: dict) -> str:
    payload = data.copy()
    expira = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload["exp"] = expira
    return jwt.encode(
        payload, settings.secret_key, algorithm=settings.algorithm
    )


# Verificacion y decodificacion de tokens JWT
def verificar_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("El token ha expirado")
    except jwt.InvalidTokenError:
        raise ValueError("Token invalido")


# Extraccion de matricula desde el correo institucional
def extraer_matricula(email: str) -> str:
    return email.split("@")[0]
