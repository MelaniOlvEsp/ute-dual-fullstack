"""Roles y permisos de Formación Dual."""

SUPPORTED_ROLES = ("alumno", "tutor_academico", "coordinador_dual")


def active_roles(roles: dict | None) -> dict[str, bool]:
    # Conserva únicamente los roles reconocidos.
    roles = roles or {}
    return {name: bool(roles.get(name, False)) for name in SUPPORTED_ROLES}


def has_role(user: dict, *names: str) -> bool:
    # Comprueba privilegios sin usar roles heredados.
    roles = active_roles(user.get("roles"))
    return any(roles.get(name) for name in names)
