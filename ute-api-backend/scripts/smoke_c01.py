"""Smoke C01: HTTP real + PostgreSQL real, solo Compose local ute_dual_c01.
Crea datos sintéticos identificables. No elimina datos ni imprime claves/tokens.
"""
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx
from local_admin import connect_local, create_coordinator
from app.infrastructure.security.jwt_passwords import hash_password
from psycopg.types.json import Jsonb

BASE = os.environ.get("API_URL", "http://127.0.0.1:8000")
if BASE not in ("http://api:8000", "http://127.0.0.1:8000", "http://127.0.0.1:8001"):
    raise SystemExit("Destino HTTP no permitido para smoke C01")

def expect(response, status):
    if response.status_code != status:
        raise AssertionError(f"{response.request.method} {response.request.url.path}: esperado {status}, recibido {response.status_code}")
    return response.json()

def main():
    suffix = secrets.token_hex(5)
    password = "C01a" + secrets.token_urlsafe(20)
    changed = "C01b" + secrets.token_urlsafe(20)
    coordinator = f"c01.{suffix}@ute.edu.mx"
    tutor = f"t01.{suffix}@ute.edu.mx"
    matricula = str(secrets.randbelow(900000000) + 100000000)
    other = str(secrets.randbelow(900000000) + 100000000)
    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator, "Coordinador sintético smoke C01")
    with connect_local() as conn:
        for number, degree in ((matricula, 1), (other, 2)):
            group = conn.execute(
                "INSERT INTO grupos (plan,carrera,zona,modalidad,cuatrimestre,letra,ciclo_ingreso) "
                "VALUES ('26','ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',1,'intensivo',%s,'A',%s) RETURNING id",
                (degree, suffix),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO alumnos (matricula,nombre,email,grupo_id,registro_dual_autorizado) VALUES (%s,%s,%s,%s,TRUE)",
                (number, "Alumno sintético smoke C01", f"{number}@ute.edu.mx", group),
            )
        conn.execute(
            "INSERT INTO usuarios (email,password_hash,roles,matricula) VALUES (%s,%s,%s,%s)",
            (f"{other}@ute.edu.mx", hash_password(password), Jsonb({"alumno": True}), other),
        )
        for period in ("Mayo-Agosto 2026", "Septiembre-Diciembre 2026"):
            conn.execute("INSERT INTO alumnos_dual (matricula,cuatrimestre) VALUES (%s,%s)", (other, period))
    with httpx.Client(base_url=BASE, timeout=20, trust_env=False) as client:
        expect(client.get("/health"), 200)
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}
        admin_headers = login(coordinator, password)
        expect(client.get("/auth/me", headers=admin_headers), 403)
        expect(client.post("/auth/cambiar-password", headers=admin_headers,
                           json={"password_actual": password, "password_nueva": changed}), 200)
        expect(client.get("/auth/me", headers=admin_headers), 401)
        admin_headers = login(coordinator, changed)
        profile = expect(client.get("/auth/me", headers=admin_headers), 200)
        assert profile["roles"]["coordinador_dual"] and not profile["roles"]["tutor_academico"]
        created = expect(client.post("/auth/tutores", headers=admin_headers,
                                     json={"nombre": "Tutor smoke C01", "email": tutor}), 201)
        temp = created["password_temporal"]
        tutor_headers = login(tutor, temp)
        expect(client.post("/auth/cambiar-password", headers=tutor_headers,
                           json={"password_actual": temp, "password_nueva": changed}), 200)
        tutor_headers = login(tutor, changed)
        tutor_profile = expect(client.get("/auth/me", headers=tutor_headers), 200)
        expect(client.get("/auth/tutores", headers=tutor_headers), 403)
        expect(client.post("/auth/register", json={"email": f"{matricula}@ute.edu.mx", "password": password}), 201)
        student_headers = login(f"{matricula}@ute.edu.mx", password)
        profile = expect(client.get("/auth/me", headers=student_headers), 200)
        assert profile["matricula"] == matricula and profile["roles"]["alumno"]
        expect(client.get("/auth/tutores", headers=student_headers), 403)
        # Perfil único aun cuando la demo tenga dos asignaciones activas.
        other_headers = login(f"{other}@ute.edu.mx", password)
        assert expect(client.get("/auth/me", headers=other_headers), 200)["matricula"] == other
        expect(client.delete("/auth/tutores/" + tutor_profile["id"], headers=admin_headers), 200)
        expect(client.get("/auth/me", headers=tutor_headers), 401)
        expect(client.post("/auth/login", json={"email": tutor, "password": changed}), 401)
        with connect_local() as conn:
            active, version = conn.execute("SELECT activo, credential_version FROM usuarios WHERE email=%s", (tutor,)).fetchone()
            assert active is False and version >= 2
    print("PASS C01: health, coordinador CLI, login/perfil, cambio obligatorio/revocación, alta tutor/alumno, permisos y baja lógica. HTTP y PostgreSQL reales.")
    print("Drive, calendario, reportes y expediente integral: NO_VERIFICADA.")

if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f"FAIL C01: {exc}", file=sys.stderr)
        raise SystemExit(1)
