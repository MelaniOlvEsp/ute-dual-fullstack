"""Smoke C08 con HTTP, PostgreSQL y almacenamiento en disco reales sobre Compose local.

Expediente por período con cambio de grupo, directorio paginado con bajas, descarga de aprobados,
paquetes de archivo (ZIP con manifiesto y hashes) por alumno y por carrera, ventana de una semana
del alumno, permisos/IDOR, registro inmutable y falla de un archivo faltante. Datos sintéticos; no
se imprimen contraseñas.

Preparación documentada: los períodos de esta prueba son pasados (la API no abre períodos
terminados), así que se insertan y se marcan como abiertos con SQL. El reloj de la ventana del
alumno se simula moviendo `evaluacion_finalizada_en` con SQL (se desactiva y se vuelve a activar el
disparador de protección solo en esa sentencia); todo lo demás ocurre por la API.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import secrets
import sys
import zipfile
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
import psycopg
from psycopg.types.json import Jsonb

import smoke_periodos
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from app.infrastructure.security.jwt_passwords import hash_password
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, BLOQUES, almacen, expect, pdf
from smoke_c06 import firma_png


def leer_zip(contenido: bytes):
    """Abre el ZIP, comprueba cada hash del manifiesto contra los bytes y devuelve (manifiesto, filas CSV, nombres)."""
    zf = zipfile.ZipFile(io.BytesIO(contenido))
    assert zf.testzip() is None
    nombres = zf.namelist()
    assert len(nombres) == len(set(nombres)), "Entradas duplicadas en el ZIP"
    assert all(not n.startswith("/") and ".." not in n.split("/") and "\\" not in n for n in nombres), nombres
    manifiesto = json.loads(zf.read("manifiesto.json"))
    rutas = set()
    for alumno in manifiesto["alumnos"]:
        for reporte in alumno["reportes"]:
            for archivo in reporte["archivos"]:
                datos = zf.read(archivo["ruta"])
                assert hashlib.sha256(datos).hexdigest() == archivo["sha256"], archivo["ruta"]
                assert len(datos) == archivo["tamano"]
                rutas.add(archivo["ruta"])
    assert set(nombres) == rutas | {"manifiesto.json", "resumen.csv"}, set(nombres) ^ (rutas | {"manifiesto.json", "resumen.csv"})
    filas = list(csv.reader(io.StringIO(zf.read("resumen.csv").decode("utf-8-sig"))))
    return manifiesto, filas, nombres, hashlib.sha256(zf.read("manifiesto.json")).hexdigest()


def main():
    suffix = secrets.token_hex(5)
    password = "C08a" + secrets.token_urlsafe(18)
    coordinator_email = f"c08.{suffix}@ute.edu.mx"
    tutor_email = f"t08.{suffix}@ute.edu.mx"
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1
    matriculas = {n: str(secrets.randbelow(900000000) + 100000000) for n in ("A", "B", "C", "F")}
    nombre_formula = "=1+1 Sintético C08 F"

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C08")

    with connect_local() as conn:
        usados = {f[0] for f in conn.execute("SELECT cuatrimestre FROM ciclos_dual").fetchall()}
        pasados = []
        while len(pasados) < 3:
            anio = secrets.randbelow(44) + 1980  # 132 etiquetas pasadas posibles
            mes = BLOQUES[secrets.randbelow(3)][0]
            label = construir_periodo(mes, anio)
            if label in usados:
                continue
            usados.add(label)
            inicio, fin = fechas_del_periodo(mes, anio)
            periodo_id = conn.execute(
                "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
                "VALUES (%s,%s,%s,%s) RETURNING id", (label, label, inicio, fin)).fetchone()[0]
            pasados.append({"id": periodo_id, "label": label, "inicio": inicio, "fin": fin})
        conn.commit()
    # p1 y p2 se finalizan (p2 es posterior: el grupo actual del alumno es el del período más reciente); p3 queda sin finalizar.
    p1, p2, p3 = sorted(pasados, key=lambda p: p["inicio"])

    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        with connect_local() as conn:
            conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (coordinator_email,))
            conn.execute(
                "INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                (tutor_email, "Tutor sintético C08", hash_password(password), Jsonb({"tutor_academico": True})))
            conn.commit()
            tutor_id = conn.execute("SELECT id FROM usuarios WHERE email=%s", (tutor_email,)).fetchone()[0]
        coordinator = login(coordinator_email, password)
        tutor = login(tutor_email, password)
        expect(client.post("/dual/tutor/firma", headers=tutor,
                           files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)
        smoke_periodos.cerrar_abiertos(client, coordinator)

        # ---------- Preparación: dos grupos (cambio de grupo entre períodos) ----------
        def crear_grupo(cuatrimestre):
            return expect(client.post("/dual/carrera/grupos", headers=tutor, json={
                "carrera": "TII", "cuatrimestre": cuatrimestre, "modalidad": "intensivo", "letra": "A",
                "turno": "Matutino", "plan": plan, "zona": zone}), 201)

        g1, g2 = crear_grupo(1), crear_grupo(2)
        empresa = expect(client.post("/dual/tutor/empresas", headers=tutor,
                                     json={"nombre": f"Empresa C08 {suffix}"}), 201)
        with connect_local() as conn:
            nom1 = conn.execute("SELECT nomenclatura FROM grupos WHERE id=%s", (g1["id"],)).fetchone()[0]
            nom2 = conn.execute("SELECT nomenclatura FROM grupos WHERE id=%s", (g2["id"],)).fetchone()[0]
        assert nom1 != nom2

        def importar(grupo, periodo, alumnos):
            filas = "".join(f"{matriculas[n]},{nombre_formula if n == 'F' else 'Alumno sintético C08 ' + n}\n"
                            for n in alumnos)
            expect(client.post(f"/dual/carrera/grupos/{grupo['id']}/alumnos", headers=tutor,
                               data={"periodo_id": str(periodo["id"])},
                               files={"file": ("alumnos.csv", ("matricula,nombre\n" + filas).encode(), "text/csv")}), 200)

        def incorporar(nombre, inicio, baja):
            expect(client.patch(f"/dual/tutor/alumnos/{matriculas[nombre]}", headers=tutor, json={
                "alumno_dual": True, "empresa_id": empresa["id"], "fecha_inicio": inicio.isoformat()}), 200)
            expect(client.patch(f"/dual/tutor/alumnos/{matriculas[nombre]}", headers=tutor, json={
                "alumno_dual": False, "fecha_baja": baja.isoformat()}), 200)

        def inicio_de(periodo):
            return calendar.lunes_de(periodo["inicio"] + timedelta(days=14))

        importar(g1, p1, ("A", "B", "C", "F"))
        for nombre in ("A", "B", "C", "F"):
            inicio = inicio_de(p1)
            incorporar(nombre, inicio, inicio + timedelta(days=27))
        # A cambia de grupo y vuelve a incorporarse en el segundo período.
        importar(g2, p2, ("A",))
        incorporar("A", inicio_de(p2), inicio_de(p2) + timedelta(days=27))

        alumno_pw = "C08s" + secrets.token_urlsafe(18)
        sesion = {}
        for nombre in ("A", "C"):
            m = matriculas[nombre]
            expect(client.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": alumno_pw}), 201)
            sesion[nombre] = login(f"{m}@ute.edu.mx", alumno_pw)

        def semanas(nombre, label):
            return sorted((o for o in expect(client.get("/dual/alumno/obligaciones", headers=sesion[nombre]), 200)
                           if o["periodo"] == label), key=lambda o: o["ordinal"])

        def entregar(nombre, obligacion, nota):
            respuesta = client.post(
                f"/dual/alumno/obligaciones/{obligacion['id']}/entrega", headers=sesion[nombre],
                data={"fecha_inicio": obligacion["inicio_efectivo"], "fecha_fin": obligacion["fin_efectivo"],
                      "calificacion_alumno": str(nota)},
                files={"archivo": ("reporte.pdf", pdf(f"{nombre} {obligacion['ordinal']}"), "application/pdf")})
            assert respuesta.status_code == 201, (nombre, respuesta.status_code, respuesta.text[:200])
            return respuesta.json()["reporte_id"]

        def revisar(reporte_id, **cuerpo):
            return expect(client.post(f"/dual/tutor/reportes/{reporte_id}/versiones/1/revision",
                                      headers=tutor, json=cuerpo), 200)

        def abrir_pasado(periodo):
            smoke_periodos.cerrar_abiertos(client, coordinator)
            with connect_local() as conn:
                conn.execute("UPDATE ciclos_dual SET abierto=TRUE WHERE id=%s", (periodo["id"],))
                conn.commit()

        def cerrar_y_finalizar(periodo):
            smoke_periodos.cerrar(client, coordinator, str(periodo["id"]))
            expect(client.post(f"/dual/tutor/periodos/{periodo['id']}/finalizacion", headers=coordinator,
                               json={"confirmar": True}), 200)

        # ---------- Período 1: tres aprobados de A/C/F, un rechazo de A y uno de B ----------
        # Antes de finalizar, un paquete del período abierto no existe (409) y el alumno lo ve no disponible.
        abrir_pasado(p1)
        sa = semanas("A", p1["label"])
        a1 = [entregar("A", sa[0], 8), entregar("A", sa[1], 10), entregar("A", sa[2], 5)]
        # B y F no entregan: quedan sin aprobados (Sin calificación).
        sc = semanas("C", p1["label"])
        c1 = entregar("C", sc[0], 9)
        for reporte_id in a1[:2]:
            assert revisar(reporte_id, decision="Aprobada")["estado"] == "Aprobada"
        revisar(a1[2], decision="Rechazada", observacion="Nota ilegible")
        # Corrección de la nota de C por el tutor (9 → 10): el expediente la marca como corregida.
        revisar(c1, decision="Aprobada", calificacion=10)
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=tutor,
                          params={"periodo_id": str(p1["id"])}), 409)
        cerrar_y_finalizar(p1)

        # ---------- Período 2: A en otro grupo ----------
        abrir_pasado(p2)
        sa2 = semanas("A", p2["label"])
        a2 = [entregar("A", sa2[0], 9), entregar("A", sa2[1], 10)]
        for reporte_id in a2:
            revisar(reporte_id, decision="Aprobada")
        cerrar_y_finalizar(p2)

        # ---------- Rutas heredadas retiradas ----------
        for metodo, ruta, headers in (
                ("GET", "/dual/alumno/mis-reportes", sesion["A"]),
                ("GET", f"/dual/alumno/reporte/{a1[0]}/pdf", sesion["A"]),
                ("GET", f"/dual/carrera/alumnos/{matriculas['A']}/reportes", tutor),
                ("GET", f"/dual/carrera/alumnos/{matriculas['A']}/exportar-csv", tutor),
                ("GET", f"/dual/carrera/alumnos/{matriculas['A']}/exportar-zip", tutor),
                ("GET", f"/dual/carrera/reporte/{a1[0]}/pdf", tutor)):
            assert client.request(metodo, ruta, headers=headers).status_code in (404, 405), ruta

        # ---------- Directorio paginado con bajas ----------
        base_q = {"cuatrimestre": p1["label"]}
        todos = expect(client.get("/dual/carrera/alumnos", headers=tutor, params={**base_q, "situacion": "baja"}), 200)
        assert todos["total"] == 4 and {a["matricula"] for a in todos["items"]} == set(matriculas.values()), todos["total"]
        assert all(a["activo"] is False and a["fecha_baja"] for a in todos["items"])
        pagina1 = expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                    params={**base_q, "situacion": "baja", "limite": 3}), 200)
        pagina2 = expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                    params={**base_q, "situacion": "baja", "limite": 3, "desplazamiento": 3}), 200)
        assert len(pagina1["items"]) == 3 and len(pagina2["items"]) == 1 and pagina1["total"] == pagina2["total"] == 4
        assert {a["matricula"] for a in pagina1["items"] + pagina2["items"]} == set(matriculas.values())
        assert expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                 params={**base_q, "situacion": "activos"}), 200)["total"] == 0
        fila = {a["matricula"]: a for a in todos["items"]}
        assert fila[matriculas["A"]]["reportes_aprobados"] == 2 and float(fila[matriculas["A"]]["promedio"]) == 9.0
        assert fila[matriculas["B"]]["reportes_aprobados"] == 0 and fila[matriculas["B"]]["promedio"] is None
        assert expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                 params={**base_q, "q": matriculas["A"]}), 200)["total"] == 1
        assert expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                 params={**base_q, "q": "%_\\"}), 200)["total"] == 0, "Los comodines se escapan"
        en_g1 = expect(client.get("/dual/carrera/alumnos", headers=tutor, params={**base_q, "grupo": nom1}), 200)
        assert en_g1["total"] == 3, ("grupo actual: A ya está en el segundo", nom1, nom2,
                                     [(x["matricula"], x["nomenclatura"]) for x in en_g1["items"]], matriculas)
        assert expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                 params={**base_q, "grupo": nom2}), 200)["total"] == 1
        assert expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                 params={"cuatrimestre": p2["label"], "grupo": nom2}), 200)["total"] == 1
        for parametros in ({"limite": 0}, {"limite": 201}, {"desplazamiento": -1}, {"situacion": "otro"},
                           {"desplazamiento": 10 ** 30}, {"q": "a\x00b"}, {"grupo": "\x00"}, {"cuatrimestre": "\x00"}):
            expect(client.get("/dual/carrera/alumnos", headers=tutor, params=parametros), 422)
        expect(client.get("/dual/carrera/alumnos/%00/expediente", headers=tutor), 422)
        expect(client.get("/dual/carrera/alumnos", headers=coordinator), 200)   # el coordinador consulta
        expect(client.get("/dual/carrera/alumnos", headers=sesion["A"]), 403)
        assert client.get("/dual/carrera/alumnos").status_code == 401

        # ---------- Expediente: períodos, grupo histórico, final vs congelado, corregidos ----------
        mio = expect(client.get("/dual/alumno/expediente", headers=sesion["A"]), 200)
        assert mio["alumno"]["matricula"] == matriculas["A"]
        por_periodo = {p["periodo"]["id"]: p for p in mio["periodos"]}
        e1, e2 = por_periodo[str(p1["id"])], por_periodo[str(p2["id"])]
        assert e1["grupo"]["nomenclatura"] == nom1 and e2["grupo"]["nomenclatura"] == nom2, "El grupo es el del período"
        assert (e1["resumen"]["promedio"], e1["resumen"]["definitivo"], e1["resumen"]["aprobados"]) == ("9.00", True, 2)
        assert (e2["resumen"]["promedio"], e2["resumen"]["definitivo"]) == ("9.50", True)
        assert len(e1["aprobados"]) == 2 and all(a["firmado"] for a in e1["aprobados"])
        assert e1["paquete"]["disponible"] is True and e1["paquete"]["hasta"]
        # La matrícula sale de la sesión: pedir otra no tiene efecto.
        ajeno = expect(client.get("/dual/alumno/expediente", headers=sesion["C"],
                                  params={"matricula": matriculas["A"]}), 200)
        assert ajeno["alumno"]["matricula"] == matriculas["C"]
        assert matriculas["A"] not in json.dumps(ajeno)
        expect(client.get(f"/dual/carrera/alumnos/{matriculas['A']}/expediente", headers=sesion["C"]), 403)
        assert client.get(f"/dual/carrera/alumnos/{matriculas['A']}/expediente").status_code == 401
        expect(client.get("/dual/carrera/alumnos/000000000/expediente", headers=tutor), 404)
        del_tutor = expect(client.get(f"/dual/carrera/alumnos/{matriculas['A']}/expediente", headers=tutor), 200)
        assert {p["periodo"]["id"] for p in del_tutor["periodos"]} == {str(p1["id"]), str(p2["id"])}
        assert all(p["paquete"]["disponible"] and p["paquete"]["hasta"] is None for p in del_tutor["periodos"])
        # Un alumno dado de baja sin aprobados conserva su expediente con «Sin calificación».
        de_b = expect(client.get(f"/dual/carrera/alumnos/{matriculas['B']}/expediente", headers=coordinator), 200)
        assert de_b["periodos"] == [] or all(p["resumen"]["promedio"] is None for p in de_b["periodos"])
        de_c = expect(client.get(f"/dual/carrera/alumnos/{matriculas['C']}/expediente", headers=tutor), 200)
        nota_c = de_c["periodos"][0]["aprobados"][0]
        assert nota_c["nota"] == 10 and nota_c["declarada_nota"] == 9 and nota_c["corregida"] is True

        # ---------- Descarga de aprobados: bytes idénticos a lo guardado; no aprobados no salen ----------
        reporte_a, version_a = e1["aprobados"][0]["reporte_id"], e1["aprobados"][0]["version"]
        with connect_local() as conn:
            firmado_sha, original_sha = conn.execute(
                "SELECT ds.sha256, d.sha256 FROM reportes_dual rd "
                "JOIN reporte_versiones v ON v.reporte_id=rd.id AND v.numero=%s "
                "JOIN revisiones rv ON rv.version_id=v.id AND rv.decision='Aprobada' "
                "JOIN documentos d ON d.id=v.documento_id JOIN documentos ds ON ds.id=rv.documento_firmado_id "
                "WHERE rd.id=%s", (version_a, reporte_a)).fetchone()
        for documento, esperado in (("firmado", firmado_sha), ("original", original_sha)):
            r = client.get(f"/dual/carrera/reportes/{reporte_a}/versiones/{version_a}/pdf", headers=tutor,
                           params={"documento": documento})
            assert r.status_code == 200 and r.content.startswith(b"%PDF")
            assert hashlib.sha256(r.content).hexdigest() == esperado, documento
        expect(client.get(f"/dual/carrera/reportes/{a1[2]}/versiones/1/pdf", headers=tutor), 404)   # rechazado
        expect(client.get(f"/dual/carrera/reportes/{reporte_a}/versiones/1/pdf", headers=sesion["C"]), 403)
        assert client.get(f"/dual/carrera/reportes/{reporte_a}/versiones/1/pdf").status_code == 401
        expect(client.get(f"/dual/carrera/reportes/{reporte_a}/versiones/1/pdf", headers=tutor,
                          params={"documento": "otro"}), 422)

        # ---------- Paquete del alumno: solo lo suyo, hashes correctos ----------
        def registros():
            with connect_local() as c:
                return c.execute("SELECT count(*) FROM paquetes_archivo").fetchone()[0]

        n0 = registros()
        r = client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": str(p1["id"])})
        assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
        assert r.headers["content-disposition"].startswith("attachment;") and int(r.headers["content-length"]) == len(r.content)
        manifiesto, filas, nombres, sha_manifiesto = leer_zip(r.content)
        assert len(nombres) == 6 and all(matriculas["A"] in n for n in nombres if n.endswith(".pdf"))
        assert [a["matricula"] for a in manifiesto["alumnos"]] == [matriculas["A"]]
        assert not any(matriculas[n] in json.dumps(manifiesto) for n in ("B", "C", "F"))
        assert filas[1][0] == matriculas["A"] and filas[1][7] == "9.00"
        with connect_local() as conn:
            assert registros() == n0 + 1
            alcance, rol, sha_reg = conn.execute(
                "SELECT alcance, rol, manifiesto_sha256 FROM paquetes_archivo ORDER BY generado_en DESC LIMIT 1").fetchone()
        assert (alcance, rol, sha_reg) == ("alumno", "alumno", sha_manifiesto)
        expect(client.get("/dual/alumno/paquete", headers=sesion["C"], params={"periodo_id": str(p2["id"])}), 404)  # sin semanas
        expect(client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": str(p3["id"])}), 409)  # sin finalizar
        expect(client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": "no-es-uuid"}), 422)
        assert client.get("/dual/alumno/paquete", params={"periodo_id": str(p1["id"])}).status_code == 401
        expect(client.get("/dual/alumno/paquete", headers=tutor, params={"periodo_id": str(p1["id"])}), 403)
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=sesion["A"],
                          params={"periodo_id": str(p1["id"])}), 403)

        # ---------- Paquete del tutor por alumno y por carrera ----------
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=coordinator,
                          params={"periodo_id": str(p1["id"])}), 403)
        assert client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}",
                          params={"periodo_id": str(p1["id"])}).status_code == 401
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=tutor,
                          params={"periodo_id": str(p3["id"])}), 409)
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['C']}", headers=tutor,
                          params={"periodo_id": str(p2["id"])}), 404)
        expect(client.get("/dual/carrera/paquetes/alumno/000000000", headers=tutor,
                          params={"periodo_id": str(p1["id"])}), 404)
        r = client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=tutor, params={"periodo_id": str(p2["id"])})
        assert r.status_code == 200
        manifiesto2, filas2, nombres2, _ = leer_zip(r.content)
        assert nom2 in "".join(nombres2) and nom1 not in "".join(nombres2), "El paquete usa el grupo de ese período"

        r = client.get("/dual/carrera/paquetes/carrera/tii", headers=tutor, params={"periodo_id": str(p1["id"])})
        assert r.status_code == 200
        mc, filas_c, nombres_c, sha_c = leer_zip(r.content)
        assert {a["matricula"] for a in mc["alumnos"]} == set(matriculas.values())
        cuerpo = {fila[0]: fila for fila in filas_c[1:]}
        assert cuerpo[matriculas["B"]][7] == "Sin calificación"
        assert cuerpo[matriculas["F"]][1].startswith("'="), "Una celda que empieza con = se protege contra fórmulas"
        assert filas_c[0][0] == "matricula" and all(f[8] == "final" for f in filas_c[1:])
        assert len(nombres_c) == 2 + 2 * 3, nombres_c      # A:2 aprobados, C:1 aprobado; original + firmado
        expect(client.get("/dual/carrera/paquetes/carrera/ZZZ", headers=tutor, params={"periodo_id": str(p1["id"])}), 404)
        expect(client.get("/dual/carrera/paquetes/carrera/TII", headers=tutor, params={"periodo_id": str(p3["id"])}), 409)
        expect(client.get("/dual/carrera/paquetes/carrera/TII", headers=coordinator, params={"periodo_id": str(p1["id"])}), 403)
        with connect_local() as conn:
            alcance, carrera, rol, alumnos, archivos, sha_reg = conn.execute(
                "SELECT alcance, carrera, rol, alumnos, archivos, manifiesto_sha256 FROM paquetes_archivo "
                "ORDER BY generado_en DESC LIMIT 1").fetchone()
            assert (alcance, carrera, rol, alumnos, archivos, sha_reg) == ("carrera", "TII", "tutor", 4, 6, sha_c)
            # El registro es inmutable.
            for sentencia in ("UPDATE paquetes_archivo SET bytes = 1", "DELETE FROM paquetes_archivo"):
                try:
                    conn.execute(sentencia)
                    raise AssertionError(f"La base permitió: {sentencia}")
                except psycopg.errors.RaiseException:
                    conn.rollback()
            try:
                conn.execute("INSERT INTO paquetes_archivo (alcance, periodo_id, rol, generado_por, manifiesto_sha256, "
                             "alumnos, archivos, bytes) VALUES ('carrera', %s, 'tutor', %s, 'xyz', 1, 1, 1)",
                             (p1["id"], tutor_id))
                raise AssertionError("La base aceptó un hash que no es SHA-256")
            except psycopg.errors.CheckViolation:
                conn.rollback()

        # ---------- Un archivo faltante falla sin dejar paquete ni registro ----------
        with connect_local() as conn:
            clave = conn.execute("SELECT clave FROM documentos WHERE sha256=%s", (firmado_sha,)).fetchone()[0]
            n_reg = conn.execute("SELECT count(*) FROM paquetes_archivo").fetchone()[0]
        guardado_original = almacen().leer("documentos", clave)
        almacen().eliminar("documentos", clave)
        try:
            for url, params in ((f"/dual/carrera/paquetes/alumno/{matriculas['A']}", {"periodo_id": str(p1["id"])}),
                                ("/dual/carrera/paquetes/carrera/TII", {"periodo_id": str(p1["id"])})):
                respuesta = client.get(url, headers=tutor, params=params)
                assert respuesta.status_code == 409 and "ZIP" not in respuesta.headers.get("content-type", ""), respuesta.text[:200]
        finally:
            almacen().guardar("documentos", clave, guardado_original)
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM paquetes_archivo").fetchone()[0] == n_reg, "Sin registro si falló"
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=tutor,
                          params={"periodo_id": str(p1["id"])}), 200)

        # ---------- Ventana de una semana del alumno (reloj SIMULADO moviendo la finalización con SQL) ----------
        def finalizada_hace(periodo, intervalo):
            with connect_local() as conn:
                conn.execute("ALTER TABLE ciclos_dual DISABLE TRIGGER ciclos_finalizado_protegido")
                try:
                    conn.execute("UPDATE ciclos_dual SET evaluacion_finalizada_en = now() - %s::interval WHERE id=%s",
                                 (intervalo, periodo["id"]))
                finally:
                    conn.execute("ALTER TABLE ciclos_dual ENABLE TRIGGER ciclos_finalizado_protegido")
                conn.commit()

        finalizada_hace(p1, "6 days 23 hours")
        expect(client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": str(p1["id"])}), 200)
        finalizada_hace(p1, "8 days")
        vencido = expect(client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": str(p1["id"])}), 403)
        assert "disponible" in str(vencido).lower() or "venci" in str(vencido).lower() or "semana" in str(vencido).lower()
        mio = expect(client.get("/dual/alumno/expediente", headers=sesion["A"]), 200)
        e1v = {p["periodo"]["id"]: p for p in mio["periodos"]}[str(p1["id"])]
        assert e1v["paquete"]["disponible"] is False and e1v["paquete"]["motivo"]
        assert len(e1v["aprobados"]) == 2, "El expediente y las notas se conservan después de la ventana"
        # El período 2 sigue dentro de la ventana y el tutor puede generar el de p1 cuando quiera.
        expect(client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": str(p2["id"])}), 200)
        expect(client.get(f"/dual/carrera/paquetes/alumno/{matriculas['A']}", headers=tutor,
                          params={"periodo_id": str(p1["id"])}), 200)

    print("Smoke C08 OK")


if __name__ == "__main__":
    main()
