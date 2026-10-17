"""Smoke C05 con HTTP, PostgreSQL y almacenamiento en disco reales sobre Compose local.

Entrega por obligación, validación de nota y PDF, versiones inmutables, reenvío tras rechazo,
concurrencia, recepción abierta (DP-13), permisos, conservación del original (hash) y fallos
inyectados contra la base real. Los datos sintéticos se conservan; no se imprimen contraseñas.
"""
from __future__ import annotations

import asyncio
import hashlib
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
from psycopg.rows import dict_row

import smoke_periodos
from local_admin import connect_local, create_coordinator
from app.application.errors import ApplicationError
from app.application.use_cases.dual import entregas
from app.bootstrap import ServiceAdapter
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from app.domain.reports import MAX_PDF_BYTES
from app.infrastructure.config.settings import settings
from app.infrastructure.database.repository import QueryCursorAdapter
from app.infrastructure.documents import dual_reports

BASE = os.environ.get("API_URL", "http://api:8000")
if BASE not in ("http://api:8000", "http://127.0.0.1:8001"):
    raise SystemExit("Destino HTTP no permitido para C05")

BLOQUES = (("Enero", 1, 4), ("Mayo", 5, 8), ("Septiembre", 9, 12))


def expect(response, status):
    if response.status_code != status:
        raise AssertionError(
            f"{response.request.method} {response.request.url.path}: "
            f"esperado {status}, recibido {response.status_code}: {response.text[:300]}")
    return response.json() if response.content and "json" in response.headers.get("content-type", "") else None


def etiqueta(fecha: date) -> str:
    for mes, ini, fin in BLOQUES:
        if ini <= fecha.month <= fin:
            return construir_periodo(mes, fecha.year)
    raise AssertionError("mes fuera de rango")


def mes_de(fecha: date) -> str:
    return next(mes for mes, ini, fin in BLOQUES if ini <= fecha.month <= fin)


def pdf(texto: str, paginas: int = 1) -> bytes:
    documento = fitz.open()
    for numero in range(paginas):
        pagina = documento.new_page()
        pagina.insert_text((72, 72), f"{texto} · página {numero + 1} · {secrets.token_hex(8)}")
    contenido = documento.tobytes()
    documento.close()
    return contenido


