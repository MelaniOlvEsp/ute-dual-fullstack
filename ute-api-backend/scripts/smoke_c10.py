"""Smoke C10: recorrido integral con coordinador, dos tutores y dos alumnos de grupos y períodos distintos.

HTTP, PostgreSQL y almacenamiento (Drive o la carpeta local de regresión) reales, con datos sintéticos. Recorre
el producto completo en un solo guion (grupo, incorporación, foro, plantilla, entregas, rechazo y reenvío,
aprobación con firma en la celda, expediente, cierre de recepción con una entrega pendiente, finalización,
segundo período sin efecto sobre el primero, descarga de períodos anteriores, paquete, depuración con gracia y
buzón) y, dentro de él, los controles negativos: acceso cruzado entre alumnos, el tutor intentando el cierre, un
archivo ausente del almacenamiento, un PDF corrupto, el envío duplicado concurrente y el buzón con el hilo cerrado.

Preparación documentada (igual que C07 y C08B): los dos períodos son pasados y distintos de cualquier otro (la API
no abre períodos terminados), así que se insertan y se marcan como abiertos con SQL; todo lo demás es por la API.
No se imprimen credenciales; los datos sintéticos se conservan.
"""
from __future__ import annotations

import hashlib
import io
import os
import secrets
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from psycopg.types.json import Jsonb

import smoke_periodos
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from app.infrastructure.security.jwt_passwords import hash_password
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, BLOQUES, almacen, expect, pdf
from smoke_c06 import firma_png, reporte_formato

TIPO_WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def docx(marca: str) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", f'<Types><Override PartName="/word/document.xml" ContentType="{TIPO_WORD}"/></Types>')
        z.writestr("word/document.xml", f"<w:document>{marca}</w:document>")
    return memoria.getvalue()


def periodo_pasado(conn, usados):
    while True:
        anio, mes = secrets.randbelow(400) + 1500, BLOQUES[secrets.randbelow(3)][0]
        label = construir_periodo(mes, anio)
        if label in usados:
            continue
        usados.add(label)
        inicio, fin = fechas_del_periodo(mes, anio)
        pid = conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) VALUES (%s,%s,%s,%s) RETURNING id",
            (label, label, inicio, fin)).fetchone()[0]
        return {"id": pid, "label": label, "inicio": inicio}


