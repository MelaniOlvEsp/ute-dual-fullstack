"""Simulación de un flujo completo con varios alumnos y pruebas de carga (no forma parte del producto).

  setup N | alumnos DESDE HASTA W RPM | revisar W RPM | cerrar | lecturas DESDE HASTA W RPM | paquete | limite | integridad
  | carrera DESDE HASTA HILOS | sonda SEGUNDOS | informe
Estado y resultados en la carpeta AUDITORIA_DIR (por omisión /tmp/auditoria dentro del contenedor). Las cuentas y los
tokens son sintéticos, se crean por SQL y no se imprimen. Ver README.md."""
import io
import json
import os
import secrets
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from comun import BASE, Medidor, Ritmo, connect_local, hash_password, httpx, minar_token, resumen

import fitz
import smoke_periodos
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from smoke_c05 import BLOQUES, expect
from smoke_c06 import firma_png, reporte_formato

W_DIR = Path(os.environ.get("AUDITORIA_DIR", "/tmp/auditoria"))
W_DIR.mkdir(parents=True, exist_ok=True)
ESTADO = W_DIR / "estado.json"


def cliente():
    return httpx.Client(base_url=BASE, timeout=180, trust_env=False)


def pdf_de(tamano_kb: int, texto: str) -> bytes:
    contenido, _ = reporte_formato(texto)
    if not tamano_kb:
        return contenido
    d = fitz.open(stream=contenido, filetype="pdf")
    d.embfile_add("relleno.bin", secrets.token_bytes(tamano_kb * 1024))
    salida = d.tobytes()
    d.close()
    return salida


def setup(n):
    sfx = secrets.token_hex(4)
    h = hash_password("x" + secrets.token_urlsafe(10))
    with connect_local() as conn:
        usados = {f[0] for f in conn.execute("SELECT cuatrimestre FROM ciclos_dual").fetchall()}
        while True:
            anio, mes = secrets.randbelow(400) + 1500, BLOQUES[secrets.randbelow(3)][0]
            label = construir_periodo(mes, anio)
            if label not in usados:
                break
        inicio, fin = fechas_del_periodo(mes, anio)
        pid = conn.execute("INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) VALUES (%s,%s,%s,%s) RETURNING id",
                           (label, label, inicio, fin)).fetchone()[0]
        t_coord = minar_token(conn, f"carga.c.{sfx}@ute.edu.mx", "Carga coordinador", {"coordinador_dual": True}, hash_=h)
        t_tutor = minar_token(conn, f"carga.t.{sfx}@ute.edu.mx", "Carga tutor", {"tutor_academico": True}, hash_=h)
        matriculas = [str(secrets.randbelow(900000000) + 100000000) for _ in range(n)]
        conn.commit()
    c, ritmo, med = cliente(), Ritmo(90), Medidor()
    smoke_periodos.cerrar_abiertos(c, t_coord)
    with connect_local() as conn:
        conn.execute("UPDATE ciclos_dual SET abierto=TRUE WHERE id=%s", (pid,))
        conn.commit()
    expect(c.post("/dual/tutor/firma", headers=t_tutor, files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)
    plan, zona = str(secrets.randbelow(90) + 10), secrets.randbelow(30000) + 1
    grupo = expect(c.post("/dual/carrera/grupos", headers=t_tutor, json={
        "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A", "turno": "Matutino", "plan": plan, "zona": zona}), 201)
    empresa = expect(c.post("/dual/tutor/empresas", headers=t_tutor, json={"nombre": f"Empresa carga {sfx}"}), 201)
    csv = "matricula,nombre\n" + "".join(f"{m},Alumno carga {i}\n" for i, m in enumerate(matriculas))
    expect(c.post(f"/dual/carrera/grupos/{grupo['id']}/alumnos", headers=t_tutor, data={"periodo_id": str(pid)},
                  files={"file": ("a.csv", csv.encode(), "text/csv")}), 200)
    with connect_local() as conn:   # las cuentas se crean después de importar a los alumnos (la matrícula referencia a la tabla de alumnos)
        alumnos = [{"m": m, "auth": minar_token(conn, f"{m}@ute.edu.mx", f"Alumno carga {i}", {"alumno": True}, matricula=m, hash_=h)["Authorization"]}
                   for i, m in enumerate(matriculas)]
        conn.commit()
    ini = calendar.lunes_de(inicio + timedelta(days=14))
    t0 = time.time()
    for a in alumnos:
        med.pedir(ritmo, c, "PATCH incorporacion", "PATCH", f"/dual/tutor/alumnos/{a['m']}", headers=t_tutor, json={
            "alumno_dual": True, "empresa_id": empresa["id"], "fecha_inicio": ini.isoformat()})
        med.pedir(ritmo, c, "PATCH baja (4 semanas)", "PATCH", f"/dual/tutor/alumnos/{a['m']}", headers=t_tutor, json={
            "alumno_dual": False, "fecha_baja": (ini + timedelta(days=27)).isoformat()})
    ESTADO.write_text(json.dumps({"periodo": {"id": str(pid), "label": label}, "alumnos": alumnos, "tutor": t_tutor["Authorization"],
                                  "coord": t_coord["Authorization"], "grupo": grupo["id"], "n": n}), encoding="utf-8")
    print(f"setup: {n} alumnos, período {label}; incorporaciones en {time.time() - t0:.1f} s")
    print(resumen(med.filas))


def estado():
    return json.loads(ESTADO.read_text(encoding="utf-8"))


def alumnos_fase(desde, hasta, w, rpm):
    e = estado()
    lote = e["alumnos"][desde:hasta]
    ritmo, med = Ritmo(rpm), Medidor()
    resultados = []

    def flujo(i_a):
        i, a = i_a
        h = {"Authorization": a["auth"]}
        c = cliente()
        med.pedir(ritmo, c, "GET foro", "GET", "/foro/publicaciones", headers=h, params={"limit": 20})
        r = med.pedir(ritmo, c, "GET obligaciones", "GET", "/dual/alumno/obligaciones", headers=h)
        if getattr(r, "status_code", 0) != 200:
            return
        semanas = sorted((o for o in r.json() if o["periodo"] == e["periodo"]["label"] and o["puede_entregar"]), key=lambda o: o["ordinal"])[:2]
        for k, o in enumerate(semanas):
            nota = 6 + (desde + i + k) % 5
            kb = 6000 if (desde + i) % 10 == 0 and k == 0 else 0     # uno de cada diez sube un PDF de ~6 MB (carga reanudable)
            contenido = pdf_de(kb, f"{a['m']} {o['ordinal']}")
            r = med.pedir(ritmo, c, "POST entrega" + (" 6MB" if kb else ""), "POST", f"/dual/alumno/obligaciones/{o['id']}/entrega", headers=h,
                          data={"fecha_inicio": o["inicio_efectivo"], "fecha_fin": o["fin_efectivo"], "calificacion_alumno": str(nota)},
                          files={"archivo": ("reporte.pdf", contenido, "application/pdf")})
            if getattr(r, "status_code", 0) == 201:
                resultados.append({"m": a["m"], "rid": r.json()["reporte_id"], "nota": nota})
        med.pedir(ritmo, c, "GET obligaciones", "GET", "/dual/alumno/obligaciones", headers=h)
        med.pedir(ritmo, c, "GET expediente alumno", "GET", "/dual/alumno/expediente", headers=h)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=w) as pool:
        list(pool.map(flujo, enumerate(lote)))
    (W_DIR / f"res_alumnos_{desde}.json").write_text(json.dumps({"filas": med.filas, "reportes": resultados}), encoding="utf-8")
    print(f"alumnos {desde}-{hasta}: {len(resultados)} entregas en {time.time() - t0:.1f} s")


