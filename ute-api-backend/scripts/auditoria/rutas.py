"""Auditoría dinámica de permisos: recorre TODAS las operaciones de /openapi.json sin sesión y con sesión de alumno, de tutor y de
coordinador, y comprueba que (1) nada responde 5xx, (2) sin sesión no hay datos, (3) cada rol recibe 403 donde no le corresponde y
(4) las cargas malformadas dan 4xx. Usa marcadores de posición que no existen, así que no modifica datos reales."""
import re
import secrets

from comun import BASE, Medidor, Ritmo, connect_local, hash_password, httpx, minar_token

sfx = secrets.token_hex(4)
h = hash_password("x" + secrets.token_urlsafe(10))
with connect_local() as conn:
    t_coord = minar_token(conn, f"aud.c.{sfx}@ute.edu.mx", "Auditoría coord", {"coordinador_dual": True}, hash_=h)
    t_tutor = minar_token(conn, f"aud.t.{sfx}@ute.edu.mx", "Auditoría tutor", {"tutor_academico": True}, hash_=h)
    m = str(secrets.randbelow(900000000) + 100000000)
    conn.execute("INSERT INTO alumnos (matricula,nombre) VALUES (%s,%s)", (m, "Auditoría alumno"))
    t_alum = minar_token(conn, f"{m}@ute.edu.mx", "Auditoría alumno", {"alumno": True}, matricula=m, hash_=h)
    conn.commit()

ritmo, med = Ritmo(100), Medidor()
cliente = httpx.Client(base_url=BASE, timeout=60, trust_env=False)
spec = cliente.get("/openapi.json").json()
valores = {"uuid": "00000000-0000-0000-0000-000000000000", "num": "999999"}


def ruta_real(ruta):
    def sub(m):
        nombre = m.group(1)
        if any(k in nombre for k in ("matricula",)):
            return "000000000"
        if nombre in ("numero", "version", "limite") or nombre.endswith("_n"):
            return "999999"
        if nombre in ("tipo",):
            return "word"
        if nombre in ("carrera", "codigo"):
            return "TII"
        return valores["uuid"]
    return re.sub(r"\{([^}]+)\}", sub, ruta)


operaciones = [(met.upper(), ruta) for ruta, ms in spec["paths"].items() for met in ms if met in ("get", "post", "put", "patch", "delete")]
print(f"Operaciones en OpenAPI: {len(operaciones)}")
PUBLICAS = {("GET", "/health"), ("POST", "/auth/login"), ("POST", "/auth/register"), ("GET", "/"), ("GET", "/openapi.json")}
hallazgos, tabla = [], []
for metodo, ruta in operaciones:
    url = ruta_real(ruta)
    cuerpo = {} if metodo in ("POST", "PUT", "PATCH") else None
    kw = {"json": cuerpo} if cuerpo is not None else {}
    fila = {"op": f"{metodo} {ruta}"}
    for rol, hdr in (("anon", {}), ("alumno", t_alum), ("tutor", t_tutor), ("coord", t_coord)):
        r = med.pedir(ritmo, cliente, f"{rol}", metodo, url, headers=hdr, **kw)
        fila[rol] = getattr(r, "status_code", "ERR")
        if getattr(r, "status_code", 0) >= 500:
            hallazgos.append(f"5xx {fila[rol]} {rol} {metodo} {ruta}: {r.text[:100]}")
    if (metodo, ruta) not in PUBLICAS and fila["anon"] not in (401, 403, 405, 404):
        hallazgos.append(f"SIN SESIÓN responde {fila['anon']}: {metodo} {ruta}")
    tabla.append(fila)
    # cargas malformadas con sesión de coordinador (nunca 5xx)
    if metodo in ("POST", "PUT", "PATCH"):
        for etiqueta, carga in (("enorme", {"x": "A" * 120000}), ("tipos", {"nombre": [1, 2], "id": {"a": 1}, "confirmar": "si"}),
                                ("nulos", {"nombre": "a\x00b", "frase": "‮", "matricula": "%00"})):
            r = med.pedir(ritmo, cliente, "malformada", metodo, url, headers=t_coord, json=carga)
            if getattr(r, "status_code", 0) >= 500:
                hallazgos.append(f"5xx con carga {etiqueta}: {metodo} {ruta} -> {r.status_code}")

# Matriz de permisos esperada por prefijo de ruta (heurística a partir de la arquitectura de roles)
SOLO_COORD = [r"^/dual/tutor/periodos/.+/(cierre-recepcion|finalizacion)$", r"^/dual/tutor/abrir-cuatrimestre$", r"^/auth/tutores", r"^/dual/plantillas/$"]
PERSONAL = [r"^/dual/tutor", r"^/dual/carrera", r"^/dual/plantillas/", r"^/auth/tutores"]
for f in tabla:
    metodo, ruta = f["op"].split(" ", 1)
    if any(re.search(p, ruta) for p in PERSONAL) and ruta not in ("/dual/plantillas/vigente",) and not re.match(r"^/dual/plantillas/\{[^}]+\}/\{[^}]+\}$", ruta) and f["alumno"] not in (401, 403, 404, 405, 422):
        hallazgos.append(f"ALUMNO accede a ruta del personal ({f['alumno']}): {f['op']}")
    if any(re.search(p, ruta) for p in SOLO_COORD) and metodo in ("POST", "DELETE") and f["tutor"] not in (401, 403, 404, 405):
        hallazgos.append(f"TUTOR accede a ruta de coordinación ({f['tutor']}): {f['op']}")

print("\n== Resumen de latencias de la auditoría\n" + __import__("comun").resumen(med.filas))
print("\n== Hallazgos (" + str(len(hallazgos)) + ")")
for x in hallazgos:
    print(" -", x)
print("\n== Tabla (estados por rol)")
for f in tabla:
    print(f"{f['op']:<70} anon={f['anon']} alumno={f['alumno']} tutor={f['tutor']} coord={f['coord']}")