def sha(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


# C10A: los smokes usan el mismo contrato de almacenamiento que la API (Drive, o la carpeta local de regresión).
def almacen():
    from app.infrastructure.storage.registro import get_storage
    return get_storage()


def leer_doc(clave: str) -> bytes:
    return almacen().leer("documentos", clave)


def existe_doc(clave: str) -> bool:
    return almacen().existe("documentos", clave)


def archivos_en_almacen() -> int:
    return len(almacen().listar("documentos"))


def conteos(conn):
    return (
        conn.execute("SELECT count(*) FROM documentos").fetchone()[0],
        conn.execute("SELECT count(*) FROM reportes_dual WHERE obligacion_id IS NOT NULL").fetchone()[0],
        conn.execute("SELECT count(*) FROM reporte_versiones").fetchone()[0],
        archivos_en_almacen(),
    )


def main():
    suffix = secrets.token_hex(5)
    password = "C05a" + secrets.token_urlsafe(18)
    changed = "C05b" + secrets.token_urlsafe(18)
    coordinator_email = f"c05.{suffix}@ute.edu.mx"
    tutor_email = f"t05.{suffix}@ute.edu.mx"
    hoy = calendar.hoy()
    lunes = calendar.lunes_de(hoy)
    domingo_actual = calendar.domingo_de(hoy)
    etiqueta_abierta = etiqueta(domingo_actual)
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1
    m_a, m_b = (str(secrets.randbelow(900000000) + 100000000) for _ in range(2))

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C05")
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
        created = expect(client.post("/auth/tutores", headers=coordinator,
                                     json={"nombre": "Tutor sintético C05", "email": tutor_email}), 201)
        tutor_temp = login(tutor_email, created["password_temporal"])
        expect(client.post("/auth/cambiar-password", headers=tutor_temp,
                           json={"password_actual": created["password_temporal"], "password_nueva": changed}), 200)
        tutor = login(tutor_email, changed)

        def abrir_periodo():
            """Deja abierto solo el período de la semana actual (DP-13)."""
            inicio, fin = fechas_del_periodo(mes_de(domingo_actual), domingo_actual.year)
            return smoke_periodos.abrir_de_prueba(client, coordinator, etiqueta_abierta, inicio, fin)

        id_periodo_abierto = abrir_periodo()

        group = expect(client.post("/dual/carrera/grupos", headers=tutor, json={
            "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A",
            "turno": "Matutino", "plan": plan, "zona": zone}), 201)
        csv = {"file": ("alumnos.csv", (f"matricula,nombre\n{m_a},Alumno sintético C05 A\n"
                                       f"{m_b},Alumno sintético C05 B\n").encode(), "text/csv")}
        expect(client.post(f"/dual/carrera/grupos/{group['id']}/alumnos", headers=tutor,
                           data={"periodo_id": str(periodo_hoy)}, files=csv), 200)
        company = expect(client.post("/dual/tutor/empresas", headers=tutor,
                                     json={"nombre": f"Empresa C05 {suffix}"}), 201)
        for m, inicio in ((m_a, lunes - timedelta(days=14)), (m_b, lunes - timedelta(days=7))):
            expect(client.patch(f"/dual/tutor/alumnos/{m}", headers=tutor, json={
                "alumno_dual": True, "empresa_id": company["id"], "fecha_inicio": inicio.isoformat()}), 200)

        alumno_pw = "C05s" + secrets.token_urlsafe(18)
        sesion = {}
        for m in (m_a, m_b):
            expect(client.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": alumno_pw}), 201)
            sesion[m] = login(f"{m}@ute.edu.mx", alumno_pw)
        alumno_a, alumno_b = sesion[m_a], sesion[m_b]

        def semanas(headers):
            return expect(client.get("/dual/alumno/obligaciones", headers=headers), 200)

        entregables = sorted(
            (o for o in semanas(alumno_a) if o["periodo"] == etiqueta_abierta),
            key=lambda o: o["ordinal"])
        assert len(entregables) >= 3, (
            "Se necesitan 3 semanas del período abierto; ¿fecha en el límite entre períodos?", len(entregables))
        w_vieja, w_media, w_actual = entregables[-3], entregables[-2], entregables[-1]
        for o in (w_vieja, w_media, w_actual):
            assert o["puede_entregar"] and o["entrega"] is None, o
        assert w_actual["estado"] == "PENDIENTE" and w_vieja["estado"] == "ATRASADA"

        def entregar(headers, obligacion, contenido, nota="9", inicio=None, fin=None,
                     nombre="reporte.pdf", esperado=201):
            respuesta = client.post(
                f"/dual/alumno/obligaciones/{obligacion['id']}/entrega", headers=headers,
                data={"fecha_inicio": inicio or obligacion["inicio_efectivo"],
                      "fecha_fin": fin or obligacion["fin_efectivo"], "calificacion_alumno": nota},
                files={"archivo": (nombre, contenido, "application/pdf")})
            if respuesta.status_code != esperado:
                raise AssertionError(f"entrega: esperado {esperado}, recibido {respuesta.status_code}: "
                                     f"{respuesta.text[:200]}")
            return respuesta.json()

        # ---------- AC2: nota, fechas y PDF inválidos no dejan rastro ----------
        valido = pdf("válido", 2)
        documento = fitz.open(stream=valido, filetype="pdf")
        protegido = documento.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="clave", owner_pw="otra")
        documento.close()
        with connect_local() as conn:
            antes = conteos(conn)
        for nota in ("0", "11", "8.5", "8,5", "abc", "-1", ""):
            entregar(alumno_a, w_vieja, valido, nota=nota, esperado=422)
        entregar(alumno_a, w_vieja, valido, inicio="2026-10-09", fin="2026-10-05", esperado=422)
        entregar(alumno_a, w_vieja, valido, nombre="imagen.png", esperado=422)
        for contenido in (b"", b"no es un pdf", b"%PDF-1.7\nbasura", valido[: len(valido) // 2], protegido):
            entregar(alumno_a, w_vieja, contenido, esperado=422)
        entregar(alumno_a, w_vieja, b"%PDF-" + b"0" * MAX_PDF_BYTES, esperado=413)
        with connect_local() as conn:
            assert conteos(conn) == antes, "Una entrega inválida no debe crear documentos, reportes ni archivos"

        # ---------- AC1: una semana pendiente de revisión no bloquea las demás ----------
        original_vieja = pdf("semana vieja")
        r_vieja = entregar(alumno_a, w_vieja, original_vieja, nota="1")  # nota mínima
        assert (r_vieja["version"], r_vieja["repetido"]) == (1, False)
        original_actual = pdf("semana actual")
        r_actual = entregar(alumno_a, w_actual, original_actual, nota="10")  # nota máxima
        assert r_actual["version"] == 1
        por_id = {o["id"]: o for o in semanas(alumno_a)}
        assert por_id[w_vieja["id"]]["entrega"] == "Pendiente" and not por_id[w_vieja["id"]]["puede_entregar"]
        assert por_id[w_vieja["id"]]["estado"] == "RECIBIDA" and por_id[w_vieja["id"]]["version"] == 1
        assert por_id[w_media["id"]]["puede_entregar"], "Entregar otra semana no depende de las demás"

        # ---------- AC4: el original se conserva byte a byte ----------
        with connect_local() as conn:
            fila = conn.execute(
                "SELECT d.clave, d.sha256, d.tamano, d.paginas FROM reportes_dual r "
                "JOIN reporte_versiones v ON v.reporte_id=r.id JOIN documentos d ON d.id=v.documento_id "
                "WHERE r.id=%s", (r_vieja["reporte_id"],)).fetchone()
        guardado = leer_doc(fila[0])
        assert guardado == original_vieja and sha(guardado) == fila[1] and fila[2] == len(original_vieja)
        descarga = client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones/1/pdf", headers=alumno_a)
        assert descarga.status_code == 200 and descarga.content == original_vieja
        assert descarga.headers["content-type"] == "application/pdf"
        tutor_ve = client.get(f"/dual/tutor/reportes/{r_vieja['reporte_id']}/versiones/1/pdf", headers=tutor)
        assert tutor_ve.status_code == 200 and tutor_ve.content == original_vieja
        bandeja = expect(client.get("/dual/tutor/reportes", headers=tutor), 200)
        assert any(r["id"] == r_vieja["reporte_id"] and r["estado"] == "Pendiente" for r in bandeja)

        # Reintento idéntico: estable. Reenvío distinto con la versión pendiente: 409.
        with connect_local() as conn:
            con_archivos = conteos(conn)
        repetido = entregar(alumno_a, w_vieja, original_vieja, nota="1")
        assert repetido["repetido"] is True and repetido["version"] == 1
        entregar(alumno_a, w_vieja, pdf("otra"), nota="1", esperado=409)
        with connect_local() as conn:
            assert conteos(conn) == con_archivos, "El reintento y el 409 no dejan documentos ni archivos extra"

        # ---------- AC3: rechazo, reenvío con versión nueva y decisión anterior conservada ----------
        # C06: el rechazo se registra con la ruta de revisión por versión (la ruta PATCH se retiró).
        expect(client.post(f"/dual/tutor/reportes/{r_vieja['reporte_id']}/versiones/1/revision", headers=tutor, json={
            "decision": "Rechazada", "observacion": "Falta la firma de la empresa"}), 200)
        rechazada = {o["id"]: o for o in semanas(alumno_a)}[w_vieja["id"]]
        assert rechazada["entrega"] == "Rechazada" and rechazada["observacion"] == "Falta la firma de la empresa"
        assert rechazada["puede_entregar"] is True
        original_v2 = pdf("semana vieja corregida", 3)
        r_v2 = entregar(alumno_a, w_vieja, original_v2, nota="8")
        assert (r_v2["version"], r_v2["reporte_id"]) == (2, r_vieja["reporte_id"])
        versiones = expect(client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones", headers=alumno_a), 200)
        assert [v["numero"] for v in versiones] == [2, 1]
        v1 = versiones[1]
        assert v1["decision"] == "Rechazada" and v1["nota_revision"] == "Falta la firma de la empresa" and v1["nota"] == 1
        assert versiones[0]["decision"] is None and versiones[0]["nota"] == 8
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM reportes_dual WHERE obligacion_id=%s",
                                (w_vieja["id"],)).fetchone()[0] == 1, "Un solo reporte lógico por obligación"
            estado = conn.execute("SELECT estado, nota_agente, calificacion_alumno FROM reportes_dual WHERE id=%s",
                                  (r_vieja["reporte_id"],)).fetchone()
            assert estado[0] == "Pendiente" and estado[1] is None and int(estado[2]) == 8
        assert client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones/1/pdf",
                          headers=alumno_a).content == original_vieja, "La versión anterior se conserva"
        assert client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones/2/pdf",
                          headers=alumno_a).content == original_v2
        assert client.get(f"/dual/tutor/reportes/{r_vieja['reporte_id']}/versiones/2/pdf", headers=tutor).content == original_v2
        # Las versiones son inmutables en la propia base de datos.
        with connect_local() as conn:
            for sentencia in ("UPDATE reporte_versiones SET nota=3 WHERE reporte_id=%s AND numero=1",
                              "UPDATE reporte_versiones SET decision='Aprobada' WHERE reporte_id=%s AND numero=1",
                              "DELETE FROM reporte_versiones WHERE reporte_id=%s AND numero=2"):
                try:
                    conn.execute(sentencia, (r_vieja["reporte_id"],))
                    raise AssertionError(f"La base permitió: {sentencia}")
                except psycopg.errors.RaiseException:
                    conn.rollback()

        # Concurrencia: contenidos distintos → una sola versión; idénticos → una sola versión.
        with connect_local() as conn:
            antes_conc = conteos(conn)
        distintos = [pdf(f"competidor {i}") for i in range(6)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            respuestas = list(pool.map(
                lambda c: client.post(
                    f"/dual/alumno/obligaciones/{w_media['id']}/entrega", headers=alumno_a,
                    data={"fecha_inicio": w_media["inicio_efectivo"], "fecha_fin": w_media["fin_efectivo"],
                          "calificacion_alumno": "7"},
                    files={"archivo": ("reporte.pdf", c, "application/pdf")}), distintos))
        codigos = sorted(r.status_code for r in respuestas)
        assert codigos == [201] + [409] * 5, codigos
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM reportes_dual WHERE obligacion_id=%s",
                                (w_media["id"],)).fetchone()[0] == 1
            assert conn.execute("SELECT count(*) FROM reporte_versiones v JOIN reportes_dual r ON r.id=v.reporte_id "
                                "WHERE r.obligacion_id=%s", (w_media["id"],)).fetchone()[0] == 1
            despues = conteos(conn)
        assert despues[0] == antes_conc[0] + 1 and despues[3] == antes_conc[3] + 1, (
            "Los envíos perdedores no dejan documento ni archivo", antes_conc, despues)

        # ---------- DP-13: sin período y con período cerrado no se entrega ----------
        otra = next(o for o in semanas(alumno_b) if o["periodo"] == etiqueta_abierta and o["puede_entregar"])
        with connect_local() as conn:
            anterior = conn.execute("SELECT periodo_id FROM obligaciones_semanales WHERE id=%s", (otra["id"],)).fetchone()[0]
            conn.execute("UPDATE obligaciones_semanales SET periodo_id=NULL WHERE id=%s", (otra["id"],))
            conn.commit()
        sin_periodo = {o["id"]: o for o in semanas(alumno_b)}[otra["id"]]
        assert not sin_periodo["puede_entregar"] and "período" in sin_periodo["motivo_bloqueo"]
        entregar(alumno_b, otra, pdf("sin período"), esperado=409)
        with connect_local() as conn:
            conn.execute("UPDATE obligaciones_semanales SET periodo_id=%s WHERE id=%s", (anterior, otra["id"]))
            conn.commit()

        # ---------- AC6: permisos y aislamiento ----------
        entregar(alumno_b, w_actual, pdf("ajeno"), esperado=404)
        expect(client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones", headers=alumno_b), 404)
        expect(client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones/1/pdf", headers=alumno_b), 404)
        expect(client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones/9/pdf", headers=alumno_a), 404)
        expect(client.get("/dual/alumno/reportes/no-es-un-uuid/versiones", headers=alumno_a), 422)
        expect(client.get("/dual/alumno/reportes/00000000-0000-0000-0000-000000000000/versiones", headers=alumno_a), 404)
        for headers in (tutor, coordinator):
            expect(client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones", headers=headers), 403)
            assert client.post(f"/dual/alumno/obligaciones/{w_actual['id']}/entrega", headers=headers,
                               data={"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-02", "calificacion_alumno": "9"},
                               files={"archivo": ("r.pdf", valido, "application/pdf")}).status_code == 403
        assert client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones").status_code == 401
        # Rutas heredadas retiradas.
        assert client.get("/dual/alumno/semana-actual", headers=alumno_a).status_code in (404, 405)
        assert client.post("/dual/alumno/", headers=alumno_a, data={"semana": "1"}).status_code in (404, 405)

        # ---------- RN-17: un reporte aprobado no se reemplaza ----------
        with connect_local() as conn:
            conn.execute("UPDATE reportes_dual SET estado='Aprobada' WHERE id=%s", (r_actual["reporte_id"],))
            conn.commit()
        entregar(alumno_a, w_actual, pdf("reemplazo"), esperado=409)
        aprobado = {o["id"]: o for o in semanas(alumno_a)}[w_actual["id"]]
        assert aprobado["entrega"] == "Aprobada" and not aprobado["puede_entregar"]
        assert client.get(f"/dual/alumno/reportes/{r_actual['reporte_id']}/versiones/1/pdf",
                          headers=alumno_a).content == original_actual

        # ---------- AC7: fallos inyectados contra la base real ----------
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

        class Archivo:
            filename = "reporte.pdf"

            def __init__(self, contenido):
                self.contenido, self.pos = contenido, 0

            async def read(self, size=-1):
                bloque = self.contenido[self.pos:self.pos + (size if size > 0 else len(self.contenido))]
                self.pos += len(bloque)
                return bloque

        # La falla ocurre al confirmar la transacción de la alumna B sobre una semana válida.
        with connect_local() as conn:
            usuario_b = conn.execute("SELECT id FROM usuarios WHERE matricula=%s", (m_b,)).fetchone()[0]
            antes_falla = conteos(conn)

        async def con_falla_b():
            async with await psycopg.AsyncConnection.connect(settings.db.db_dsn, row_factory=dict_row) as conn:
                runtime = SimpleNamespace(database=FallaAlSalir(conn), services=servicios)
                try:
                    await entregas.entregar(
                        otra["id"], date.fromisoformat(otra["inicio_efectivo"]),
                        date.fromisoformat(otra["fin_efectivo"]), "9", Archivo(pdf("falla")),
                        {"id": usuario_b, "matricula": m_b}, runtime=runtime)
                except RuntimeError as exc:
                    assert "inyectado" in str(exc)
                    # Como en producción (get_transaction): ante una excepción se hace rollback.
                    await conn.rollback()
                    return
                raise AssertionError("La falla inyectada debía propagarse")

        asyncio.run(con_falla_b())
        with connect_local() as conn:
            assert conteos(conn) == antes_falla, "Una falla al confirmar no deja documento, reporte ni archivo nuevos"
        # El original válido anterior sigue intacto.
        assert client.get(f"/dual/alumno/reportes/{r_vieja['reporte_id']}/versiones/1/pdf",
                          headers=alumno_a).content == original_vieja

        # Huérfanos: un archivo sin fila se limpia por referencia; los referenciados no se tocan.
        huerfano = asyncio.run(dual_reports.guardar_documento(pdf("huérfano")))
        with connect_local() as conn:
            referenciadas = {f[0] for f in conn.execute("SELECT clave FROM documentos").fetchall()}
        eliminados = dual_reports.limpiar_huerfanos(referenciadas, antiguedad_segundos=0)
        assert huerfano["clave"] in eliminados and not existe_doc(huerfano["clave"])
        with connect_local() as conn:
            # Solo los documentos de esta corrida: una corrida anterior fallida pudo dejar filas sueltas.
            propios = conn.execute(
                "SELECT d.clave FROM documentos d JOIN reporte_versiones v ON v.documento_id=d.id "
                "JOIN reportes_dual r ON r.id=v.reporte_id WHERE r.matricula IN (%s,%s)", (m_a, m_b)).fetchall()
            assert len(propios) >= 4
            for clave, in propios:
                assert existe_doc(clave), "Se borró un original referenciado"

        # ---------- DP-13: período cerrado ----------
        smoke_periodos.cerrar(client, coordinator, id_periodo_abierto)
        cerrado = {o["id"]: o for o in semanas(alumno_b)}[otra["id"]]
        assert not cerrado["puede_entregar"] and "no está abierta" in cerrado["motivo_bloqueo"]
        entregar(alumno_b, otra, pdf("tarde"), esperado=409)
        # También bloquea el reenvío de un rechazado cuando el período ya no recibe.
        with connect_local() as conn:
            conn.execute("UPDATE reportes_dual SET estado='Rechazada', nota_agente='x' WHERE id=%s",
                         (r_vieja["reporte_id"],))
            conn.commit()
        entregar(alumno_a, w_vieja, pdf("reenvío tardío"), esperado=409)
        # El período queda cerrado: así no se condiciona a otros recorridos (solo puede haber uno abierto).

    print("PASS C05: validación de nota y PDF sin rastro, entrega por obligación sin depender de otras semanas, "
          "versiones inmutables con decisión conservada, original byte a byte, concurrencia, período abierto, "
          "permisos, fallos inyectados y limpieza de huérfanos. HTTP, PostgreSQL y almacenamiento REALES.")
    print("Drive y móvil físico: NO_VERIFICADOS. Datos sintéticos conservados.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError, ApplicationError) as exc:
        print(f"FAIL C05: {exc}", file=sys.stderr)
        raise SystemExit(1)
