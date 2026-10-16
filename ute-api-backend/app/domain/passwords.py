"""Validaciones del secreto utilizado para autenticación."""
from unicodedata import category


def validate_password(password: str) -> None:
    # Exige una contraseña razonable sin depender de infraestructura.
    if len(password) < 12 or len(password) > 128:
        raise ValueError("La contraseña debe tener entre 12 y 128 caracteres")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña admite como máximo 72 bytes UTF-8")
    if not any(category(char) == "Ll" for char in password):
        raise ValueError("Incluye una letra minúscula")
    if not any(category(char) == "Lu" for char in password):
        raise ValueError("Incluye una letra mayúscula")
    if not any(category(char) == "Nd" for char in password):
        raise ValueError("Incluye un número")
