"""Smoke C07 con HTTP, PostgreSQL y almacenamiento en disco reales sobre Compose local.

Cierre manual de recepción por ID, revisión con la recepción cerrada, finalización con promedio
congelado e inmutable, orden transaccional entre entrega y cierre (bloqueos de fila reales),
etiqueta de semanas cortadas por un cierre anticipado, período que recibe mientras otro se
finaliza y permisos. Datos sintéticos; no se imprimen contraseñas.

Preparación documentada: los períodos de esta prueba son pasados (para no chocar con el período en
curso de las demás pruebas) y la API no abre períodos terminados, así que se insertan y se marcan
como abiertos con SQL; el instante de cierre de uno se mueve con SQL para simular un cierre
anticipado, porque las semanas de prueba ya terminaron. Todo lo demás ocurre por la API.
"""
from __future__ import annotations

import io
import os
import secrets
import sys
import threading
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz
import httpx
import psycopg

import smoke_periodos
from psycopg.types.json import Jsonb

from app.infrastructure.security.jwt_passwords import hash_password
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, BLOQUES, etiqueta, expect, mes_de, pdf
from smoke_c06 import firma_png
from app.domain import calendar
from app.domain.periods import construir_periodo, fechas_del_periodo
from app.infrastructure.database.queries.dual_coordinador_carrera import QUERIES as QUERIES_CARRERA


