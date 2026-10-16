# app/core/utils/periodos.py
# Catalogo unico de periodos de cuatrimestre.
# Siempre son los mismos 3 rangos de meses; lo unico que cambia es el año.
from datetime import date, timedelta

from app.domain.calendar import hoy as _hoy  # "hoy" en la zona operativa (C04)

PERIODOS_CUATRIMESTRE = [
    {"clave": "ENE-ABR", "mes_inicio": "Enero", "mes_fin": "Abril",
     "num_inicio": 1, "num_fin": 4},
    {"clave": "MAY-AGO", "mes_inicio": "Mayo", "mes_fin": "Agosto",
     "num_inicio": 5, "num_fin": 8},
    {"clave": "SEP-DIC", "mes_inicio": "Septiembre", "mes_fin": "Diciembre",
     "num_inicio": 9, "num_fin": 12},
]

# Combinaciones "MesInicio-MesFin" permitidas, listas para comparar
_LABELS_VALIDOS = {
    f"{p['mes_inicio']}-{p['mes_fin']}" for p in PERIODOS_CUATRIMESTRE
}


# Ejecuta la responsabilidad especificada para este módulo.
def _normalizar_mes(mes: str) -> str:
    return mes.strip().capitalize()


# Ejecuta la responsabilidad especificada para este módulo.
def _ultimo_dia_mes(anio: int, mes: int) -> date:
    if mes == 12:
        return date(anio, 12, 31)
    return date(anio, mes + 1, 1) - timedelta(days=1)


# Ejecuta la responsabilidad especificada para este módulo.
def validar_periodo(periodo: str) -> str:
    # Valida que 'periodo' tenga el formato "MesInicio-MesFin AAAA" y
    # que la combinacion de meses sea una de las 3 permitidas.
    # Retorna un mensaje de error, o cadena vacia si es valido.
    partes_espacio = periodo.strip().split()
    if len(partes_espacio) < 2:
        return (
            "El periodo debe incluir el año, ej. Mayo-Agosto 2026."
        )
    anio_str = partes_espacio[-1]
    mes_part = " ".join(partes_espacio[:-1])

    try:
        anio = int(anio_str)
    except ValueError:
        return f"Año inválido: {anio_str}"

    anio_actual = _hoy().year
    if anio < anio_actual:
        return f"El año {anio} ya pasó. Usa {anio_actual} o un año futuro."

    partes = mes_part.split("-")
    if len(partes) != 2:
        return (
            "Periodo inválido. Usa uno de: "
            "Enero-Abril, Mayo-Agosto, Septiembre-Diciembre."
        )

    combo = f"{_normalizar_mes(partes[0])}-{_normalizar_mes(partes[1])}"
    if combo not in _LABELS_VALIDOS:
        return (
            f"'{combo}' no es un periodo válido. Los únicos periodos "
            "permitidos son: Enero-Abril, Mayo-Agosto, Septiembre-Diciembre."
        )
    return ""


# Ejecuta la responsabilidad especificada para este módulo.
def construir_periodo(mes_inicio: str, anio: int) -> str:
    # Dado el mes de inicio (Enero/Mayo/Septiembre) y el año, arma
    # el string de periodo canonico, ej. construir_periodo("Mayo", 2026)
    # -> "Mayo-Agosto 2026".
    mes_norm = _normalizar_mes(mes_inicio)
    for p in PERIODOS_CUATRIMESTRE:
        if p["mes_inicio"] == mes_norm:
            return f"{p['mes_inicio']}-{p['mes_fin']} {anio}"
    raise ValueError(f"Mes de inicio desconocido: {mes_inicio}")


# Ejecuta la responsabilidad especificada para este módulo.
def fechas_del_periodo(mes_inicio: str, anio: int) -> tuple[date, date]:
    # Retorna (fecha_inicio, fecha_fin) deterministas para un periodo,
    # ej. fechas_del_periodo("Mayo", 2026) -> (2026-05-01, 2026-08-31).
    mes_norm = _normalizar_mes(mes_inicio)
    for p in PERIODOS_CUATRIMESTRE:
        if p["mes_inicio"] == mes_norm:
            inicio = date(anio, p["num_inicio"], 1)
            fin = _ultimo_dia_mes(anio, p["num_fin"])
            return inicio, fin
    raise ValueError(f"Mes de inicio desconocido: {mes_inicio}")


# Ejecuta la responsabilidad especificada para este módulo.
def periodo_actual(hoy: date | None = None) -> str:
    # Retorna el periodo canonico ("MesInicio-MesFin AAAA") al que
    # pertenece la fecha dada (o hoy, si no se especifica).
    hoy = hoy or _hoy()
    for p in PERIODOS_CUATRIMESTRE:
        if p["num_inicio"] <= hoy.month <= p["num_fin"]:
            return f"{p['mes_inicio']}-{p['mes_fin']} {hoy.year}"
    # No debería alcanzarse: los 3 rangos cubren los 12 meses
    ultimo = PERIODOS_CUATRIMESTRE[-1]
    return f"{ultimo['mes_inicio']}-{ultimo['mes_fin']} {hoy.year}"
