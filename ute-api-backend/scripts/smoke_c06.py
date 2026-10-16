"""Smoke C06 con HTTP, PostgreSQL y almacenamiento en disco reales sobre Compose local.

Revisión por versión: corrección trazable de fechas y nota, rechazo con observación, reenvío,
aprobación con firma estampada en la celda del tutor (respaldo: hoja adicional), original y firmado
conservados, versión obsoleta, concurrencia entre tutores, fallos inyectados contra la base real,
permisos y revisión con la recepción cerrada. Datos sintéticos; no se imprimen contraseñas.
"""
from __future__ import annotations

import asyncio
import io
import os
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz
import httpx
import psycopg
from PIL import Image
from psycopg.rows import dict_row

from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, BLOQUES, archivos_en_almacen, etiqueta, expect, mes_de, pdf, sha
from app.application.errors import ApplicationError
from app.application.use_cases.dual import revisiones
from app.bootstrap import ServiceAdapter
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from app.infrastructure.config.settings import settings
from app.infrastructure.database.repository import QueryCursorAdapter
from app.infrastructure.documents import dual_reports


def firma_png() -> bytes:
    imagen = Image.new("RGB", (300, 100), (255, 255, 255))
    for x in range(20, 280):
        imagen.putpixel((x, 50 + int(20 * ((x % 40) / 40))), (20, 40, 160))
    salida = io.BytesIO()
    imagen.save(salida, "PNG")
    return salida.getvalue()


def reporte_formato(texto: str) -> tuple[bytes, fitz.Rect]:
    """Réplica sintética del formato: tabla Nombre | Firma | Calificación con la fila del tutor."""
    documento = fitz.open()
    pagina = documento.new_page()
    pagina.insert_text((72, 72), f"{texto} · {secrets.token_hex(6)}", fontsize=12)
    x, filas = [52, 194, 328, 435, 560], [640, 655, 688, 721, 754]
    for y in filas:
        pagina.draw_line((x[0], y), (x[-1], y), width=1)
    for xx in x:
        pagina.draw_line((xx, filas[0]), (xx, filas[-1]), width=1)
    for punto, etiqueta_texto in (((250, 651), "Nombre"), ((370, 651), "Firma"), ((470, 651), "Calificación"),
                                  ((60, 678), "Instructor"), ((60, 711), "Formador"),
                                  ((60, 744), "Tutor académico"), ((200, 744), "Persona sintética")):
        pagina.insert_text(punto, etiqueta_texto, fontsize=9)
    contenido = documento.tobytes()
    documento.close()
    return contenido, fitz.Rect(x[2], filas[3], x[3], filas[4])


def conteos(conn):
    return conn.execute("SELECT count(*) FROM documentos").fetchone()[0], archivos_en_almacen()