def main():
    suffix = secrets.token_hex(5)
    password = "C07a" + secrets.token_urlsafe(18)
    coordinator_email = f"c07.{suffix}@ute.edu.mx"
    tutor_email = f"t07.{suffix}@ute.edu.mx"
    hoy = calendar.hoy()
    lunes = calendar.lunes_de(hoy)
    domingo_actual = calendar.domingo_de(hoy)
    etiqueta_actual = etiqueta(domingo_actual)
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1
    matriculas = {n: str(secrets.randbelow(900000000) + 100000000) for n in ("A", "B", "C", "D", "R1", "R2")}

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C07")

    # Tres períodos pasados sin usar (uno por escenario); años distintos para no repetir etiquetas.
    with connect_local() as conn:
        for anio in (hoy.year - 1, hoy.year, hoy.year + 1):
            for mes, _, _ in BLOQUES:
                inicio, fin = fechas_del_periodo(mes, anio)
                label = construir_periodo(mes, anio)
                conn.execute(
                    "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
                    "VALUES (%s,%s,%s,%s) ON CONFLICT (cuatrimestre) DO NOTHING", (label, label, inicio, fin))
        usados = {f[0] for f in conn.execute("SELECT cuatrimestre FROM ciclos_dual").fetchall()}
        pasados = []
        while len(pasados) < 3:
            anio = secrets.randbelow(24) + 2000
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
    p_principal, p_lock_a, p_lock_b = pasados

    with httpx.Client(base_url=BASE, timeout=90, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        # El límite de inicios de sesión es de 8 por 5 minutos: coordinador, tutor y seis alumnos.
        # Preparación por SQL: sin cambio obligatorio de clave se ahorran dos inicios de sesión.
        with connect_local() as conn:
            conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (coordinator_email,))
            conn.execute(
                "INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                (tutor_email, "Tutor sintético C07", hash_password(password), Jsonb({"tutor_academico": True})))
            conn.commit()
            coordinador_id = conn.execute("SELECT id FROM usuarios WHERE email=%s", (coordinator_email,)).fetchone()[0]
        coordinator = login(coordinator_email, password)
        tutor = login(tutor_email, password)
        expect(client.post("/dual/tutor/firma", headers=tutor,
                           files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)

        smoke_periodos.cerrar_abiertos(client, coordinator)

        # ---------- Preparación de alumnos ----------
        grupo = expect(client.post("/dual/carrera/grupos", headers=tutor, json={
            "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A",
            "turno": "Matutino", "plan": plan, "zona": zone}), 201)
        empresa = expect(client.post("/dual/tutor/empresas", headers=tutor,
                                     json={"nombre": f"Empresa C07 {suffix}"}), 201)

        def importar(periodo_id, nombres):
            filas = "".join(f"{matriculas[n]},Alumno sintético C07 {n}\n" for n in nombres)
            expect(client.post(f"/dual/carrera/grupos/{grupo['id']}/alumnos", headers=tutor,
                               data={"periodo_id": str(periodo_id)},
                               files={"file": ("alumnos.csv", ("matricula,nombre\n" + filas).encode(), "text/csv")}), 200)

        def incorporar(nombre, inicio, baja=None):
            expect(client.patch(f"/dual/tutor/alumnos/{matriculas[nombre]}", headers=tutor, json={
                "alumno_dual": True, "empresa_id": empresa["id"], "fecha_inicio": inicio.isoformat()}), 200)
            if baja:
                expect(client.patch(f"/dual/tutor/alumnos/{matriculas[nombre]}", headers=tutor, json={
                    "alumno_dual": False, "fecha_baja": baja.isoformat()}), 200)

        def inicio_de(periodo):
            return calendar.lunes_de(periodo["inicio"] + timedelta(days=14))

        importar(p_principal["id"], ("A", "B", "C"))
        importar(p_lock_a["id"], ("R1",))
        importar(p_lock_b["id"], ("R2",))
        for nombre, periodo in (("A", p_principal), ("B", p_principal), ("C", p_principal),
                                ("R1", p_lock_a), ("R2", p_lock_b)):
            inicio = inicio_de(periodo)
            incorporar(nombre, inicio, inicio + timedelta(days=27))  # cuatro semanas completas
        importar(p_principal["id"], ("D",))
        incorporar("D", lunes - timedelta(days=14))

        alumno_pw = "C07s" + secrets.token_urlsafe(18)
        sesion = {}
        for nombre, m in matriculas.items():
            expect(client.post("/auth/register", json={"email": f"{m}@ute.edu.mx", "password": alumno_pw}), 201)
            sesion[nombre] = login(f"{m}@ute.edu.mx", alumno_pw)

        def semanas(nombre, label):
            return sorted((o for o in expect(client.get("/dual/alumno/obligaciones", headers=sesion[nombre]), 200)
                           if o["periodo"] == label), key=lambda o: o["ordinal"])

        def entregar(nombre, obligacion, nota, esperado=201):
            respuesta = client.post(
                f"/dual/alumno/obligaciones/{obligacion['id']}/entrega", headers=sesion[nombre],
                data={"fecha_inicio": obligacion["inicio_efectivo"], "fecha_fin": obligacion["fin_efectivo"],
                      "calificacion_alumno": str(nota)},
                files={"archivo": ("reporte.pdf", pdf(f"{nombre} {obligacion['ordinal']}"), "application/pdf")})
            assert respuesta.status_code == esperado, (nombre, esperado, respuesta.status_code, respuesta.text[:200])
            return respuesta.json()

        def revisar(reporte_id, esperado=200, **cuerpo):
            respuesta = client.post(f"/dual/tutor/reportes/{reporte_id}/versiones/1/revision", headers=tutor, json=cuerpo)
            assert respuesta.status_code == esperado, (esperado, respuesta.status_code, respuesta.text[:200])
            return respuesta.json()

        def abrir_pasado(periodo):
            smoke_periodos.cerrar_abiertos(client, coordinator)
            with connect_local() as conn:
                conn.execute("UPDATE ciclos_dual SET abierto=TRUE WHERE id=%s", (periodo["id"],))
                conn.commit()

        def cierre_en_hilo(periodo_id, resultado):
            resultado["respuesta"] = client.post(
                f"/dual/tutor/periodos/{periodo_id}/cierre-recepcion", headers=coordinator, json={"confirmar": True})

        # ---------- AC-15: una entrega en vuelo (bloqueo compartido) hace esperar al cierre ----------
        abrir_pasado(p_lock_a)
        r1 = semanas("R1", p_lock_a["label"])
        assert len(r1) == 4 and all(o["puede_entregar"] for o in r1)
        entregar("R1", r1[0], 8)  # la recepción abierta acepta entregas
        with connect_local() as conn:
            conn.execute("SELECT id FROM ciclos_dual WHERE id=%s FOR SHARE", (p_lock_a["id"],))  # entrega "en vuelo"
            resultado = {}
            hilo = threading.Thread(target=cierre_en_hilo, args=(p_lock_a["id"], resultado))
            hilo.start()
            time.sleep(1.5)
            assert hilo.is_alive(), "El cierre debe esperar a la entrega que tiene el bloqueo compartido"
            conn.commit()
            hilo.join(timeout=30)
        assert resultado["respuesta"].status_code == 200 and resultado["respuesta"].json()["repetido"] is False
        # Con la recepción cerrada ya nadie entrega ni reenvía.
        entregar("R1", r1[1], 8, esperado=409)

        # ---------- AC-15: el cierre confirmado primero hace que la entrega que esperaba reciba 409 ----------
        abrir_pasado(p_lock_b)
        r2 = semanas("R2", p_lock_b["label"])
        with connect_local() as conn:
            conn.execute("SELECT id FROM ciclos_dual WHERE id=%s FOR NO KEY UPDATE", (p_lock_b["id"],))  # cierre en curso
            entrega = {}

            def entrega_en_hilo():
                entrega["respuesta"] = client.post(
                    f"/dual/alumno/obligaciones/{r2[0]['id']}/entrega", headers=sesion["R2"],
                    data={"fecha_inicio": r2[0]["inicio_efectivo"], "fecha_fin": r2[0]["fin_efectivo"],
                          "calificacion_alumno": "9"},
                    files={"archivo": ("reporte.pdf", pdf("compite con el cierre"), "application/pdf")})

            hilo = threading.Thread(target=entrega_en_hilo)
            hilo.start()
            time.sleep(1.5)
            assert hilo.is_alive(), "La entrega debe esperar al cierre que tiene el bloqueo exclusivo"
            conn.execute("UPDATE ciclos_dual SET cerrado=TRUE, abierto=FALSE, cerrado_por=%s, cerrado_at=now() "
                         "WHERE id=%s", (coordinador_id, p_lock_b["id"]))
            conn.commit()
            hilo.join(timeout=30)
        assert entrega["respuesta"].status_code == 409, entrega["respuesta"].text[:200]
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM reportes_dual WHERE obligacion_id=%s",
                                (r2[0]["id"],)).fetchone()[0] == 0, "Una entrega posterior al cierre no deja rastro"

        # ---------- Escenario principal: A, B y C en el período P ----------
        abrir_pasado(p_principal)
        sa, sb, sc = (semanas(n, p_principal["label"]) for n in ("A", "B", "C"))
        assert len(sa) == len(sb) == len(sc) == 4
        reportes = {}
        for ordinal, nota in ((0, 8), (1, 9), (2, 10)):
            reportes[("A", ordinal)] = entregar("A", sa[ordinal], nota)["reporte_id"]
        reportes[("A", 3)] = entregar("A", sa[3], 5)["reporte_id"]
        reportes[("B", 0)] = entregar("B", sb[0], 6)["reporte_id"]
        reportes[("C", 0)] = entregar("C", sc[0], 9)["reporte_id"]
        reportes[("C", 1)] = entregar("C", sc[1], 7)["reporte_id"]
        for ordinal in (0, 1, 2):
            assert revisar(reportes[("A", ordinal)], decision="Aprobada")["estado"] == "Aprobada"
        revisar(reportes[("A", 3)], decision="Rechazada", observacion="Nota ilegible")
        revisar(reportes[("B", 0)], decision="Rechazada", observacion="Falta la firma de la empresa")
        revisar(reportes[("C", 1)], decision="Aprobada")

        id_p = str(p_principal["id"])
        antes = expect(client.get(f"/dual/tutor/periodos/{id_p}/resumen", headers=tutor), 200)
        assert (antes["periodo"]["recepcion"], antes["periodo"]["evaluacion"]) == ("abierta", "en_curso")
        assert antes["conteos"]["pendientes_revision"] == 1 and antes["conteos"]["aprobadas"] == 4
        assert antes["puede_cerrar_recepcion"] is True and antes["puede_finalizar"] is False
        provisional = {a["matricula"]: a for a in antes["alumnos"]}
        assert provisional[matriculas["A"]]["promedio"] == "9.00" and provisional[matriculas["A"]]["definitivo"] is False
        assert provisional[matriculas["B"]]["promedio"] is None
        assert provisional[matriculas["B"]]["promedio_texto"] == "Sin calificación"
        assert provisional[matriculas["C"]]["promedio"] == "7.00"

        # ---------- Permisos y validaciones ----------
        for headers in (tutor, sesion["A"]):
            for ruta in ("cierre-recepcion", "finalizacion"):
                assert client.post(f"/dual/tutor/periodos/{id_p}/{ruta}", headers=headers,
                                   json={"confirmar": True}).status_code == 403
        assert client.post(f"/dual/tutor/periodos/{id_p}/cierre-recepcion", json={"confirmar": True}).status_code == 401
        for cuerpo in ({}, {"confirmar": False}, {"confirmar": "si"}):
            assert client.post(f"/dual/tutor/periodos/{id_p}/cierre-recepcion", headers=coordinator,
                               json=cuerpo).status_code == 422, cuerpo
        assert client.get(f"/dual/tutor/periodos/{id_p}/resumen", headers=sesion["A"]).status_code == 403
        expect(client.get("/dual/tutor/periodos", headers=tutor), 200)
        expect(client.post("/dual/tutor/periodos/00000000-0000-0000-0000-000000000000/cierre-recepcion",
                           headers=coordinator, json={"confirmar": True}), 404)
        expect(client.post("/dual/tutor/periodos/no-es-un-uuid/finalizacion", headers=coordinator,
                           json={"confirmar": True}), 422)
        assert client.post("/dual/tutor/cierre", headers=coordinator,
                           json={"periodo_label": p_principal["label"]}).status_code in (404, 405), "Ruta heredada retirada"
        # No se finaliza sin cerrar la recepción.
        expect(client.post(f"/dual/tutor/periodos/{id_p}/finalizacion", headers=coordinator, json={"confirmar": True}), 409)

        # ---------- AC-14: cierre por ID, sin renombrar, con efectos inmediatos ----------
        cierre = expect(client.post(f"/dual/tutor/periodos/{id_p}/cierre-recepcion", headers=coordinator,
                                    json={"confirmar": True}), 200)
        assert cierre["repetido"] is False and cierre["periodo"]["recepcion"] == "cerrada"
        assert cierre["periodo"]["periodo_label"] == p_principal["label"], "El cierre no renombra el período"
        assert cierre["periodo"]["cierre_efectivo"] == hoy.isoformat()
        assert (cierre["periodo"]["fecha_inicio"], cierre["periodo"]["fecha_fin"]) == (
            p_principal["inicio"].isoformat(), p_principal["fin"].isoformat()), "Las fechas calendario no cambian"
        repetido = expect(client.post(f"/dual/tutor/periodos/{id_p}/cierre-recepcion", headers=coordinator,
                                      json={"confirmar": True}), 200)
        assert repetido["repetido"] is True
        with connect_local() as conn:
            cerrado_por, label = conn.execute("SELECT cerrado_por, periodo_label FROM ciclos_dual WHERE id=%s",
                                              (p_principal["id"],)).fetchone()
        assert cerrado_por == coordinador_id and label == p_principal["label"]
        entregar("C", sc[2], 8, esperado=409)                    # entrega nueva
        entregar("A", sa[3], 6, esperado=409)                    # reenvío de un rechazado (RN-19)
        propia = {o["id"]: o for o in semanas("A", p_principal["label"])}[sa[3]["id"]]
        assert propia["puede_entregar"] is False and "no está abierta" in propia["motivo_bloqueo"]

        # ---------- DP-03 / RN-24: cierre anticipado (se mueve el instante de cierre con SQL) ----------
        semana3 = date.fromisoformat(sa[2]["semana_inicio"])
        with connect_local() as conn:
            conn.execute("UPDATE ciclos_dual SET cerrado_at = ((%s::date + 2) + time '12:00') "
                         "AT TIME ZONE 'America/Mexico_City' WHERE id=%s", (semana3, p_principal["id"]))
            conn.commit()
        cierre_simulado = (semana3 + timedelta(days=2)).isoformat()
        por_ordinal = {o["ordinal"]: o for o in semanas("B", p_principal["label"])}
        assert por_ordinal[1]["entrega"] == "Rechazada" and por_ordinal[1]["estado"] == "RECIBIDA"
        assert por_ordinal[2]["estado"] == "ATRASADA", "La semana que ya había terminado antes del cierre sigue atrasada"
        assert por_ordinal[3]["estado"] == "NO_RECIBIDA_POR_CIERRE"
        assert por_ordinal[4]["estado"] == "NO_RECIBIDA_POR_CIERRE"
        assert por_ordinal[3]["cierre_efectivo"] == cierre_simulado
        c_ordinales = {o["ordinal"]: o["estado"] for o in semanas("C", p_principal["label"])}
        assert (c_ordinales[3], c_ordinales[4]) == ("NO_RECIBIDA_POR_CIERRE",) * 2
        cerrado = expect(client.get(f"/dual/tutor/periodos/{id_p}/resumen", headers=tutor), 200)
        assert cerrado["conteos"]["sin_entrega"] == 5 and cerrado["conteos"]["no_recibidas_por_cierre"] == 4, cerrado["conteos"]
        assert cerrado["periodo"]["cierre_efectivo"] == cierre_simulado

        # ---------- RN-19: el tutor sigue revisando; AC-17: un pendiente impide finalizar ----------
        assert cerrado["conteos"]["pendientes_revision"] == 1 and cerrado["puede_finalizar"] is False
        assert cerrado["motivo_finalizar"] == "Queda 1 reporte pendiente de revisión."
        with connect_local() as conn:
            antes_cierres = conn.execute("SELECT count(*) FROM cierres_alumno_periodo").fetchone()[0]
        sin = expect(client.post(f"/dual/tutor/periodos/{id_p}/finalizacion", headers=coordinator,
                                 json={"confirmar": True}), 409)
        assert "pendiente de revisión" in str(sin)
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM cierres_alumno_periodo").fetchone()[0] == antes_cierres
            assert conn.execute("SELECT evaluacion_finalizada_en FROM ciclos_dual WHERE id=%s",
                                (p_principal["id"],)).fetchone()[0] is None

        # ---------- AC-18: otro período recibe mientras este se revisa y se finaliza ----------
        id_actual = smoke_periodos.abrir_de_prueba(client, coordinator, etiqueta_actual,
                                                   *fechas_del_periodo(mes_de(domingo_actual), domingo_actual.year))
        d_semanas = [o for o in semanas("D", etiqueta_actual) if o["puede_entregar"]]
        assert len(d_semanas) >= 2, "Se necesitan dos semanas del período en curso"
        reporte_d = entregar("D", d_semanas[0], 9)["reporte_id"]
        revisar(reporte_d, decision="Aprobada")
        # El directorio filtrado por período pasa por `resolve_query` (regresión: el filtro con « AND »
        # interno respondía 500) y promedia por período, no por grado.
        listado = expect(client.get("/dual/carrera/alumnos", headers=tutor,
                                    params={"cuatrimestre": etiqueta_actual}), 200)
        fila_d = next(a for a in listado if a["matricula"] == matriculas["D"])
        assert fila_d["reportes_aprobados"] == 1 and float(fila_d["promedio"]) == 9.0, fila_d
        expect(client.get("/dual/carrera/alumnos", headers=tutor, params={
            "cuatrimestre": etiqueta_actual, "grupo": fila_d["nomenclatura"]}), 200)
        expect(client.get("/dual/carrera/alumnos", headers=tutor), 200)
        resumen_actual_antes = expect(client.get(f"/dual/tutor/periodos/{id_actual}/resumen", headers=tutor), 200)
        obligaciones_d_antes = [(o["id"], o["periodo"], o["semana_inicio"]) for o in semanas("D", etiqueta_actual)]

        # El tutor revisa en el período que ya cerró su recepción (con la corrección de nota de C).
        revisar(reportes[("C", 0)], decision="Aprobada", calificacion=10)
        sin_pendientes = expect(client.get(f"/dual/tutor/periodos/{id_p}/resumen", headers=tutor), 200)
        assert sin_pendientes["puede_finalizar"] is True and sin_pendientes["motivo_finalizar"] is None

        # ---------- AC-16/AC-17: finaliza y congela el promedio ----------
        final = expect(client.post(f"/dual/tutor/periodos/{id_p}/finalizacion", headers=coordinator,
                                   json={"confirmar": True}), 200)
        assert final["repetido"] is False and final["periodo"]["evaluacion"] == "finalizada"
        definitivos = {a["matricula"]: a for a in final["alumnos"]}
        assert (definitivos[matriculas["A"]]["promedio"], definitivos[matriculas["A"]]["suma"],
                definitivos[matriculas["A"]]["aprobados"]) == ("9.00", 27, 3)      # 8, 9, 10 y un rechazo
        assert definitivos[matriculas["B"]]["promedio"] is None and definitivos[matriculas["B"]]["promedio_texto"] == "Sin calificación"
        assert (definitivos[matriculas["C"]]["promedio"], definitivos[matriculas["C"]]["suma"]) == ("8.50", 17)
        assert all(a["definitivo"] for a in final["alumnos"])
        with connect_local() as conn:
            filas = {f[0]: f[1:] for f in conn.execute(
                "SELECT matricula, suma, cantidad, promedio FROM cierres_alumno_periodo WHERE periodo_id=%s",
                (p_principal["id"],)).fetchall()}
            assert filas[matriculas["A"]] == (27, 3, Decimal("9.00"))
            assert filas[matriculas["B"]] == (0, 0, None), "Sin aprobados: promedio nulo, no 0.00"
            assert filas[matriculas["C"]] == (17, 2, Decimal("8.50"))
            assert conn.execute("SELECT count(*) FROM cierre_alumno_notas n JOIN cierres_alumno_periodo c ON c.id=n.cierre_id "
                                "WHERE c.periodo_id=%s", (p_principal["id"],)).fetchone()[0] == 5
            assert conn.execute("SELECT evaluacion_finalizada_por FROM ciclos_dual WHERE id=%s",
                                (p_principal["id"],)).fetchone()[0] == coordinador_id
        # Reintento idéntico: estable y sin filas nuevas.
        otra = expect(client.post(f"/dual/tutor/periodos/{id_p}/finalizacion", headers=coordinator,
                                  json={"confirmar": True}), 200)
        assert otra["repetido"] is True
        with connect_local() as conn:
            assert conn.execute("SELECT count(*) FROM cierres_alumno_periodo WHERE periodo_id=%s",
                                (p_principal["id"],)).fetchone()[0] == 3

        # El resultado y el período finalizado son inmutables en la propia base.
        with connect_local() as conn:
            for sentencia, params in (
                    ("UPDATE cierres_alumno_periodo SET promedio=10, suma=30, cantidad=3 WHERE periodo_id=%s", (p_principal["id"],)),
                    ("DELETE FROM cierres_alumno_periodo WHERE periodo_id=%s", (p_principal["id"],)),
                    ("UPDATE cierre_alumno_notas SET nota=1 WHERE cierre_id IN "
                     "(SELECT id FROM cierres_alumno_periodo WHERE periodo_id=%s)", (p_principal["id"],)),
                    ("DELETE FROM cierre_alumno_notas WHERE cierre_id IN "
                     "(SELECT id FROM cierres_alumno_periodo WHERE periodo_id=%s)", (p_principal["id"],)),
                    ("UPDATE ciclos_dual SET abierto=TRUE WHERE id=%s", (p_principal["id"],)),
                    ("UPDATE ciclos_dual SET cerrado=FALSE WHERE id=%s", (p_principal["id"],)),
                    ("UPDATE ciclos_dual SET evaluacion_finalizada_en=NULL, evaluacion_finalizada_por=NULL WHERE id=%s",
                     (p_principal["id"],))):
                try:
                    conn.execute(sentencia, params)
                    raise AssertionError(f"La base permitió: {sentencia[:50]}")
                except psycopg.errors.RaiseException:
                    conn.rollback()
                except psycopg.errors.CheckViolation:
                    conn.rollback()
            # Defensa en profundidad: ni versiones ni revisiones nuevas en un período finalizado.
            version, documento = conn.execute(
                "SELECT v.id, v.documento_id FROM reporte_versiones v JOIN reportes_dual r ON r.id=v.reporte_id "
                "WHERE r.id=%s", (reportes[("A", 3)],)).fetchone()
            tutor_id = conn.execute("SELECT id FROM usuarios WHERE email=%s", (tutor_email,)).fetchone()[0]
            for sentencia, params in (
                    ("INSERT INTO revisiones (version_id,tutor_id,decision,observacion,fecha_inicio,fecha_fin,nota) "
                     "VALUES (%s,%s,'Rechazada','x','2000-01-01','2000-01-02',5)", (version, tutor_id)),
                    ("INSERT INTO reporte_versiones (reporte_id,numero,fecha_inicio,fecha_fin,nota,documento_id) "
                     "VALUES (%s,99,'2000-01-01','2000-01-02',5,%s)", (reportes[("A", 3)], documento))):
                try:
                    conn.execute(sentencia, params)
                    raise AssertionError(f"La base aceptó escritura en un período finalizado: {sentencia[:40]}")
                except psycopg.errors.RaiseException:
                    conn.rollback()
        revisar(reportes[("A", 0)], 409, decision="Rechazada", observacion="ya decidido")

        # El período que recibía no cambió con la finalización del otro (AC-18) y sigue recibiendo.
        resumen_actual_despues = expect(client.get(f"/dual/tutor/periodos/{id_actual}/resumen", headers=tutor), 200)
        assert resumen_actual_despues["periodo"] == resumen_actual_antes["periodo"]
        assert resumen_actual_despues["conteos"] == resumen_actual_antes["conteos"]
        assert resumen_actual_despues["periodo"]["recepcion"] == "abierta"
        assert [(o["id"], o["periodo"], o["semana_inicio"]) for o in semanas("D", etiqueta_actual)] == obligaciones_d_antes
        entregar("D", d_semanas[1], 8)

        # ---------- AC-16: el directorio promedia por período, no por grado ----------
        where = ("WHERE EXISTS (SELECT 1 FROM obligaciones_semanales o JOIN alumnos_dual x ON x.id = o.incorporacion_id "
                 "JOIN ciclos_dual p ON p.id = o.periodo_id WHERE x.matricula = a.matricula AND p.cuatrimestre = %s)")
        consulta = QUERIES_CARRERA["dual.coordinador_carrera.q003"]["sql"].replace("{where}", where)
        with connect_local() as conn:
            filas = conn.execute(consulta, [p_principal["label"]] * 5).fetchall()
        directorio = {f[0]: (f[-2], f[-1]) for f in filas}
        assert directorio[matriculas["A"]] == (3, Decimal("9.00")) and directorio[matriculas["C"]] == (2, Decimal("8.50"))
        assert directorio[matriculas["B"]] == (0, None)

        # ---------- Un período cerrado no se reabre ----------
        smoke_periodos.cerrar(client, coordinator, id_actual)
        inicio_a, fin_a = fechas_del_periodo(mes_de(domingo_actual), domingo_actual.year)
        reabrir = client.post("/dual/tutor/abrir-cuatrimestre", headers=coordinator, json={
            "periodo_label": etiqueta_actual, "fecha_inicio": inicio_a.isoformat(), "fecha_fin": fin_a.isoformat()})
        assert reabrir.status_code == 409 and "no se reabre" in reabrir.text, reabrir.text[:200]

    print("PASS C07: cierre de recepción por ID sin renombrar, orden transaccional con la entrega (ambos órdenes), "
          "revisión con la recepción cerrada, finalización bloqueada por pendientes, promedio 9.00 / Sin calificación / "
          "8.50 congelado e inmutable, etiqueta «no recibida por cierre», otro período recibiendo y permisos. "
          "HTTP, PostgreSQL y almacenamiento REALES.")
    print("Preparación por SQL: períodos pasados abiertos y un instante de cierre movido (simulación del cierre anticipado). "
          "Drive y móvil físico: NO_VERIFICADOS. Datos sintéticos conservados.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f"FAIL C07: {exc}", file=sys.stderr)
        raise SystemExit(1)
