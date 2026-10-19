"""C14-AC5 real: alta con inicio en 2015, baja de 4 semanas registrada antes de la primera lectura."""
import secrets
import time

from comun import BASE, connect_local, hash_password, httpx, minar_token

sfx = secrets.token_hex(4)
h = hash_password("x" + secrets.token_urlsafe(10))
m = str(secrets.randbelow(900000000) + 100000000)
with connect_local() as conn:
    conn.execute("INSERT INTO alumnos (matricula,nombre) VALUES (%s,%s)", (m, "Retroactiva"))
    t_tutor = minar_token(conn, f"retro.t.{sfx}@ute.edu.mx", "Retro tutor", {"tutor_academico": True}, hash_=h)
    t_alum = minar_token(conn, f"{m}@ute.edu.mx", "Retroactiva", {"alumno": True}, matricula=m, hash_=h)
    conn.commit()
c = httpx.Client(base_url=BASE, timeout=60, trust_env=False)
emp = c.post("/dual/tutor/empresas", headers=t_tutor, json={"nombre": f"Empresa retro {sfx}"}).json()


def filas():
    with connect_local() as conn:
        return conn.execute("SELECT count(*), max(o.semana_fin) FROM obligaciones_semanales o JOIN alumnos_dual i "
                            "ON i.id=o.incorporacion_id WHERE i.matricula=%s", (m,)).fetchone()


t0 = time.perf_counter()
r1 = c.patch(f"/dual/tutor/alumnos/{m}", headers=t_tutor, json={"alumno_dual": True, "empresa_id": emp["id"], "fecha_inicio": "2015-01-05"})
t1 = time.perf_counter()
print("alta:", r1.status_code, f"{(t1 - t0) * 1000:.0f} ms", "filas tras alta:", filas())
r2 = c.patch(f"/dual/tutor/alumnos/{m}", headers=t_tutor, json={"alumno_dual": False, "fecha_baja": "2015-02-01"})
t2 = time.perf_counter()
print("baja:", r2.status_code, f"{(t2 - t1) * 1000:.0f} ms", "filas tras baja:", filas())
r3 = c.get("/dual/alumno/obligaciones", headers=t_alum)
t3 = time.perf_counter()
print("lectura:", r3.status_code, f"{(t3 - t2) * 1000:.0f} ms", "filas:", filas())