def main():
    suffix = secrets.token_hex(5)
    password = "C06a" + secrets.token_urlsafe(18)
    changed = "C06b" + secrets.token_urlsafe(18)
    coordinator_email = f"c06.{suffix}@ute.edu.mx"
    tutor1_email, tutor2_email = f"t06a.{suffix}@ute.edu.mx", f"t06b.{suffix}@ute.edu.mx"
    hoy = calendar.hoy()
    lunes = calendar.lunes_de(hoy)
    domingo_actual = calendar.domingo_de(hoy)
    etiqueta_abierta = etiqueta(domingo_actual)
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1
    m_a, m_b = (str(secrets.randbelow(900000000) + 100000000) for _ in range(2))

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C06")
    with connect_local() as conn:
        for anio in (hoy.year - 1, hoy.year, hoy.year + 1):
            for mes, _, _ in BLOQUES:
                inicio, fin = fechas_del_periodo(mes, anio)
                label = construir_periodo(mes, anio)
                conn.execute(
                    "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
                    "VALUES (%s,%s,%s,%s) ON CONFLICT (cuatrimestre) DO NOTHING", (label, label, inicio, fin))
        periodo_hoy = conn.execute("SELECT id FROM ciclos_dual WHERE cuatrimestre=%s", (etiqueta_abierta,)).fetchone()[0]
        conn.commit()

    with httpx.Client(base_url=BASE, timeout=60, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        temp = login(coordinator_email, password)
        expect(client.post("/auth/cambiar-password", headers=temp,
                           json={"password_actual": password, "password_nueva": changed}), 200)
        coordinator = login(coordinator_email, changed)

        def crear_tutor(nombre, email):
            creado = expect(client.post("/auth/tutores", headers=coordinator,
                                        json={"nombre": nombre, "email": email}), 201)
            provisional = login(email, creado["password_temporal"])
            expect(client.post("/auth/cambiar-password", headers=provisional, json={
                "password_actual": creado["password_temporal"], "password_nueva": changed}), 200)
            return login(email, changed)

        tutor1 = crear_tutor("Tutor sintético C06 A", tutor1_email)
        tutor2 = crear_tutor("Tutor sintético C06 B", tutor2_email)
        with connect_local() as conn:
            tutor1_id = conn.execute("SELECT id FROM usuarios WHERE email=%s", (tutor1_email,)).fetchone()[0]

        def abrir_periodo():
            actual = expect(client.get("/dual/tutor/cuatrimestre-actual", headers=coordinator), 200)
            if actual["abierto"] and actual["periodo_label"] != etiqueta_abierta:
                expect(client.post("/dual/tutor/cierre", headers=coordinator,
                                   json={"periodo_label": actual["periodo_label"]}), 200)
            if not (actual["abierto"] and actual["periodo_label"] == etiqueta_abierta):
                inicio, fin = fechas_del_periodo(mes_de(domingo_actual), domingo_actual.year)
                expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=coordinator, json={
                    "periodo_label": etiqueta_abierta,
                    "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat()}), 200)

        abrir_periodo()

        group = expect(client.post("/dual/carrera/grupos", headers=tutor1, json={
            "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A",
            "turno": "Matutino", "plan": plan, "zona": zone}), 201)
        csv = {"file": ("alumnos.csv", (f"matricula,nombre\n{m_a},Alumno sintético C06 A\n"
                                       f"{m_b},Alumno sintético C06 B\n").encode(), "text/csv")}
        expect(client.post(f"/dual/carrera/grupos/{group['id']}/alumnos", headers=tutor1,
                           data={"periodo_id": str(periodo_hoy)}, files=csv), 200)
        company = expect(client.post("/dual/tutor/empresas", headers=tutor1,
                                     json={"nombre": f"Empresa C06 {suffix}"}), 201)
        for m, inicio in ((m_a, lunes - timedelta(days=35)), (m_b, lunes - timedelta(days=28))):
            expect(client.patch(f"/dual/tutor/alumnos/{m}", headers=tutor1, json={
                "alumno_dual": True, "empresa_id": company["id"], "fecha_inicio": inicio.isoformat()}), 200)

        alumno_pw = "C06s" + secrets.token_urlsafe(18)
        sesion = {}
        for m in (m_a, m_b):
            expect(client.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": alumno_pw}), 201)
            sesion[m] = login(f"{m}@ute.edu.mx", alumno_pw)
        alumno_a, alumno_b = sesion[m_a], sesion[m_b]

        def semanas(headers):
            return expect(client.get("/dual/alumno/obligaciones", headers=headers), 200)

        def entregables(headers):
            return sorted((o for o in semanas(headers) if o["periodo"] == etiqueta_abierta and o["puede_entregar"]),
                          key=lambda o: o["ordinal"])

        propias_a = entregables(alumno_a)
        assert len(propias_a) >= 5, ("Se necesitan 5 semanas del período abierto", len(propias_a))
        a1, a2, a3, a4, a5 = propias_a[-5:]
        b1 = entregables(alumno_b)[-1]

        def entregar(headers, obligacion, contenido, nota="8", esperado=201):
            respuesta = client.post(
                f"/dual/alumno/obligaciones/{obligacion['id']}/entrega", headers=headers,
                data={"fecha_inicio": obligacion["inicio_efectivo"], "fecha_fin": obligacion["fin_efectivo"],
                      "calificacion_alumno": nota},
                files={"archivo": ("reporte.pdf", contenido, "application/pdf")})
            if respuesta.status_code != esperado:
                raise AssertionError(f"entrega: esperado {esperado}, recibido {respuesta.status_code}: "
                                     f"{respuesta.text[:200]}")
            return respuesta.json()

        def revisar(headers, reporte_id, numero, esperado=200, **cuerpo):
            respuesta = client.post(f"/dual/tutor/reportes/{reporte_id}/versiones/{numero}/revision",
                                    headers=headers, json=cuerpo)
            if respuesta.status_code != esperado:
                raise AssertionError(f"revisión: esperado {esperado}, recibido {respuesta.status_code}: "
                                     f"{respuesta.text[:200]}")
            return respuesta.json()

        def detalle(headers, reporte_id):
            return expect(client.get(f"/dual/tutor/reportes/{reporte_id}", headers=headers), 200)

        def bytes_de(url, headers, esperado=200):
            respuesta = client.get(url, headers=headers)
            assert respuesta.status_code == esperado, (url, respuesta.status_code)
            return respuesta.content

        # La firma del tutor A se registra por la API; el tutor B no tiene firma (aún).
        expect(client.post("/dual/tutor/firma", headers=tutor1,
                           files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)

        # ---------- AC1/AC2/AC4: corrección trazable y aprobación con firma en la celda ----------
        original1, celda = reporte_formato("semana uno")
        r1 = entregar(alumno_a, a1, original1, nota="8")
        rid1 = r1["reporte_id"]
        d = detalle(tutor1, rid1)
        assert d["estado"] == "Pendiente" and d["version_vigente"] == 1 and d["puede_revisar"] is True
        assert d["firma_registrada"] is True and d["semana_inicio"] == a1["semana_inicio"]
        assert d["versiones"][0]["nota"] == 8 and d["versiones"][0]["decision"] is None
        bandeja = expect(client.get("/dual/tutor/reportes", headers=tutor1), 200)
        assert any(r["id"] == rid1 and r["version"] == 1 for r in bandeja)
        assert bytes_de(f"/dual/tutor/reportes/{rid1}/versiones/1/pdf", tutor1) == original1

        with connect_local() as conn:
            antes = conteos(conn)
        # Entradas inválidas: 422 y ningún rastro (ni archivo firmado ni revisión).
        revisar(tutor1, rid1, 1, 422, decision="Rechazada")
        revisar(tutor1, rid1, 1, 422, decision="Rechazada", observacion="   ")
        revisar(tutor1, rid1, 1, 422, decision="Pendiente")
        for nota in (0, 11, 8.5, True, "9"):
            revisar(tutor1, rid1, 1, 422, decision="Aprobada", calificacion=nota)
        revisar(tutor1, rid1, 1, 422, decision="Aprobada", fecha_inicio="2026-12-31", fecha_fin="2026-01-01")
        with connect_local() as conn:
            assert conteos(conn) == antes, "Una revisión inválida no debe dejar documentos ni archivos"
            assert conn.execute("SELECT count(*) FROM revisiones r JOIN reporte_versiones v ON v.id=r.version_id "
                                "WHERE v.reporte_id=%s", (rid1,)).fetchone()[0] == 0
        assert detalle(tutor1, rid1)["estado"] == "Pendiente"

        obligaciones_antes = {o["id"]: (o["periodo"], o["semana_inicio"], o["ordinal"]) for o in semanas(alumno_a)}
        inicio_corregido = (date.fromisoformat(a1["inicio_efectivo"]) + timedelta(days=1)).isoformat()
        assert inicio_corregido <= a1["fin_efectivo"]
        resultado = revisar(tutor1, rid1, 1, decision="Aprobada", observacion="Buen trabajo", calificacion=9,
                            fecha_inicio=inicio_corregido)
        assert resultado["estado"] == "Aprobada" and resultado["firma"] == "celda" and resultado["repetido"] is False
        d = detalle(tutor1, rid1)
        v = d["versiones"][0]
        assert d["estado"] == "Aprobada" and d["puede_revisar"] is False
        assert v["nota"] == 8 and v["validada_nota"] == 9, "Lo declarado no cambia; lo validado queda aparte"
        assert {c["campo"]: (c["previo"], c["nuevo"]) for c in v["correcciones"]} == {
            "nota": ("8", "9"), "fecha_inicio": (a1["inicio_efectivo"], inicio_corregido)}
        assert v["firmado"] is True and v["firma_modo"] == "celda" and v["decision"] == "Aprobada"
        # DP-02: la corrección nunca mueve la obligación ni el período.
        assert {o["id"]: (o["periodo"], o["semana_inicio"], o["ordinal"]) for o in semanas(alumno_a)} == obligaciones_antes

        with connect_local() as conn:
            fila = conn.execute(
                "SELECT d.clave, d.sha256, ds.clave, ds.sha256, ds.firma_modo, ds.rol FROM reportes_dual r "
                "JOIN reporte_versiones v ON v.reporte_id=r.id JOIN documentos d ON d.id=v.documento_id "
                "JOIN revisiones rv ON rv.version_id=v.id JOIN documentos ds ON ds.id=rv.documento_firmado_id "
                "WHERE r.id=%s", (rid1,)).fetchone()
        clave_original, hash_original, clave_firmado, hash_firmado, modo_firmado, rol_firmado = fila
        assert dual_reports.ruta_documento(clave_original).read_bytes() == original1, "El original no se altera"
        assert sha(original1) == hash_original
        firmado1 = dual_reports.ruta_documento(clave_firmado).read_bytes()
        assert sha(firmado1) == hash_firmado and firmado1 != original1 and (modo_firmado, rol_firmado) == ("celda", "firmado")
        with fitz.open(stream=original1, filetype="pdf") as antes_doc, fitz.open(stream=firmado1, filetype="pdf") as despues_doc:
            assert despues_doc.page_count == antes_doc.page_count == 1
            assert despues_doc[0].get_text() == antes_doc[0].get_text()
            imagenes = despues_doc[0].get_image_info()
            assert len(imagenes) == 1 and celda.contains(fitz.Rect(imagenes[0]["bbox"])), imagenes

        # Descargas: tutor, alumno y lecturas heredadas ven el mismo firmado; el original sigue disponible.
        assert bytes_de(f"/dual/tutor/reportes/{rid1}/versiones/1/pdf?documento=firmado", tutor1) == firmado1
        assert bytes_de(f"/dual/tutor/reportes/{rid1}/versiones/1/pdf", tutor1) == original1
        assert bytes_de(f"/dual/alumno/reportes/{rid1}/versiones/1/pdf?documento=firmado", alumno_a) == firmado1
        assert bytes_de(f"/dual/alumno/reportes/{rid1}/versiones/1/pdf", alumno_a) == original1
        assert bytes_de(f"/dual/alumno/reporte/{rid1}/pdf", alumno_a) == firmado1
        assert bytes_de(f"/dual/tutor/reporte/{rid1}/pdf", tutor1) == firmado1
        propia = {o["id"]: o for o in semanas(alumno_a)}[a1["id"]]
        assert propia["entrega"] == "Aprobada" and not propia["puede_entregar"]
        vistas = expect(client.get(f"/dual/alumno/reportes/{rid1}/versiones", headers=alumno_a), 200)
        assert vistas[0]["firmado"] is True and vistas[0]["validada_nota"] == 9 and vistas[0]["decision"] == "Aprobada"
        # Un alumno ajeno no ve ni descarga el firmado.
        expect(client.get(f"/dual/alumno/reportes/{rid1}/versiones/1/pdf?documento=firmado", headers=alumno_b), 404)

        # Reintento idéntico estable; decisión distinta y reenvío del alumno: 409 sin efectos.
        with connect_local() as conn:
            antes = conteos(conn)
        repetido = revisar(tutor1, rid1, 1, decision="Aprobada", observacion="Buen trabajo", calificacion=9,
                           fecha_inicio=inicio_corregido)
        assert repetido["repetido"] is True
        revisar(tutor1, rid1, 1, 409, decision="Rechazada", observacion="Cambio de opinión")
        entregar(alumno_a, a1, pdf("reemplazo"), esperado=409)
        with connect_local() as conn:
            assert conteos(conn) == antes, "El reintento y los 409 no dejan documentos ni archivos"

        # Revisiones y correcciones inmutables en la propia base.
        with connect_local() as conn:
            for sentencia in ("UPDATE revisiones SET decision='Rechazada', observacion='x' WHERE decision='Aprobada' "
                              "AND version_id IN (SELECT id FROM reporte_versiones WHERE reporte_id=%s)",
                              "DELETE FROM revisiones WHERE version_id IN "
                              "(SELECT id FROM reporte_versiones WHERE reporte_id=%s)",
                              "UPDATE reporte_correcciones SET valor_nuevo='1' WHERE revision_id IN (SELECT rv.id "
                              "FROM revisiones rv JOIN reporte_versiones v ON v.id=rv.version_id WHERE v.reporte_id=%s)",
                              "DELETE FROM reporte_correcciones WHERE revision_id IN (SELECT rv.id "
                              "FROM revisiones rv JOIN reporte_versiones v ON v.id=rv.version_id WHERE v.reporte_id=%s)"):
                try:
                    conn.execute(sentencia, (rid1,))
                    raise AssertionError(f"La base permitió: {sentencia[:40]}")
                except psycopg.errors.RaiseException:
                    conn.rollback()

        # ---------- AC3: rechazo con observación, reenvío, versión obsoleta y aprobación de la v2 ----------
        original2, _ = reporte_formato("semana dos")
        r2 = entregar(alumno_a, a2, original2, nota="7")
        rid2 = r2["reporte_id"]
        revisar(tutor1, rid2, 1, decision="Rechazada", observacion="Falta la firma de la empresa")
        propia = {o["id"]: o for o in semanas(alumno_a)}[a2["id"]]
        assert propia["entrega"] == "Rechazada" and propia["observacion"] == "Falta la firma de la empresa"
        assert propia["puede_entregar"] is True
        d = detalle(tutor1, rid2)
        assert d["estado"] == "Rechazada" and d["puede_revisar"] is False
        revisar(tutor1, rid2, 1, 409, decision="Aprobada")  # la v1 ya tiene decisión
        original2b, celda2 = reporte_formato("semana dos corregida")
        assert entregar(alumno_a, a2, original2b, nota="8")["version"] == 2
        d = detalle(tutor1, rid2)
        assert d["version_vigente"] == 2 and d["puede_revisar"] is True and [v["numero"] for v in d["versiones"]] == [2, 1]
        assert d["versiones"][1]["decision"] == "Rechazada" and d["versiones"][1]["observacion"] == "Falta la firma de la empresa"
        with connect_local() as conn:
            antes = conteos(conn)
        revisar(tutor1, rid2, 1, 409, decision="Aprobada")  # decidir sobre la versión obsoleta
        with connect_local() as conn:
            assert conteos(conn) == antes
        assert revisar(tutor1, rid2, 2, decision="Aprobada")["firma"] == "celda"
        d = detalle(tutor1, rid2)
        assert d["estado"] == "Aprobada" and d["versiones"][0]["correcciones"] == []
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM revisiones r JOIN reporte_versiones v ON v.id=r.version_id "
                                "WHERE v.reporte_id=%s", (rid2,)).fetchone()[0] == 2
        assert bytes_de(f"/dual/alumno/reportes/{rid2}/versiones/1/pdf", alumno_a) == original2
        expect(client.get(f"/dual/alumno/reportes/{rid2}/versiones/1/pdf?documento=firmado", headers=alumno_a), 404)

        # ---------- DP-07: formato no reconocido → respaldo con hoja adicional ----------
        plano = pdf("sin tabla de firmas", 2)
        r3 = entregar(alumno_a, a3, plano)
        assert revisar(tutor1, r3["reporte_id"], 1, decision="Aprobada")["firma"] == "hoja_adicional"
        firmado3 = bytes_de(f"/dual/tutor/reportes/{r3['reporte_id']}/versiones/1/pdf?documento=firmado", tutor1)
        with fitz.open(stream=firmado3, filetype="pdf") as doc3:
            assert doc3.page_count == 3
        assert bytes_de(f"/dual/tutor/reportes/{r3['reporte_id']}/versiones/1/pdf", tutor1) == plano

        # ---------- AC7: tutor sin firma registrada no puede aprobar; puede rechazar ----------
        original4, _ = reporte_formato("semana cuatro")
        r4 = entregar(alumno_a, a4, original4)
        rid4 = r4["reporte_id"]
        assert detalle(tutor2, rid4)["firma_registrada"] is False
        with connect_local() as conn:
            antes = conteos(conn)
        revisar(tutor2, rid4, 1, 409, decision="Aprobada")
        with connect_local() as conn:
            assert conteos(conn) == antes and detalle(tutor1, rid4)["estado"] == "Pendiente"

        # ---------- AC5: fallos inyectados contra la base real ----------
        servicios = ServiceAdapter()

        class FallaAlSalir:
            def __init__(self, conn):
                self.conn = conn

            @asynccontextmanager
            async def transaction(self):
                async with self.conn.cursor() as cur:
                    yield QueryCursorAdapter(cur)
                    raise RuntimeError("fallo inyectado antes de confirmar")

            @asynccontextmanager
            async def read(self):
                async with self.conn.cursor() as cur:
                    yield QueryCursorAdapter(cur)

        class ServiciosSinEstampa(ServiceAdapter):
            @staticmethod
            def estampar_firma(*args):
                raise ApplicationError(400, "fallo inyectado al firmar")

        usuario_t1 = {"id": tutor1_id, "sub": tutor1_email}
        with connect_local() as conn:
            antes = conteos(conn)

        async def aprobar_con_falla(servicios_usados, esperado):
            async with await psycopg.AsyncConnection.connect(settings.db.db_dsn, row_factory=dict_row) as conn:
                runtime = SimpleNamespace(database=FallaAlSalir(conn), services=servicios_usados)
                try:
                    await revisiones.revisar(rid4, 1, "Aprobada", None, None, None, None, usuario_t1, runtime=runtime)
                except esperado:
                    await conn.rollback()  # como en producción: ante una excepción se hace rollback
                    return
                raise AssertionError("La falla inyectada debía propagarse")

        asyncio.run(aprobar_con_falla(servicios, RuntimeError))
        asyncio.run(aprobar_con_falla(ServiciosSinEstampa(), ApplicationError))
        with connect_local() as conn:
            assert conteos(conn) == antes, "Una falla al firmar o confirmar no deja documento ni archivo nuevos"
            assert conn.execute("SELECT count(*) FROM revisiones r JOIN reporte_versiones v ON v.id=r.version_id "
                                "WHERE v.reporte_id=%s", (rid4,)).fetchone()[0] == 0
        assert detalle(tutor1, rid4)["estado"] == "Pendiente", "Un fallo no deja el reporte aprobado a medias"
        assert bytes_de(f"/dual/tutor/reportes/{rid4}/versiones/1/pdf", tutor1) == original4, "El original sigue intacto"
        assert revisar(tutor1, rid4, 1, decision="Aprobada")["firma"] == "celda"  # y luego sí se puede aprobar

        # ---------- AC6: dos tutores deciden la misma versión a la vez ----------
        expect(client.post("/dual/tutor/firma", headers=tutor2,
                           files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)
        original_b, _ = reporte_formato("alumno b")
        rb = entregar(alumno_b, b1, original_b)
        with connect_local() as conn:
            antes_conc = conteos(conn)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [pool.submit(client.post, f"/dual/tutor/reportes/{rb['reporte_id']}/versiones/1/revision",
                                   headers=tutor1, json={"decision": "Aprobada"}),
                       pool.submit(client.post, f"/dual/tutor/reportes/{rb['reporte_id']}/versiones/1/revision",
                                   headers=tutor2, json={"decision": "Rechazada", "observacion": "Competencia"})]
            codigos = sorted(f.result().status_code for f in futuros)
        assert codigos == [200, 409], codigos
        d = detalle(tutor1, rb["reporte_id"])
        assert d["estado"] in ("Aprobada", "Rechazada") and d["versiones"][0]["decision"] == d["estado"]
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM revisiones r JOIN reporte_versiones v ON v.id=r.version_id "
                                "WHERE v.reporte_id=%s", (rb["reporte_id"],)).fetchone()[0] == 1
            despues = conteos(conn)
        firmados_nuevos = 1 if d["estado"] == "Aprobada" else 0
        assert despues == (antes_conc[0] + firmados_nuevos, antes_conc[1] + firmados_nuevos), (
            "El tutor perdedor no deja documento ni archivo", antes_conc, despues)

        # ---------- Permisos y aislamiento ----------
        for headers in (alumno_a, coordinator):
            expect(client.get(f"/dual/tutor/reportes/{rid1}", headers=headers), 403)
            assert client.post(f"/dual/tutor/reportes/{rid1}/versiones/1/revision", headers=headers,
                               json={"decision": "Aprobada"}).status_code == 403
            assert client.get(f"/dual/tutor/reportes/{rid1}/versiones/1/pdf", headers=headers).status_code == 403
        assert client.get(f"/dual/tutor/reportes/{rid1}").status_code == 401
        assert client.post(f"/dual/tutor/reportes/{rid1}/versiones/1/revision",
                           json={"decision": "Aprobada"}).status_code == 401
        expect(client.get("/dual/tutor/reportes/00000000-0000-0000-0000-000000000000", headers=tutor1), 404)
        revisar(tutor1, "00000000-0000-0000-0000-000000000000", 1, 404, decision="Aprobada")
        revisar(tutor1, rid4, 9, 404, decision="Aprobada")
        expect(client.get(f"/dual/tutor/reportes/{rid1}/versiones/9/pdf", headers=tutor1), 404)
        expect(client.get("/dual/tutor/reportes/no-es-un-uuid", headers=tutor1), 422)
        expect(client.get(f"/dual/tutor/reportes/{rid1}/versiones/1/pdf?documento=otro", headers=tutor1), 422)
        expect(client.get(f"/dual/tutor/reportes/{rb['reporte_id']}/versiones/1/pdf?documento=firmado", headers=tutor1),
               200 if d["estado"] == "Aprobada" else 404)
        assert client.patch(f"/dual/tutor/reportes/{rid1}", headers=tutor1,
                            json={"estado": "Aprobada"}).status_code in (404, 405)

        # ---------- RN-18/RN-19: con la recepción cerrada la revisión continúa ----------
        r5 = entregar(alumno_a, a5, reporte_formato("semana cinco")[0])
        expect(client.post("/dual/tutor/cierre", headers=coordinator, json={"periodo_label": etiqueta_abierta}), 200)
        assert detalle(tutor1, r5["reporte_id"])["periodo_cerrado"] is True
        revisar(tutor1, r5["reporte_id"], 1, decision="Rechazada", observacion="Revisión tras el cierre")
        entregar(alumno_a, a5, reporte_formato("tarde")[0], esperado=409)  # pero el alumno ya no reenvía
        cerrada = {o["id"]: o for o in semanas(alumno_a)}[a5["id"]]
        assert not cerrada["puede_entregar"] and cerrada["entrega"] == "Rechazada"
        # El período queda cerrado: así no se condiciona a otros recorridos (solo puede haber uno abierto).

        # ---------- Integridad final de los documentos de esta corrida ----------
        with connect_local() as conn:
            filas = conn.execute(
                "SELECT d.clave, d.sha256, d.tamano FROM documentos d WHERE d.id IN ("
                "SELECT v.documento_id FROM reporte_versiones v JOIN reportes_dual r ON r.id=v.reporte_id "
                "WHERE r.matricula IN (%s,%s) UNION SELECT rv.documento_firmado_id FROM revisiones rv "
                "JOIN reporte_versiones v ON v.id=rv.version_id JOIN reportes_dual r ON r.id=v.reporte_id "
                "WHERE r.matricula IN (%s,%s) AND rv.documento_firmado_id IS NOT NULL)", (m_a, m_b, m_a, m_b)).fetchall()
        # 7 originales + 4 firmados (a1, a2 v2, a3, a4) y el de b1 si ganó la aprobación.
        assert len(filas) in (11, 12), len(filas)
        for clave, hash_guardado, tamano in filas:
            contenido = dual_reports.ruta_documento(clave).read_bytes()
            assert sha(contenido) == hash_guardado and len(contenido) == tamano, clave

    print("PASS C06: corrección trazable sin mover período, rechazo con observación y reenvío, aprobación con "
          "firma en la celda (respaldo con hoja adicional), original y firmado conservados byte a byte, versión "
          "obsoleta y concurrencia entre tutores, fallos inyectados, permisos y revisión con recepción cerrada. "
          "HTTP, PostgreSQL y almacenamiento REALES.")
    print("Drive, móvil físico e integración con el formato real del responsable (solo réplica sintética): "
          "NO_VERIFICADOS. Datos sintéticos conservados.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError, ApplicationError) as exc:
        print(f"FAIL C06: {exc}", file=sys.stderr)
        raise SystemExit(1)
