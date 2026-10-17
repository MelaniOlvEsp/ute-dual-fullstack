"""Smoke C09 con HTTP, PostgreSQL y almacenamiento en disco reales sobre Compose local.

Plantilla común Word + PDF versionada (publicación todo o nada, permisos, descargas, historial e
inmutabilidad), buzón con la política del hilo cerrado de DP-09 D1 (solo lectura, reapertura del
personal, hilo nuevo enlazado, privacidad entre alumnos) y anuncios con la moderación de D2
(eliminación lógica conservada). Datos sintéticos; no se imprimen contraseñas.
"""
from __future__ import annotations

import hashlib
import io
import os
import secrets
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
import psycopg
from psycopg.types.json import Jsonb

from app.domain.periods import construir_periodo, fechas_del_periodo
from app.infrastructure.config.settings import settings
from app.infrastructure.security.jwt_passwords import hash_password
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, BLOQUES, almacen, expect, pdf

TIPO_PRINCIPAL = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def docx(marca: str, extras=None, tipos=None) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   tipos or f'<Types><Override PartName="/word/document.xml" ContentType="{TIPO_PRINCIPAL}"/></Types>')
        z.writestr("word/document.xml", f"<w:document>{marca}</w:document>")
        for nombre, datos in (extras or {}).items():
            z.writestr(nombre, datos)
    return memoria.getvalue()


def archivos_de_plantilla() -> int:
    return len(almacen().listar("plantillas"))


