"""Smoke C04 con HTTP y PostgreSQL reales sobre Compose local.

Parte 1 (HTTP, fecha de hoy real): obligaciones, semana parcial, baja inclusiva, estados,
permisos y concurrencia. Parte 2 (casos de uso reales con reloj inyectado y la misma BD):
período por domingo (AC-07), corte del lunes (AC-08) y período creado después. Los datos
sintéticos se conservan; no se imprimen contraseñas.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
import os
import secrets
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
import psycopg
from psycopg.rows import dict_row

from local_admin import connect_local, create_coordinator
from app.application.use_cases.dual import obligaciones
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from app.infrastructure.config.settings import settings
from app.infrastructure.database.repository import QueryCursorAdapter

BASE = os.environ.get("API_URL", "http://api:8000")
if BASE not in ("http://api:8000", "http://127.0.0.1:8001"):
    raise SystemExit("Destino HTTP no permitido para C04")

BLOQUES = (("Enero", 1, 4), ("Mayo", 5, 8), ("Septiembre", 9, 12))


def expect(response, status):
    if response.status_code != status:
        raise AssertionError(
            f"{response.request.method} {response.request.url.path}: "
            f"esperado {status}, recibido {response.status_code}: {response.text[:300]}")
    return response.json()


def etiqueta(fecha: date) -> str:
    for mes, ini, fin in BLOQUES:
        if ini <= fecha.month <= fin:
            return construir_periodo(mes, fecha.year)
    raise AssertionError("mes fuera de rango")


def asegurar_periodo(conn, label: str, mes: str, anio: int) -> None:
    inicio, fin = fechas_del_periodo(mes, anio)
    conn.execute(
        "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
        "VALUES (%s,%s,%s,%s) ON CONFLICT (cuatrimestre) DO NOTHING",
        (label, label, inicio, fin))


class Gateway:
    """Puerto de base de datos sobre una conexión real, para ejecutar casos de uso con reloj inyectado."""

    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def transaction(self):
        async with self.conn.cursor() as cur:
            yield QueryCursorAdapter(cur)
        await self.conn.commit()


async def con_runtime(coro_factory):
    async with await psycopg.AsyncConnection.connect(settings.db.db_dsn, row_factory=dict_row) as conn:
        return await coro_factory(SimpleNamespace(database=Gateway(conn)))


def main():
    suffix = secrets.token_hex(5)
    password = "C04a" + secrets.token_urlsafe(18)
    changed = "C04b" + secrets.token_urlsafe(18)
    coordinator_email = f"c04.{suffix}@ute.edu.mx"
    tutor_email = f"t04.{suffix}@ute.edu.mx"
    hoy = calendar.hoy()
    lunes = calendar.lunes_de(hoy)
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1

    def matricula():
        return str(secrets.randbelow(900000000) + 100000000)

    m_a, m_b, m_c, m_d, m_e, m_f = (matricula() for _ in range(6))

    # Años lejanos únicos por ejecución: no chocan con períodos reales ni de otras corridas.
    while True:
        anio_e = secrets.randbelow(3000) + 3000
        if date(anio_e, 4, 30).weekday() != 6:  # el 30 de abril no cae en domingo: hay semana cruzada
            break
    anio_f = secrets.randbelow(3000) + 6100

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C04")
    with connect_local() as conn:
        # Períodos reales alrededor de hoy (idempotente) y de la prueba con reloj inyectado.
        for anio in (hoy.year - 1, hoy.year, hoy.year + 1):
            for mes, _, _ in BLOQUES:
                asegurar_periodo(conn, construir_periodo(mes, anio), mes, anio)
        for mes in ("Enero", "Mayo"):
            asegurar_periodo(conn, construir_periodo(mes, anio_e), mes, anio_e)
        periodo_hoy = conn.execute(
            "SELECT id FROM ciclos_dual WHERE cuatrimestre=%s", (etiqueta(hoy),)).fetchone()[0]
        conn.commit()  # el intento solapado de abajo hace rollback y no debe deshacer los períodos

        # DB: dos períodos con fechas solapadas son imposibles (DP-04).
        try:
            conn.execute(
                "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) VALUES (%s,%s,%s,%s)",
                (f"Septiembre-Diciembre {anio_e}", f"Septiembre-Diciembre {anio_e}",
                 date(anio_e, 8, 15), date(anio_e, 12, 31)))
            raise AssertionError("La restricción de no solapamiento no rechazó el período")
        except psycopg.errors.ExclusionViolation:
            conn.rollback()

    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        temp = login(coordinator_email, password)
        expect(client.post("/auth/cambiar-password", headers=temp,
                           json={"password_actual": password, "password_nueva": changed}), 200)
        coordinator = login(coordinator_email, changed)
        created = expect(client.post("/auth/tutores", headers=coordinator,
                                     json={"nombre": "Tutor sintético C04", "email": tutor_email}), 201)
        tutor_temp = login(tutor_email, created["password_temporal"])
        expect(client.post("/auth/cambiar-password", headers=tutor_temp,
                           json={"password_actual": created["password_temporal"], "password_nueva": changed}), 200)
        tutor = login(tutor_email, changed)

        group = expect(client.post("/dual/carrera/grupos", headers=tutor, json={
            "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A",
            "turno": "Matutino", "plan": plan, "zona": zone}), 201)
        rows = "".join(f"{m},Alumno sintético C04 {i}\n" for i, m in enumerate((m_a, m_b, m_c, m_d, m_e, m_f)))
        csv = {"file": ("alumnos.csv", ("matricula,nombre\n" + rows).encode(), "text/csv")}
        expect(client.post(f"/dual/carrera/grupos/{group['id']}/alumnos", headers=tutor,
                           data={"periodo_id": str(periodo_hoy)}, files=csv), 200)
        company = expect(client.post("/dual/tutor/empresas", headers=tutor,
                                     json={"nombre": f"Empresa C04 {suffix}"}), 201)

        def incorporar(m, inicio):
            expect(client.patch(f"/dual/tutor/alumnos/{m}", headers=tutor, json={
                "alumno_dual": True, "empresa_id": company["id"], "fecha_inicio": inicio.isoformat()}), 200)

        def dar_de_baja(m, baja):
            expect(client.patch(f"/dual/tutor/alumnos/{m}", headers=tutor,
                                json={"alumno_dual": False, "fecha_baja": baja.isoformat()}), 200)

        def semanas(m, periodo=None, headers=None, ruta=None):
            return expect(client.get(ruta or f"/dual/tutor/alumnos/{m}/obligaciones",
                                     headers=headers or tutor,
                                     params={"periodo": periodo} if periodo else None), 200)

        # A: empieza un miércoles hace dos semanas (primera semana parcial). B: lunes hace una semana.
        inicio_a = lunes - timedelta(days=14) + timedelta(days=2)
        inicio_b = lunes - timedelta(days=7)
        incorporar(m_a, inicio_a)
        incorporar(m_b, inicio_b)
        # C: baja a mitad de semana. D: baja retroactiva con semanas posteriores ya generadas.
        incorporar(m_c, lunes - timedelta(days=21))
        baja_c = lunes - timedelta(days=14) + timedelta(days=2)
        dar_de_baja(m_c, baja_c)
        incorporar(m_d, lunes - timedelta(days=28))
        baja_d = lunes - timedelta(days=21) + timedelta(days=2)
        dar_de_baja(m_d, baja_d)

        # AC-06: A tiene semana parcial de miércoles a domingo; A y B tienen obligaciones propias.
        a = semanas(m_a)
        esperadas_a = calendar.semanas_incorporacion(inicio_a, None, hoy)
        assert len(a) == len(esperadas_a) == 3, (len(a), len(esperadas_a))
        primera = min(a, key=lambda o: o["ordinal"])
        assert primera["parcial"] and primera["inicio_efectivo"] == inicio_a.isoformat()
        assert primera["semana_inicio"] == (lunes - timedelta(days=14)).isoformat()
        assert [o["ordinal"] for o in sorted(a, key=lambda o: o["ordinal"])] == [1, 2, 3]
        b = semanas(m_b)
        assert len(b) == 2 and not any(o["parcial"] for o in b)
        assert {o["incorporacion_id"] for o in a}.isdisjoint({o["incorporacion_id"] for o in b})

        # RN-09: semanas anteriores atrasadas, la vigente pendiente (no se habilita ninguna futura).
        por_ordinal = {o["ordinal"]: o for o in a}
        assert por_ordinal[1]["estado"] == "ATRASADA" and por_ordinal[2]["estado"] == "ATRASADA"
        assert por_ordinal[3]["estado"] == "PENDIENTE"
        assert max(o["semana_inicio"] for o in a) == lunes.isoformat(), "No debe haber semanas futuras"
        # AC-07 (fechas reales): el período de cada semana es el de su domingo.
        for o in a:
            assert o["periodo"] == etiqueta(date.fromisoformat(o["semana_fin"])), o

        # RN-10 / provisional: una semana recibida no bloquea a las demás.
        with connect_local() as conn:
            conn.execute(
                "INSERT INTO reportes_dual (matricula,cuatrimestre,semana,calificacion_alumno,fecha_inicio,fecha_fin) "
                "VALUES (%s,%s,1,8,%s,%s)",
                (m_a, etiqueta(date.fromisoformat(primera["semana_fin"])),
                 primera["semana_inicio"], primera["semana_fin"]))
        a2 = {o["ordinal"]: o for o in semanas(m_a)}
        assert a2[1]["estado"] == "RECIBIDA" and a2[2]["estado"] == "ATRASADA" and a2[3]["estado"] == "PENDIENTE"

        # Bandeja del tutor: atrasadas y pendiente de A y B, sin la semana ya recibida.
        bandeja = expect(client.get("/dual/tutor/alumnos-atrasados", headers=tutor), 200)
        de_a = [r for r in bandeja if r["matricula"] == m_a]
        de_b = [r for r in bandeja if r["matricula"] == m_b]
        assert sorted(r["semana_esperada"] for r in de_a) == [2, 3]
        assert sorted(r["status"] for r in de_a) == ["Overdue", "Pending"]
        assert sorted(r["semana_esperada"] for r in de_b) == [1, 2]
        assert not [r for r in bandeja if r["matricula"] in (m_c, m_d)], "Una baja no genera pendientes"
        assert all(r["nomenclatura"] == group["nomenclatura"] for r in de_a + de_b)
        sin_reporte = expect(client.get("/dual/tutor/alumnos-sin-reporte", headers=tutor, params={
            "cuatrimestre": etiqueta(date.fromisoformat(por_ordinal[2]["semana_fin"])), "semana": 2}), 200)
        assert m_a in {r["matricula"] for r in sin_reporte}

        # RN-06 / DP-03: baja inclusiva con última semana parcial; nada posterior (ni retroactivo).
        c = sorted(semanas(m_c), key=lambda o: o["ordinal"])
        assert len(c) == 2 and not c[0]["parcial"] and c[1]["parcial"]
        assert c[1]["fin_efectivo"] == baja_c.isoformat()
        d = sorted(semanas(m_d), key=lambda o: o["ordinal"])
        assert len(d) == 2 and d[1]["fin_efectivo"] == baja_d.isoformat()
        with connect_local() as conn:
            total_d = conn.execute(
                "SELECT count(*) FROM obligaciones_semanales o JOIN alumnos_dual ad ON ad.id=o.incorporacion_id "
                "WHERE ad.matricula=%s", (m_d,)).fetchone()[0]
        assert total_d > len(d), "Las semanas posteriores a la baja se excluyen, no se borran"

        # Idempotencia y concurrencia: solicitudes simultáneas no duplican obligaciones.
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda _: semanas(m_a), range(6)))
            list(pool.map(lambda _: expect(client.get("/dual/tutor/alumnos-atrasados", headers=tutor), 200), range(4)))
        with connect_local() as conn:
            assert conn.execute(
                "SELECT count(*) FROM obligaciones_semanales o JOIN alumnos_dual ad ON ad.id=o.incorporacion_id "
                "WHERE ad.matricula=%s", (m_a,)).fetchone()[0] == 3
            assert conn.execute(
                "SELECT count(*) FROM (SELECT incorporacion_id, semana_inicio FROM obligaciones_semanales "
                "GROUP BY 1,2 HAVING count(*) > 1) d").fetchone()[0] == 0

        # Permisos: el alumno solo ve lo propio; ajenos e inexistentes no se exponen.
        alumno_pw = "C04s" + secrets.token_urlsafe(18)
        sesiones = {}
        for m in (m_a, m_b):
            expect(client.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": alumno_pw}), 201)
            sesiones[m] = login(f"{m}@ute.edu.mx", alumno_pw)
        propias = semanas(None, headers=sesiones[m_a], ruta="/dual/alumno/obligaciones")
        assert len(propias) == 3 and {o["incorporacion_id"] for o in propias} == {o["incorporacion_id"] for o in a}
        assert len(semanas(None, headers=sesiones[m_b], ruta="/dual/alumno/obligaciones")) == 2
        expect(client.get(f"/dual/tutor/alumnos/{m_b}/obligaciones", headers=sesiones[m_a]), 403)
        expect(client.get("/dual/tutor/alumnos-atrasados", headers=sesiones[m_a]), 403)
        expect(client.get("/dual/alumno/obligaciones", headers=tutor), 403)
        expect(client.get("/dual/tutor/alumnos/000000000/obligaciones", headers=tutor), 404)
        expect(client.get("/dual/alumno/obligaciones"), 401)

        # DP-04 / MP-18: solo el coordinador abre períodos y consulta el actual; tutor y alumno reciben 403.
        apertura_e = {
            "periodo_label": f"Septiembre-Diciembre {anio_e}",
            "fecha_inicio": date(anio_e, 8, 1).isoformat(), "fecha_fin": date(anio_e, 12, 15).isoformat()}
        expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=tutor, json=apertura_e), 403)
        expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=sesiones[m_a], json=apertura_e), 403)
        expect(client.get("/dual/tutor/cuatrimestre-actual", headers=tutor), 403)
        expect(client.get("/dual/tutor/cuatrimestre-actual", headers=sesiones[m_a]), 403)
        expect(client.get("/dual/tutor/cuatrimestre-actual", headers=coordinator), 200)
        # No se abre un período con fechas solapadas; no queda fila creada.
        solapado = expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=coordinator, json=apertura_e), 409)
        assert "solapan" in str(solapado)
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM ciclos_dual WHERE cuatrimestre=%s",
                                (f"Septiembre-Diciembre {anio_e}",)).fetchone()[0] == 0

        # Casos de uso reales con reloj inyectado.
        # AC-07 / AC-08: incorporación el 30 de abril; la semana termina en mayo.
        inicio_e = date(anio_e, 4, 30)
        incorporar(m_e, inicio_e)
        domingo_e = calendar.domingo_de(inicio_e)
        assert domingo_e.month == 5 and calendar.lunes_de(inicio_e).month == 4

        async def parte_e(rt):
            viernes = await obligaciones.mis_obligaciones(m_e, None, runtime=rt, hoy=inicio_e)
            assert len(viernes) == 1 and viernes[0]["parcial"] and viernes[0]["estado"] == "PENDIENTE"
            assert viernes[0]["periodo"] == f"Mayo-Agosto {anio_e}", viernes[0]["periodo"]
            domingo = await obligaciones.mis_obligaciones(m_e, None, runtime=rt, hoy=domingo_e)
            assert [o["estado"] for o in domingo if o["ordinal"] == 1] == ["PENDIENTE"]  # AC-08: aún se puede entregar
            lunes_sig = await obligaciones.mis_obligaciones(
                m_e, None, runtime=rt, hoy=domingo_e + timedelta(days=1))
            primera_e = next(o for o in lunes_sig if o["ordinal"] == 1)
            assert primera_e["estado"] == "ATRASADA" and len(lunes_sig) == 2          # AC-08: el lunes es atraso
            junio = await obligaciones.mis_obligaciones(m_e, None, runtime=rt, hoy=date(anio_e, 6, 10))
            assert next(o for o in junio if o["ordinal"] == 1)["periodo"] == f"Mayo-Agosto {anio_e}"  # AC-07
            assert [o["ordinal"] for o in sorted(junio, key=lambda o: o["ordinal"])] == list(range(1, len(junio) + 1))
            filtradas = await obligaciones.mis_obligaciones(
                m_e, f"Mayo-Agosto {anio_e}", runtime=rt, hoy=date(anio_e, 6, 10))
            assert all(o["periodo"] == f"Mayo-Agosto {anio_e}" for o in filtradas)
            assert {o["ordinal"] for o in filtradas} <= {o["ordinal"] for o in junio}  # el ordinal no depende del filtro

        asyncio.run(con_runtime(parte_e))

        # Período creado después: las obligaciones sin período lo reciben al abrirlo.
        inicio_f = date(anio_f, 1, 5)
        incorporar(m_f, inicio_f)

        async def antes_f(rt):
            filas = await obligaciones.mis_obligaciones(m_f, None, runtime=rt, hoy=date(anio_f, 1, 20))
            assert filas and all(o["periodo"] is None for o in filas), "Sin período hasta que exista"

        async def despues_f(rt):
            filas = await obligaciones.mis_obligaciones(m_f, None, runtime=rt, hoy=date(anio_f, 1, 20))
            assert all(o["periodo"] == f"Enero-Abril {anio_f}" for o in filas), filas

        asyncio.run(con_runtime(antes_f))
        inicio_p, fin_p = fechas_del_periodo("Enero", anio_f)
        expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=coordinator, json={
            "periodo_label": f"Enero-Abril {anio_f}",
            "fecha_inicio": inicio_p.isoformat(), "fecha_fin": fin_p.isoformat()}), 200)
        expect(client.post("/dual/tutor/cierre", headers=coordinator,
                           json={"periodo_label": f"Enero-Abril {anio_f}"}), 200)
        asyncio.run(con_runtime(despues_f))

        # M2: el período en curso (inicio anterior a hoy) se puede abrir; uno ya terminado no.
        for mes, ini, fin in BLOQUES:
            if ini <= hoy.month <= fin:
                mes_actual = mes
                break
        inicio_c, fin_c = fechas_del_periodo(mes_actual, hoy.year)
        etiqueta_c = construir_periodo(mes_actual, hoy.year)
        if inicio_c < hoy:
            en_curso = expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=coordinator, json={
                "periodo_label": etiqueta_c,
                "fecha_inicio": inicio_c.isoformat(), "fecha_fin": fin_c.isoformat()}), 200)
            assert en_curso["cuatrimestre"]["periodo_label"] == etiqueta_c
            actual = expect(client.get("/dual/tutor/cuatrimestre-actual", headers=coordinator), 200)
            assert actual["abierto"] and actual["periodo_label"] == etiqueta_c
            expect(client.post("/dual/tutor/cierre", headers=coordinator, json={"periodo_label": etiqueta_c}), 200)
        anterior = [(m, i, f) for m, i, f in BLOQUES if f < hoy.month]
        if anterior:
            mes_a, _, _ = anterior[-1]
            inicio_a2, fin_a2 = fechas_del_periodo(mes_a, hoy.year)
            terminado = expect(client.post("/dual/tutor/abrir-cuatrimestre", headers=coordinator, json={
                "periodo_label": construir_periodo(mes_a, hoy.year),
                "fecha_inicio": inicio_a2.isoformat(), "fecha_fin": fin_a2.isoformat()}), 422)
            assert "en curso o futuros" in str(terminado)

    print("PASS C04: obligaciones por incorporación (semana parcial, baja inclusiva, sin semanas futuras), "
          "período por domingo, corte del lunes con reloj inyectado, permisos, concurrencia, "
          "no solapamiento de períodos y período posterior. HTTP y PostgreSQL REALES.")
    print("Reloj inyectado solo en la Parte 2 (casos de uso con BD real). Integraciones externas y "
          "móvil físico: NO_VERIFICADAS. Datos sintéticos conservados.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f"FAIL C04: {exc}", file=sys.stderr)
        raise SystemExit(1)