def main():
    suffix = secrets.token_hex(5)
    password = "C10a" + secrets.token_urlsafe(18)
    coord_email, t1_email, t2_email = (f"{p}10.{suffix}@ute.edu.mx" for p in ("c", "ta", "tb"))
    plan, zona = str(secrets.randbelow(90) + 10), secrets.randbelow(30000) + 1
    matriculas = {n: str(secrets.randbelow(900000000) + 100000000) for n in ("A", "B")}

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coord_email, "Coordinador sintético C10")
    with connect_local() as conn:
        usados = {f[0] for f in conn.execute("SELECT cuatrimestre FROM ciclos_dual").fetchall()}
        p1, p2 = periodo_pasado(conn, usados), periodo_pasado(conn, usados)
        conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (coord_email,))
        for email in (t1_email, t2_email):
            conn.execute("INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                         (email, "Tutor sintético C10", hash_password(password), Jsonb({"tutor_academico": True})))
        conn.commit()

    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as c:
        def login(email, secreto):
            d = expect(c.post("/auth/login", json={"email": email, "password": secreto}), 200)
            return {"Authorization": "Bearer " + d["access_token"]}

        coord, t1, t2 = (login(e, password) for e in (coord_email, t1_email, t2_email))
        for t in (t1, t2):
            expect(c.post("/dual/tutor/firma", headers=t, files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)

        # ---------- Grupos, alumnos e incorporación: A (TII, período 1) y B (MER, período 2) ----------
        def grupo(carrera):
            return expect(c.post("/dual/carrera/grupos", headers=t1, json={
                "carrera": carrera, "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A", "turno": "Matutino",
                "plan": plan, "zona": zona}), 201)

        empresa = expect(c.post("/dual/tutor/empresas", headers=t1, json={"nombre": f"Empresa C10 {suffix}"}), 201)
        for nombre, g, p in (("A", grupo("TII"), p1), ("B", grupo("MER"), p2)):
            m = matriculas[nombre]
            expect(c.post(f"/dual/carrera/grupos/{g['id']}/alumnos", headers=t1, data={"periodo_id": str(p["id"])},
                          files={"file": ("a.csv", f"matricula,nombre\n{m},Alumno sintético C10 {nombre}\n".encode(), "text/csv")}), 200)
            inicio = calendar.lunes_de(p["inicio"] + timedelta(days=14))
            expect(c.patch(f"/dual/tutor/alumnos/{m}", headers=t1, json={
                "alumno_dual": True, "empresa_id": empresa["id"], "fecha_inicio": inicio.isoformat()}), 200)
            expect(c.patch(f"/dual/tutor/alumnos/{m}", headers=t1, json={
                "alumno_dual": False, "fecha_baja": (inicio + timedelta(days=27)).isoformat()}), 200)
        pw_alumno = "C10s" + secrets.token_urlsafe(18)
        sesion = {}
        for nombre, m in matriculas.items():
            expect(c.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": pw_alumno}), 201)
            sesion[nombre] = login(f"{m}@ute.edu.mx", pw_alumno)
        a, b = sesion["A"], sesion["B"]

        def semanas(nombre, p):
            return sorted((o for o in expect(c.get("/dual/alumno/obligaciones", headers=sesion[nombre]), 200)
                           if o["periodo"] == p["label"]), key=lambda o: o["ordinal"])

        def entregar(nombre, o, nota, contenido=None, esperado=201, nombre_archivo="reporte.pdf"):
            r = c.post(f"/dual/alumno/obligaciones/{o['id']}/entrega", headers=sesion[nombre],
                       data={"fecha_inicio": o["inicio_efectivo"], "fecha_fin": o["fin_efectivo"], "calificacion_alumno": str(nota)},
                       files={"archivo": (nombre_archivo, contenido if contenido is not None else reporte_formato(f"{nombre} {o['ordinal']}")[0], "application/pdf")})
            assert r.status_code == esperado, (nombre, esperado, r.status_code, r.text[:200])
            return r.json()

        def revisar(headers, reporte, version=1, esperado=200, **cuerpo):
            r = c.post(f"/dual/tutor/reportes/{reporte}/versiones/{version}/revision", headers=headers, json=cuerpo)
            assert r.status_code == esperado, (esperado, r.status_code, r.text[:200])
            return r.json()

        def abrir_pasado(p):
            smoke_periodos.cerrar_abiertos(c, coord)
            with connect_local() as conn:
                conn.execute("UPDATE ciclos_dual SET abierto=TRUE WHERE id=%s", (p["id"],))
                conn.commit()

        def documentos():
            with connect_local() as conn:
                return conn.execute("SELECT count(*) FROM documentos").fetchone()[0]

        # ---------- 1. Foro y plantilla (todos los roles ingresan y descargan) ----------
        publicacion = expect(c.post("/foro/publicaciones", headers=coord, json={"contenido": f"Bienvenida C10 {suffix}"}), 201)["id"]
        assert publicacion in {p["id"] for p in expect(c.get("/foro/publicaciones?limit=100", headers=a), 200)}
        word, plantilla_pdf = docx(suffix), pdf("plantilla c10")
        v = expect(c.post("/dual/plantillas/", headers=coord, files={
            "word": ("p.docx", word, "application/octet-stream"), "pdf": ("p.pdf", plantilla_pdf, "application/pdf")},
            data={"nota": "C10"}), 201)
        assert expect(c.get("/dual/plantillas/vigente", headers=a), 200)["vigente"]["numero"] == v["numero"]
        assert c.get(f"/dual/plantillas/{v['numero']}/word", headers=a).content == word
        assert c.get(f"/dual/plantillas/{v['numero']}/pdf", headers=b).content == plantilla_pdf

        # ---------- 2. Período 1, alumno A: entregas, rechazo, reenvío y aprobación con firma ----------
        abrir_pasado(p1)
        sa = semanas("A", p1)
        assert len(sa) == 4 and all(o["puede_entregar"] for o in sa)
        # Negativo: PDF corrupto, protegido o de otro tipo no dejan documentos ni reportes.
        antes = documentos()
        valido = pdf("válido")
        for mal in (b"", b"no es un pdf", b"%PDF-1.7\nbasura", valido[: len(valido) // 2]):
            entregar("A", sa[0], 8, contenido=mal, esperado=422)
        entregar("A", sa[0], 8, contenido=valido, esperado=422, nombre_archivo="imagen.png")
        assert documentos() == antes, "Una entrega inválida no deja documentos"

        r0 = entregar("A", sa[0], 5)
        assert (r0["version"], r0["repetido"]) == (1, False)
        revisar(t1, r0["reporte_id"], decision="Rechazada", observacion="Falta la firma de la empresa")
        r0v2 = entregar("A", sa[0], 8)                       # reenvío tras el rechazo
        assert r0v2["reporte_id"] == r0["reporte_id"] and r0v2["version"] == 2
        aprobada0 = revisar(t1, r0["reporte_id"], version=2, decision="Aprobada")
        assert aprobada0["estado"] == "Aprobada" and aprobada0.get("firma") == "celda", aprobada0
        r1 = entregar("A", sa[1], 10)
        assert revisar(t1, r1["reporte_id"], decision="Aprobada").get("firma") == "celda"
        r2 = entregar("A", sa[2], 9)                         # queda pendiente: se revisa después del cierre

        # Negativo: envío duplicado concurrente: solo uno crea el reporte.
        distintos = [reporte_formato(f"carrera {i}")[0] for i in range(6)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            codigos = sorted(x.status_code for x in pool.map(lambda contenido: c.post(
                f"/dual/alumno/obligaciones/{sa[3]['id']}/entrega", headers=a,
                data={"fecha_inicio": sa[3]["inicio_efectivo"], "fecha_fin": sa[3]["fin_efectivo"], "calificacion_alumno": "7"},
                files={"archivo": ("reporte.pdf", contenido, "application/pdf")}), distintos))
        assert codigos == [201] + [409] * 5, codigos
        with connect_local() as conn:
            r3 = conn.execute("SELECT id FROM reportes_dual WHERE obligacion_id=%s", (sa[3]["id"],)).fetchall()
        assert len(r3) == 1
        revisar(t2, r3[0][0], decision="Rechazada", observacion="Nota ilegible")   # el otro tutor también revisa

        # ---------- 3. Expediente e historial; descarga de un período con un archivo ausente ----------
        mio = expect(c.get("/dual/alumno/expediente", headers=a), 200)
        e1 = next(p for p in mio["periodos"] if p["periodo"]["id"] == str(p1["id"]))
        assert len(e1["aprobados"]) == 2 and all(x["firmado"] for x in e1["aprobados"])
        with connect_local() as conn:   # el historial conserva ambas versiones y sus decisiones
            assert conn.execute("SELECT v.numero, rv.decision FROM reporte_versiones v LEFT JOIN revisiones rv ON rv.version_id=v.id "
                                "WHERE v.reporte_id=%s ORDER BY v.numero", (r0["reporte_id"],)).fetchall() == [(1, "Rechazada"), (2, "Aprobada")]
        aprobado = e1["aprobados"][0]
        with connect_local() as conn:
            clave, sha_firmado = conn.execute(
                "SELECT ds.clave, ds.sha256 FROM reportes_dual rd JOIN reporte_versiones v ON v.reporte_id=rd.id AND v.numero=%s "
                "JOIN revisiones rv ON rv.version_id=v.id AND rv.decision='Aprobada' JOIN documentos ds ON ds.id=rv.documento_firmado_id "
                "WHERE rd.id=%s", (aprobado["version"], aprobado["reporte_id"])).fetchone()
        ruta_pdf = f"/dual/carrera/reportes/{aprobado['reporte_id']}/versiones/{aprobado['version']}/pdf"
        descarga = c.get(ruta_pdf, headers=t1, params={"documento": "firmado"})
        assert descarga.status_code == 200 and hashlib.sha256(descarga.content).hexdigest() == sha_firmado
        # Negativo: el archivo desaparece del almacenamiento; se informa con claridad y nunca se entrega otra cosa.
        contenido_firmado = almacen().leer("documentos", clave)
        almacen().eliminar("documentos", clave)
        try:
            ausente = c.get(ruta_pdf, headers=t1, params={"documento": "firmado"})
            assert ausente.status_code in (404, 409, 503) and not ausente.content.startswith(b"%PDF"), ausente.status_code
            assert not any(s in ausente.text.lower() for s in ("drive", "token", "googleapis")), "Error sin detalles internos"
        finally:
            almacen().guardar("documentos", clave, contenido_firmado)   # se repone el mismo contenido
        assert c.get(ruta_pdf, headers=t1, params={"documento": "firmado"}).content == contenido_firmado

        # ---------- 4. Cierre de recepción con una entrega pendiente (período 1) ----------
        id1 = str(p1["id"])
        for headers in (t1, t2, a):                          # Negativo: el tutor y el alumno no cierran ni finalizan
            for ruta in ("cierre-recepcion", "finalizacion"):
                assert c.post(f"/dual/tutor/periodos/{id1}/{ruta}", headers=headers, json={"confirmar": True}).status_code == 403
        resumen = expect(c.get(f"/dual/tutor/periodos/{id1}/resumen", headers=t1), 200)
        assert resumen["conteos"]["pendientes_revision"] == 1 and resumen["puede_cerrar_recepcion"] is True
        expect(c.post(f"/dual/tutor/periodos/{id1}/finalizacion", headers=coord, json={"confirmar": True}), 409)  # sin cerrar
        cierre = expect(c.post(f"/dual/tutor/periodos/{id1}/cierre-recepcion", headers=coord, json={"confirmar": True}), 200)
        assert cierre["repetido"] is False and cierre["periodo"]["recepcion"] == "cerrada"
        entregar("A", sa[3], 6, esperado=409)                # reenviar el rechazado con la recepción cerrada: bloqueado
        sin = expect(c.post(f"/dual/tutor/periodos/{id1}/finalizacion", headers=coord, json={"confirmar": True}), 409)
        assert "pendiente de revisión" in str(sin)
        assert revisar(t2, r2["reporte_id"], decision="Aprobada")["estado"] == "Aprobada"   # revisión posterior al cierre
        final = expect(c.post(f"/dual/tutor/periodos/{id1}/finalizacion", headers=coord, json={"confirmar": True}), 200)
        fa = next(x for x in final["alumnos"] if x["matricula"] == matriculas["A"])
        assert (fa["promedio"], fa["suma"], fa["aprobados"], fa["definitivo"]) == ("9.00", 27, 3, True), fa

        # ---------- 5. Segundo período (alumno B): el primero no cambia ----------
        def instantanea():
            with connect_local() as conn:
                cierres = conn.execute("SELECT matricula, suma, cantidad, promedio FROM cierres_alumno_periodo "
                                       "WHERE periodo_id=%s ORDER BY matricula", (p1["id"],)).fetchall()
            exp = expect(c.get("/dual/alumno/expediente", headers=a), 200)
            return (expect(c.get(f"/dual/tutor/periodos/{id1}/resumen", headers=t1), 200), cierres,
                    [p for p in exp["periodos"] if p["periodo"]["id"] == id1])

        primero = instantanea()
        abrir_pasado(p2)
        sb = semanas("B", p2)
        b1, b2 = entregar("B", sb[0], 7), entregar("B", sb[1], 9)
        for rid in (b1["reporte_id"], b2["reporte_id"]):
            revisar(t1, rid, decision="Aprobada")
        smoke_periodos.cerrar(c, coord, str(p2["id"]))
        fb = next(x for x in expect(c.post(f"/dual/tutor/periodos/{p2['id']}/finalizacion", headers=coord,
                                           json={"confirmar": True}), 200)["alumnos"] if x["matricula"] == matriculas["B"])
        assert (fb["promedio"], fb["suma"]) == ("8.00", 16), fb
        assert instantanea() == primero, "Abrir y finalizar un segundo período no modifica el primero"

        # ---------- 6. Acceso cruzado A/B (negativos) ----------
        exp_b = expect(c.get("/dual/alumno/expediente", headers=b), 200)
        assert {p["periodo"]["id"] for p in exp_b["periodos"]} == {str(p2["id"])} and matriculas["A"] not in str(exp_b)
        assert matriculas["B"] not in str(expect(c.get("/dual/alumno/expediente", headers=a), 200))
        for ruta, headers in ((f"/dual/alumno/reportes/{b1['reporte_id']}/versiones/1/pdf", a),
                              (f"/dual/alumno/reportes/{r0['reporte_id']}/versiones/2/pdf", b),
                              (f"/dual/carrera/alumnos/{matriculas['A']}/expediente", b),
                              (f"/dual/carrera/reportes/{b1['reporte_id']}/versiones/1/pdf", a),
                              (f"/dual/carrera/paquetes/alumno/{matriculas['B']}?periodo_id={p2['id']}", a)):
            assert c.get(ruta, headers=headers).status_code in (403, 404), ruta
        assert c.get("/dual/alumno/paquete", headers=a, params={"periodo_id": str(p2["id"])}).status_code == 404
        assert c.get("/dual/alumno/paquete", headers=b, params={"periodo_id": id1}).status_code == 404

        # ---------- 7. Períodos anteriores: descargas, paquete y depuración con gracia ----------
        propio = c.get(f"/dual/alumno/reportes/{aprobado['reporte_id']}/versiones/{aprobado['version']}/pdf", headers=a)
        assert propio.status_code == 200 and propio.content.startswith(b"%PDF")
        zip_a = c.get("/dual/alumno/paquete", headers=a, params={"periodo_id": id1})
        assert zip_a.status_code == 200 and zip_a.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(zip_a.content)) as z:
            assert sum(n.endswith(".pdf") for n in z.namelist()) == 6 and not any(matriculas["B"] in n for n in z.namelist())
        zip_tii = c.get("/dual/carrera/paquetes/carrera/TII", headers=t1, params={"periodo_id": id1})
        assert zip_tii.status_code == 200
        frase = f"DEPURAR {p1['label']} TII"
        purga = expect(c.post(f"/dual/carrera/periodos/{id1}/purgas", headers=t1,
                              json={"carrera": "TII", "confirmar": True, "frase": frase}), 200)
        assert purga["purga"]["estado"] == "programada"
        assert c.get(ruta_pdf, headers=t1, params={"documento": "firmado"}).status_code == 200, "La gracia no elimina nada"
        cancelada = expect(c.post(f"/dual/carrera/periodos/{id1}/purgas/{purga['purga']['id']}/cancelacion", headers=t1), 200)
        assert cancelada["purga"]["estado"] == "cancelada"

        # ---------- 8. Buzón: conversación completa y política del hilo cerrado ----------
        hilo = expect(c.post("/foro/buzon/", headers=a, json={"area": "dual", "asunto": "Duda de horas", "mensaje": "¿Cómo cuento las horas?"}), 201)["id"]
        assert c.get(f"/foro/buzon/{hilo}", headers=b).status_code == 404, "Otro alumno no ve el hilo"
        expect(c.post(f"/foro/buzon/{hilo}/respuestas", headers=t1, json={"texto": "Cuenta las del convenio."}), 201)
        expect(c.post(f"/foro/buzon/{hilo}/respuestas", headers=coord, json={"texto": "Confirmado."}), 201)
        expect(c.patch(f"/foro/buzon/{hilo}/cerrar", headers=t1), 200)
        for headers in (a, t1, coord):
            assert c.post(f"/foro/buzon/{hilo}/respuestas", headers=headers, json={"texto": "¿sigue abierto?"}).status_code == 409
        nuevo = expect(c.post("/foro/buzon/", headers=a, json={"area": "dual", "asunto": "Seguimiento", "mensaje": "Sigo con la duda",
                                                               "hilo_anterior_id": hilo}), 201)
        assert nuevo["hilo_anterior_id"] == hilo
        assert c.patch(f"/foro/buzon/{hilo}/reabrir", headers=a).status_code == 403
        expect(c.patch(f"/foro/buzon/{hilo}/reabrir", headers=t2), 200)
        expect(c.post(f"/foro/buzon/{hilo}/respuestas", headers=a, json={"texto": "Una última pregunta"}), 201)

    print("PASS C10: recorrido integral (foro, plantilla, entregas, rechazo y reenvío, firma en la celda, expediente, cierre con "
          "pendiente, finalización 9.00 y 8.00, segundo período sin efecto en el primero, paquete, depuración con gracia, buzón) "
          "y negativos (acceso cruzado, cierre por tutor, archivo ausente, PDF corrupto, envío concurrente, hilo cerrado). "
          f"HTTP, PostgreSQL y almacenamiento {almacen().nombre} REALES. Móvil físico y hospedaje: NO_VERIFICADOS. Datos sintéticos conservados.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f"FAIL C10: {exc}", file=sys.stderr)
        raise SystemExit(1)
