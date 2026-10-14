"""Validaciones del secreto utilizado para autenticación."""


def validate_password(password: str) -> None:
    # Exige una contraseña razonable sin depender de infraestructura.
    if len(password) < 12 or len(password) > 128:
        raise ValueError("La contraseña debe tener entre 12 y 128 caracteres")
    if not any(char.islower() for char in password):
        raise ValueError("Incluye una letra minúscula")
    if not any(char.isupper() for char in password):
        raise ValueError("Incluye una letra mayúscula")
    if not any(char.isdigit() for char in password):
        raise ValueError("Incluye un número")
