"""Ayudantes de los guiones de auditoría y de carga (no forman parte del producto). Se ejecutan dentro del contenedor `smoke`."""
import secrets
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]          # ute-api-backend
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

import os

import httpx
from psycopg.types.json import Jsonb

from app.infrastructure.security.jwt_passwords import crear_token, hash_password
from local_admin import connect_local

BASE = os.environ.get("API_URL", "http://api:8000")
if BASE not in ("http://api:8000", "http://127.0.0.1:8001"):
    raise SystemExit("Destino HTTP no permitido para los guiones de auditoría")


def minar_token(conn, email, nombre, roles, matricula=None, hash_=None, matricula_claim=None):
    """Crea la cuenta por SQL (sin pasar por el inicio de sesión, que se limita a 8 por 5 minutos) y devuelve su token."""
    fila = conn.execute(
        "INSERT INTO usuarios (email,nombre,password_hash,roles,matricula,must_change_password) VALUES (%s,%s,%s,%s,%s,FALSE) "
        "RETURNING id, credential_version", (email, nombre, hash_ or hash_password(secrets.token_urlsafe(16)), Jsonb(roles), matricula)).fetchone()
    matricula = matricula or matricula_claim
    claims = {"sub": email, "id": str(fila[0]), "matricula": matricula, "roles": roles, "must_change_password": False,
              "credential_version": fila[1], "nombre": nombre, "grupo_id": None, "turno": None, "nomenclatura": None,
              "cuatrimestre": None, "carrera": None, "modalidad": None, "dual_activo": False}
    return {"Authorization": "Bearer " + crear_token(claims)}


class Ritmo:
    """Limita las peticiones por minuto de este proceso (el límite por usuario de la API es de 240 por minuto)."""

    def __init__(self, rpm):
        self.intervalo = 60.0 / rpm if rpm else 0
        self.cerrojo = threading.Lock()
        self.siguiente = time.monotonic()

    def esperar(self):
        if not self.intervalo:
            return
        with self.cerrojo:
            ahora = time.monotonic()
            espera = max(0.0, self.siguiente - ahora)
            self.siguiente = max(ahora, self.siguiente) + self.intervalo
        if espera:
            time.sleep(espera)


class Medidor:
    def __init__(self):
        self.filas = []
        self.cerrojo = threading.Lock()

    def pedir(self, ritmo, cliente, operacion, metodo, ruta, **kw):
        ritmo.esperar()
        t0 = time.perf_counter()
        try:
            r = cliente.request(metodo, ruta, **kw)
            estado, cuerpo = r.status_code, r
        except Exception as e:  # tiempo agotado, conexión rechazada...
            estado, cuerpo = type(e).__name__, None
        ms = (time.perf_counter() - t0) * 1000
        with self.cerrojo:
            self.filas.append((operacion, estado, round(ms, 1)))
        return cuerpo


def resumen(filas):
    por_op = {}
    for op, estado, ms in filas:
        por_op.setdefault(op, []).append((estado, ms))
    salida = []
    for op, lista in sorted(por_op.items()):
        tiempos = sorted(m for _, m in lista)
        n = len(tiempos)
        pct = lambda p: tiempos[min(n - 1, int(n * p))]
        estados = {}
        for e, _ in lista:
            estados[e] = estados.get(e, 0) + 1
        salida.append(f"{op:<28} n={n:<4} p50={pct(0.5):>7.0f}ms p95={pct(0.95):>7.0f}ms max={tiempos[-1]:>7.0f}ms estados={estados}")
    return "\n".join(salida)