def todos_los_reportes():
    reportes = []
    for f in sorted(W_DIR.glob("res_alumnos_*.json")):
        reportes += json.loads(f.read_text(encoding="utf-8"))["reportes"]
    return reportes


def revisar(w, rpm):
    e = estado()
    h = {"Authorization": e["tutor"]}
    ritmo, med = Ritmo(rpm), Medidor()
    reportes = todos_los_reportes()

    def aprobar(r):
        c = cliente()
        med.pedir(ritmo, c, "POST revision (aprobar y firmar)", "POST", f"/dual/tutor/reportes/{r['rid']}/versiones/1/revision",
                  headers=h, json={"decision": "Aprobada"})

    t0 = time.time()
    c0 = cliente()
    med.pedir(ritmo, c0, "GET bandeja tutor", "GET", "/dual/tutor/reportes", headers=h, params={"estado": "Pendiente"})
    with ThreadPoolExecutor(max_workers=w) as pool:
        list(pool.map(aprobar, reportes))
    (W_DIR / "res_revisar.json").write_text(json.dumps({"filas": med.filas}), encoding="utf-8")
    print(f"revisión: {len(reportes)} reportes en {time.time() - t0:.1f} s")


def cerrar():
    e = estado()
    hc, ht = {"Authorization": e["coord"]}, {"Authorization": e["tutor"]}
    c, med, ritmo = cliente(), Medidor(), Ritmo(90)
    pid = e["periodo"]["id"]
    r = med.pedir(ritmo, c, "GET resumen periodo", "GET", f"/dual/tutor/periodos/{pid}/resumen", headers=ht)
    print("resumen antes:", {k: v for k, v in r.json()["conteos"].items()})
    med.pedir(ritmo, c, "POST cierre recepcion", "POST", f"/dual/tutor/periodos/{pid}/cierre-recepcion", headers=hc, json={"confirmar": True})
    r = med.pedir(ritmo, c, "POST finalizacion", "POST", f"/dual/tutor/periodos/{pid}/finalizacion", headers=hc, json={"confirmar": True})
    print("finalización:", r.status_code)
    esperado = {}
    for x in todos_los_reportes():
        esperado.setdefault(x["m"], []).append(x["nota"])
    definitivos = {a["matricula"]: a for a in r.json()["alumnos"]}
    mal = []
    for m, notas in esperado.items():
        prom = f"{sum(notas) / len(notas):.2f}"
        got = definitivos.get(m, {}).get("promedio")
        if got != prom or not definitivos[m]["definitivo"]:
            mal.append((m[:3] + "…", prom, got))
    print(f"promedios comprobados: {len(esperado)}; discrepancias: {len(mal)} {mal[:5]}")
    (W_DIR / "res_cerrar.json").write_text(json.dumps({"filas": med.filas}), encoding="utf-8")