def main():
    suffix = secrets.token_hex(5)
    password = "C09a" + secrets.token_urlsafe(18)
    coordinator_email = f"c09.{suffix}@ute.edu.mx"
    tutor_emails = [f"t09a.{suffix}@ute.edu.mx", f"t09b.{suffix}@ute.edu.mx"]
    plan, zone = str(secrets.randbelow(90) + 10), secrets.randbelow(30000) + 1
    matriculas = {n: str(secrets.randbelow(900000000) + 100000000) for n in ("A", "B")}

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C09")

    with connect_local() as conn:
        usados = {f[0] for f in conn.execute("SELECT cuatrimestre FROM ciclos_dual").fetchall()}
        while True:
            anio, mes = secrets.randbelow(44) + 1980, BLOQUES[secrets.randbelow(3)][0]
            label = construir_periodo(mes, anio)
            if label not in usados:
                break
        inicio, fin = fechas_del_periodo(mes, anio)
        periodo_id = conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) VALUES (%s,%s,%s,%s) RETURNING id",
            (label, label, inicio, fin)).fetchone()[0]
        conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (coordinator_email,))
        for email in tutor_emails:
            conn.execute("INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                         (email, "Tutor sintético C09", hash_password(password), Jsonb({"tutor_academico": True})))
        conn.commit()
        ids = {e: conn.execute("SELECT id FROM usuarios WHERE email=%s", (e,)).fetchone()[0]
               for e in [coordinator_email] + tutor_emails}

    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        coordinator, tutor, tutor2 = (login(e, password) for e in [coordinator_email] + tutor_emails)
        grupo = expect(client.post("/dual/carrera/grupos", headers=tutor, json={
            "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A", "turno": "Matutino",
            "plan": plan, "zona": zone}), 201)
        filas = "".join(f"{m},Alumno sintético C09 {n}\n" for n, m in matriculas.items())
        expect(client.post(f"/dual/carrera/grupos/{grupo['id']}/alumnos", headers=tutor, data={"periodo_id": str(periodo_id)},
                           files={"file": ("a.csv", ("matricula,nombre\n" + filas).encode(), "text/csv")}), 200)
        pw_alumno = "C09s" + secrets.token_urlsafe(18)
        sesion = {}
        for n, m in matriculas.items():
            expect(client.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": pw_alumno}), 201)
            sesion[n] = login(f"{m}@ute.edu.mx", pw_alumno)
        alumno_a, alumno_b = sesion["A"], sesion["B"]

        # ================= Plantilla común Word + PDF =================
        antes = expect(client.get("/dual/plantillas/vigente", headers=alumno_a), 200)["vigente"]
        n0 = antes["numero"] if antes else 0
        with connect_local() as conn:
            filas_antes = conn.execute("SELECT count(*) FROM plantillas_version").fetchone()[0]
        archivos_antes = archivos_de_plantilla()
        w1, p1 = docx("version A"), pdf("plantilla A", 2)

        def publicar(headers, word=None, pdf_=None, **extra):
            archivos = {}
            if word is not None:
                archivos["word"] = word
            if pdf_ is not None:
                archivos["pdf"] = pdf_
            return client.post("/dual/plantillas/", headers=headers, files=archivos, data=extra)

        ok = lambda: ("plantilla.docx", w1, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        okpdf = lambda: ("plantilla.pdf", p1, "application/pdf")
        # Permisos: solo el coordinador publica; todos los roles autenticados consultan y descargan.
        for headers in (tutor, alumno_a):
            assert publicar(headers, ok(), okpdf()).status_code == 403
            assert client.get("/dual/plantillas/", headers=headers).status_code == 403
        assert client.post("/dual/plantillas/", files={"word": ok(), "pdf": okpdf()}).status_code == 401
        assert client.get("/dual/plantillas/vigente").status_code == 401
        assert client.get("/dual/plantillas/1/word").status_code == 401
        expect(client.get("/dual/plantillas/vigente", headers=tutor), 200)

        # Cargas inválidas: nada se publica ni queda en disco (todo o nada).
        malas = [
            (("a.docx", b"MZ no es word", "application/octet-stream"), okpdf(), 422),
            (("a.docx", docx("macro", extras={"word/vbaProject.bin": b"x"}), "application/octet-stream"), okpdf(), 422),
            (("a.docx", docx("maco", tipos='<Types><Override ContentType="application/vnd.ms-word.document.macroEnabled.main+xml"/></Types>'), "a/b"), okpdf(), 422),
            (("a.docx", docx("ruta", extras={"../evil.xml": b"x"}), "a/b"), okpdf(), 422),
            (("a.docx", docx("bomba", extras={"word/relleno.xml": b"0" * (6 * 1024 * 1024)}), "a/b"), okpdf(), 422),
            (("a.doc", w1, "a/b"), okpdf(), 422),
            (ok(), ("a.pdf", b"%PDF-1.4 danado", "application/pdf"), 422),
            (ok(), ("a.pdf", b"no es pdf", "application/pdf"), 422),
            (ok(), ("../../a.txt", p1, "text/plain"), 422),
            (("a.docx", b"x" * (10 * 1024 * 1024 + 1), "a/b"), okpdf(), 413),
        ]
        for word, pdf_, estado in malas:
            r = publicar(coordinator, word, pdf_)
            assert r.status_code == estado, (word[0], r.status_code, r.text[:160])
        assert publicar(coordinator, ok()).status_code == 422, "Falta uno de los dos archivos"
        assert publicar(coordinator, pdf_=okpdf()).status_code == 422
        assert publicar(coordinator, ok(), okpdf(), nota="x" * 201).status_code == 422
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM plantillas_version").fetchone()[0] == filas_antes
        assert archivos_de_plantilla() == archivos_antes, "Un rechazo no deja archivos sueltos"
        despues = expect(client.get("/dual/plantillas/vigente", headers=alumno_a), 200)["vigente"]
        assert (despues or {}).get("numero", 0) == n0

        # Publicación válida: versión n0+1 vigente, descargas byte a byte y nombres generados.
        r = publicar(coordinator, ok(), okpdf(), nota="Primera de la prueba")
        assert r.status_code == 201, r.text[:200]
        v1 = r.json()
        assert v1["numero"] == n0 + 1 and v1["vigente"] is True and v1["pdf"]["paginas"] == 2
        assert archivos_de_plantilla() == archivos_antes + 2
        vigente = expect(client.get("/dual/plantillas/vigente", headers=alumno_b), 200)["vigente"]
        assert vigente["numero"] == v1["numero"] and "clave" not in str(vigente)
        for headers in (alumno_a, tutor, coordinator):
            for tipo, esperado, ext in (("word", w1, "docx"), ("pdf", p1, "pdf")):
                d = client.get(f"/dual/plantillas/{v1['numero']}/{tipo}", headers=headers)
                assert d.status_code == 200 and d.content == esperado, (tipo, d.status_code)
                assert f'filename="Plantilla_Reporte_Dual_v{v1["numero"]}.{ext}"' in d.headers["content-disposition"]
                assert d.headers["content-disposition"].startswith("attachment")
        assert client.get(f"/dual/plantillas/{v1['numero']}/exe", headers=alumno_a).status_code == 422
        assert client.get("/dual/plantillas/999999/word", headers=alumno_a).status_code == 404

        # Una versión nueva reemplaza la vigente sin tocar la anterior (inmutables).
        w2, p2 = docx("version B"), pdf("plantilla B", 1)
        r = publicar(coordinator, ("n.docx", w2, "a/b"), ("n.pdf", p2, "application/pdf"))
        assert r.status_code == 201 and r.json()["numero"] == v1["numero"] + 1
        historial = expect(client.get("/dual/plantillas/", headers=coordinator), 200)
        assert [v["numero"] for v in historial][:2] == [v1["numero"] + 1, v1["numero"]]
        assert [v["vigente"] for v in historial].count(True) == 1 and historial[0]["vigente"] is True
        viejo = client.get(f"/dual/plantillas/{v1['numero']}/word", headers=alumno_a)
        assert viejo.content == w1 and hashlib.sha256(viejo.content).hexdigest() == historial[1]["word"]["sha256"]
        assert client.get(f"/dual/plantillas/{v1['numero']+1}/pdf", headers=alumno_a).content == p2
        with connect_local() as conn:
            for sentencia in ("UPDATE plantillas_version SET nota = 'x' WHERE numero = %s",
                              "UPDATE plantillas_version SET vigente = TRUE WHERE numero = %s",
                              "DELETE FROM plantillas_version WHERE numero = %s"):
                try:
                    conn.execute(sentencia, (v1["numero"],))
                    raise AssertionError(f"La base permitió: {sentencia[:40]}")
                except psycopg.errors.RaiseException:
                    conn.rollback()
                except psycopg.errors.UniqueViolation:
                    conn.rollback()

        # ================= Buzón: política del hilo cerrado (D1) =================
        t1 = expect(client.post("/foro/buzon/", headers=alumno_a, json={
            "area": "dual", "asunto": "Duda del reporte", "mensaje": "¿Cómo cuento las horas?"}), 201)["id"]
        assert t1 and client.get(f"/foro/buzon/{t1}", headers=alumno_b).status_code == 404, "Otro alumno no ve el hilo"
        assert client.post(f"/foro/buzon/{t1}/respuestas", headers=alumno_b, json={"texto": "intruso"}).status_code == 404
        assert client.patch(f"/foro/buzon/{t1}/reabrir", headers=alumno_b).status_code == 403
        expect(client.post(f"/foro/buzon/{t1}/respuestas", headers=tutor, json={"texto": "Cuenta las horas del convenio."}), 201)
        expect(client.post(f"/foro/buzon/{t1}/respuestas", headers=coordinator, json={"texto": "Confirmado."}), 201)
        expect(client.post(f"/foro/buzon/{t1}/respuestas", headers=alumno_a, json={"texto": "Gracias."}), 201)
        detalle = expect(client.get(f"/foro/buzon/{t1}", headers=alumno_a), 200)
        assert [r["autor_rol"] for r in detalle["respuestas"]] == ["Tutor académico", "Coordinación Dual", "Alumno"]
        assert detalle["hilo_anterior_id"] is None
        expect(client.patch(f"/foro/buzon/{t1}/leido", headers=tutor), 200)
        expect(client.patch(f"/foro/buzon/{t1}/cerrar", headers=tutor), 200)
        assert client.patch(f"/foro/buzon/{t1}/cerrar", headers=alumno_a).status_code == 403
        # Hilo cerrado: solo lectura para todos; marcar leído no lo reabre.
        for headers in (alumno_a, tutor, coordinator):
            r = client.post(f"/foro/buzon/{t1}/respuestas", headers=headers, json={"texto": "¿sigue abierto?"})
            assert r.status_code == 409 and "cerrado" in r.text.lower(), (r.status_code, r.text[:160])
        expect(client.patch(f"/foro/buzon/{t1}/leido", headers=coordinator), 200)
        assert expect(client.get(f"/foro/buzon/{t1}", headers=alumno_a), 200)["estado"] == "Cerrado"
        with connect_local() as conn:
            try:
                conn.execute("INSERT INTO buzon_respuestas (mensaje_id, autor_id, autor_rol, texto) VALUES (%s,%s,'x','x')",
                             (t1, ids[tutor_emails[0]]))
                raise AssertionError("La base aceptó una respuesta en un hilo cerrado")
            except psycopg.errors.RaiseException:
                conn.rollback()
            assert conn.execute("SELECT count(*) FROM buzon_respuestas WHERE mensaje_id=%s", (t1,)).fetchone()[0] == 3
        # El alumno abre un hilo nuevo enlazado; no puede enlazar uno ajeno ni uno abierto.
        t2 = expect(client.post("/foro/buzon/", headers=alumno_a, json={
            "area": "dual", "asunto": "Seguimiento de la duda", "mensaje": "Sigo con lo de las horas",
            "hilo_anterior_id": t1}), 201)
        assert t2["hilo_anterior_id"] == t1 and t2["estado"] == "Enviado"
        assert expect(client.get(f"/foro/buzon/{t2['id']}", headers=tutor), 200)["hilo_anterior_id"] == t1
        assert client.post("/foro/buzon/", headers=alumno_b, json={
            "area": "dual", "asunto": "Intento ajeno", "mensaje": "x", "hilo_anterior_id": t1}).status_code == 404
        r = client.post("/foro/buzon/", headers=alumno_a, json={
            "area": "dual", "asunto": "Enlace a uno abierto", "mensaje": "x", "hilo_anterior_id": t2["id"]})
        assert r.status_code == 409, r.text[:160]
        # Solo el personal reabre, de forma explícita e idempotente; después el alumno puede responder.
        r = client.patch(f"/foro/buzon/{t1}/reabrir", headers=tutor)
        assert r.status_code == 200 and r.json()["repetido"] is False, r.text
        assert client.patch(f"/foro/buzon/{t1}/reabrir", headers=coordinator).json()["repetido"] is True
        assert expect(client.get(f"/foro/buzon/{t1}", headers=alumno_a), 200)["estado"] == "Leido"
        expect(client.post(f"/foro/buzon/{t1}/respuestas", headers=alumno_a, json={"texto": "Una última pregunta"}), 201)
        assert client.patch(f"/foro/buzon/{t1}/reabrir", headers=alumno_a).status_code == 403
        assert client.patch(f"/foro/buzon/{t1}/reabrir").status_code == 401

        # ================= Anuncios: moderación y conservación (D2) =================
        assert client.post("/foro/publicaciones", headers=alumno_a, json={"contenido": "no autorizado"}).status_code == 403
        p_tutor = expect(client.post("/foro/publicaciones", headers=tutor, json={"contenido": "Aviso del tutor A"}), 201)["id"]
        p_tutor2 = expect(client.post("/foro/publicaciones", headers=tutor2, json={"contenido": "Aviso del tutor B"}), 201)["id"]
        p_coord = expect(client.post("/foro/publicaciones", headers=coordinator, json={"contenido": "Aviso de coordinación"}), 201)["id"]

        def visibles(headers):
            return {p["id"] for p in expect(client.get("/foro/publicaciones?limit=100", headers=headers), 200)}

        assert {p_tutor, p_tutor2, p_coord} <= visibles(alumno_a)
        assert client.delete(f"/foro/publicaciones/{p_tutor}", headers=tutor2).status_code == 403, "Otro tutor no modera"
        assert client.delete(f"/foro/publicaciones/{p_tutor}", headers=alumno_a).status_code == 403
        assert client.delete(f"/foro/publicaciones/{p_tutor}").status_code == 401
        expect(client.delete(f"/foro/publicaciones/{p_tutor}", headers=tutor), 200)             # el autor
        expect(client.delete(f"/foro/publicaciones/{p_tutor2}", headers=coordinator), 200)      # el coordinador modera
        for pid in (p_tutor, p_tutor2):
            assert pid not in visibles(alumno_a) and pid not in visibles(tutor)
        assert p_coord in visibles(alumno_b)
        assert client.delete(f"/foro/publicaciones/{p_tutor}", headers=tutor).status_code == 404, "Ya eliminado"
        assert client.post(f"/foro/publicaciones/{p_tutor}/reaccion", headers=alumno_a, json={"tipo": "like"}).status_code == 404
        with connect_local() as conn:
            fila = conn.execute("SELECT contenido, eliminada_por, eliminada_en FROM foro_publicaciones WHERE id=%s", (p_tutor2,)).fetchone()
            assert fila[0] == "Aviso del tutor B" and fila[1] == ids[coordinator_email] and fila[2] is not None, "Se conserva"
            fila = conn.execute("SELECT eliminada_por FROM foro_publicaciones WHERE id=%s", (p_tutor,)).fetchone()
            assert fila[0] == ids[tutor_emails[0]]
            for sentencia in ("UPDATE foro_publicaciones SET contenido = 'editado' WHERE id = %s",
                              "UPDATE foro_publicaciones SET eliminada_en = NULL, eliminada_por = NULL WHERE id = %s"):
                try:
                    conn.execute(sentencia, (p_tutor,))
                    raise AssertionError(f"La base permitió: {sentencia[:45]}")
                except psycopg.errors.RaiseException:
                    conn.rollback()
        expect(client.delete(f"/foro/publicaciones/{p_coord}", headers=coordinator), 200)

    print("Smoke C09 OK")


if __name__ == "__main__":
    main()