def lecturas(desde, hasta, w, rpm):
    e = estado()
    ritmo, med = Ritmo(rpm), Medidor()
    pid = e["periodo"]["id"]

    def leer(a):
        h, c = {"Authorization": a["auth"]}, cliente()
        med.pedir(ritmo, c, "GET expediente alumno", "GET", "/dual/alumno/expediente", headers=h)
        r = med.pedir(ritmo, c, "GET paquete alumno (ZIP)", "GET", "/dual/alumno/paquete", headers=h, params={"periodo_id": pid})
        if getattr(r, "status_code", 0) == 200:
            try:
                assert len(zipfile.ZipFile(io.BytesIO(r.content)).namelist()) >= 3
            except Exception:
                med.filas.append(("ZIP inválido", "error", 0))

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=w) as pool:
        list(pool.map(leer, e["alumnos"][desde:hasta]))
    (W_DIR / f"res_lecturas_{desde}.json").write_text(json.dumps({"filas": med.filas}), encoding="utf-8")
    print(f"lecturas {desde}-{hasta} en {time.time() - t0:.1f} s")


def paquete():
    e = estado()
    h = {"Authorization": e["tutor"]}
    c, med, ritmo = cliente(), Medidor(), Ritmo(90)
    t0 = time.time()
    r = med.pedir(ritmo, c, "GET paquete carrera (ZIP)", "GET", "/dual/carrera/paquetes/carrera/TII", headers=h, params={"periodo_id": e["periodo"]["id"]})
    pdfs = sum(1 for n in zipfile.ZipFile(io.BytesIO(r.content)).namelist() if n.endswith(".pdf")) if r.status_code == 200 else 0
    print(f"paquete de la carrera: estado {r.status_code}, {len(r.content) / 1e6:.1f} MB, {pdfs} PDF en {time.time() - t0:.1f} s")
    (W_DIR / "res_paquete.json").write_text(json.dumps({"filas": med.filas}), encoding="utf-8")


def limite():
    c0 = cliente()
    estados, cuerpos = {}, {}
    t0 = time.time()

    def uno(_):
        r = cliente().get("/health")
        return r.status_code, r.text[:90]

    with ThreadPoolExecutor(max_workers=20) as pool:
        for s, t in pool.map(uno, range(200)):
            estados[s] = estados.get(s, 0) + 1
            cuerpos.setdefault(s, t)
    print(f"200 GET /health en {time.time() - t0:.1f} s desde una sola IP: {estados}")
    for s, t in cuerpos.items():
        if s != 200:
            print(f"  cuerpo de la respuesta {s}: {t}")


def integridad():
    e = estado()
    pid, lab = e["periodo"]["id"], e["periodo"]["label"]
    with connect_local() as conn:
        q = lambda s, p=(): conn.execute(s, p).fetchone()[0]
        n = e["n"]
        reportes = q("SELECT count(*) FROM reportes_dual WHERE cuatrimestre=%s", (lab,))
        versiones = q("SELECT count(*) FROM reporte_versiones v JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.cuatrimestre=%s", (lab,))
        duplicados = q("SELECT count(*) FROM (SELECT obligacion_id FROM reportes_dual WHERE cuatrimestre=%s GROUP BY obligacion_id HAVING count(*)>1) x", (lab,))
        revis = q("SELECT count(*) FROM revisiones rv JOIN reporte_versiones v ON v.id=rv.version_id JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.cuatrimestre=%s AND rv.decision='Aprobada'", (lab,))
        firmados = q("SELECT count(*) FROM revisiones rv JOIN reporte_versiones v ON v.id=rv.version_id JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.cuatrimestre=%s AND rv.documento_firmado_id IS NOT NULL", (lab,))
        cierres = q("SELECT count(*) FROM cierres_alumno_periodo WHERE periodo_id=%s", (pid,))
        sin_archivo = q("SELECT count(*) FROM documentos d WHERE d.id IN (SELECT v.documento_id FROM reporte_versiones v JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.cuatrimestre=%s) AND d.archivado_en IS NULL AND d.sha256 !~ '^[0-9a-f]{64}$'", (lab,))
    print(f"integridad (n={n}): reportes={reportes} versiones={versiones} obligaciones con más de un reporte={duplicados} aprobadas={revis} firmadas={firmados} cierres={cierres} documentos con huella inválida={sin_archivo}")
    from app.infrastructure.storage.registro import get_storage
    a = get_storage()
    with connect_local() as conn:
        claves = [f[0] for f in conn.execute(
            "SELECT d.clave FROM documentos d WHERE d.id IN (SELECT v.documento_id FROM reporte_versiones v JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.cuatrimestre=%s) "
            "OR d.id IN (SELECT rv.documento_firmado_id FROM revisiones rv JOIN reporte_versiones v ON v.id=rv.version_id JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.cuatrimestre=%s)", (lab, lab)).fetchall()]
    ausentes = [k for k in claves if not a.existe("documentos", k)]
    print(f"documentos del período: {len(claves)}; ausentes en Drive: {len(ausentes)}")


def carrera_obligaciones(desde, hasta, hilos):
    """Carrera de creación perezosa de obligaciones: varias lecturas simultáneas de un mismo alumno no deben duplicar ni perder filas."""
    e = estado()
    med, ritmo = Medidor(), Ritmo(0)
    lote = e["alumnos"][desde:hasta]

    def leer(a):
        c = cliente()
        return med.pedir(ritmo, c, "GET obligaciones (carrera)", "GET", "/dual/alumno/obligaciones", headers={"Authorization": a["auth"]})

    t0 = time.time()
    total = 0
    for a in lote:
        with ThreadPoolExecutor(max_workers=hilos) as pool:
            respuestas = list(pool.map(lambda _: leer(a), range(hilos)))
        total += len(respuestas)
    esperadas = None
    malos = []
    with connect_local() as conn:
        for a in lote:
            filas = conn.execute("SELECT count(*), count(DISTINCT o.semana_inicio) FROM obligaciones_semanales o JOIN alumnos_dual ad ON ad.id=o.incorporacion_id WHERE ad.matricula=%s", (a["m"],)).fetchone()
            esperadas = esperadas or filas[0]
            if filas[0] != filas[1] or filas[0] != esperadas:
                malos.append((a["m"][:3] + "…", filas))
    estados = {}
    for _, s, _ in med.filas:
        estados[s] = estados.get(s, 0) + 1
    print(f"carrera: {total} lecturas simultáneas ({hilos} por alumno) de {len(lote)} alumnos en {time.time() - t0:.1f} s; estados {estados}; "
          f"obligaciones por alumno {esperadas}; duplicados o conteos distintos: {len(malos)} {malos[:3]}")
    (W_DIR / "res_carrera.json").write_text(json.dumps({"filas": med.filas}), encoding="utf-8")

def sonda(segundos):
    """Mide la capacidad de respuesta de la API mientras otro proceso hace una tarea pesada (p. ej. el paquete ZIP de la carrera)."""
    e = estado()
    h = {"Authorization": e["alumnos"][0]["auth"]}
    c = cliente()
    filas, fin = [], time.time() + segundos
    while time.time() < fin:
        for etiqueta, ruta in (("sonda /health", "/health"), ("sonda expediente", "/dual/alumno/expediente")):
            t0 = time.perf_counter()
            try:
                r = c.get(ruta, headers=h if "expediente" in ruta else {})
                estado_ = r.status_code
            except Exception as ex:
                estado_ = type(ex).__name__
            filas.append((etiqueta, estado_, round((time.perf_counter() - t0) * 1000, 1)))
        time.sleep(1.2)
    print(resumen(filas))
    (W_DIR / "res_sonda.json").write_text(json.dumps({"filas": filas}), encoding="utf-8")

def informe():
    filas = []
    for f in sorted(W_DIR.glob("res_*.json")):
        filas += [tuple(x) for x in json.loads(f.read_text(encoding="utf-8")).get("filas", [])]
    print(resumen(filas))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"setup": lambda: setup(int(a[0])), "alumnos": lambda: alumnos_fase(int(a[0]), int(a[1]), int(a[2]), int(a[3])),
     "revisar": lambda: revisar(int(a[0]), int(a[1])), "cerrar": cerrar,
     "lecturas": lambda: lecturas(int(a[0]), int(a[1]), int(a[2]), int(a[3])), "paquete": paquete, "limite": limite,
     "integridad": integridad, "sonda": lambda: sonda(int(a[0])), "informe": informe, "carrera": lambda: carrera_obligaciones(int(a[0]), int(a[1]), int(a[2]))}[c]()
