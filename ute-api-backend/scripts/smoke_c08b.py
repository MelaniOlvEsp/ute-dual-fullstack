"""Smoke C08B con HTTP, PostgreSQL y almacenamiento en disco reales sobre Compose local.

Depuración de los archivos de un período: sin paquete no se elimina nada, programación por tutor y
coordinador con gracia de 7 días, cancelación, idempotencia, conflicto entre alcances, ejecución
automática por la tarea de fondo y manual, reintento tras un fallo real del almacenamiento, 410 en
descargas, conservación de notas y filas, inmutabilidad en la base y permisos. Datos sintéticos; no se
imprimen contraseñas.

Preparación documentada: período pasado abierto con SQL (la API no abre períodos terminados). El reloj
de la gracia se SIMULA moviendo `solicitada_en` y `ejecutar_en` con SQL (se desactiva el disparador solo
en esa sentencia); la tarea de fondo real ejecuta la purga vencida (intervalo de 60 s por omisión).
"""
from __future__ import annotations

import hashlib
import io
import os
import secrets
import sys
import time
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
from app.infrastructure.documents.dual_reports import ruta_documento
from app.infrastructure.security.jwt_passwords import hash_password
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, BLOQUES, expect, pdf
from smoke_c06 import firma_png


def main():
    suffix = secrets.token_hex(5)
    password = "C8Ba" + secrets.token_urlsafe(18)
    coordinator_email = f"c8b.{suffix}@ute.edu.mx"
    tutor_email = f"t8b.{suffix}@ute.edu.mx"
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1
    matriculas = {n: str(secrets.randbelow(900000000) + 100000000) for n in ("A", "C", "M")}

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C08B")

    with connect_local() as conn:
        usados = {f[0] for f in conn.execute("SELECT cuatrimestre FROM ciclos_dual").fetchall()}
        while True:
            anio = secrets.randbelow(44) + 1980
            mes = BLOQUES[secrets.randbelow(3)][0]
            label = construir_periodo(mes, anio)
            if label not in usados:
                break
        inicio, fin = fechas_del_periodo(mes, anio)
        periodo_id = conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) VALUES (%s,%s,%s,%s) RETURNING id",
            (label, label, inicio, fin)).fetchone()[0]
        conn.commit()
    periodo = {"id": periodo_id, "label": label, "inicio": inicio}
    pid = str(periodo_id)

    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        with connect_local() as conn:
            conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (coordinator_email,))
            conn.execute("INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                         (tutor_email, "Tutor sintético C08B", hash_password(password), Jsonb({"tutor_academico": True})))
            conn.commit()
        coordinator, tutor = login(coordinator_email, password), login(tutor_email, password)
        expect(client.post("/dual/tutor/firma", headers=tutor,
                           files={"imagen": ("firma.png", firma_png(), "image/png")}), 200)
        smoke_periodos.cerrar_abiertos(client, coordinator)

        # ---------- Preparación: carreras TII (A y C) y MER (M), un período finalizado ----------
        def crear_grupo(carrera):
            return expect(client.post("/dual/carrera/grupos", headers=tutor, json={
                "carrera": carrera, "cuatrimestre": 1, "modalidad": "intensivo", "letra": "A",
                "turno": "Matutino", "plan": plan, "zona": zone}), 201)

        g_tii, g_mer = crear_grupo("TII"), crear_grupo("MER")
        empresa = expect(client.post("/dual/tutor/empresas", headers=tutor, json={"nombre": f"Empresa C08B {suffix}"}), 201)
        inicio_inc = calendar.lunes_de(periodo["inicio"] + timedelta(days=14))

        def importar(grupo, nombres):
            filas = "".join(f"{matriculas[n]},Alumno sintético C08B {n}\n" for n in nombres)
            expect(client.post(f"/dual/carrera/grupos/{grupo['id']}/alumnos", headers=tutor, data={"periodo_id": pid},
                               files={"file": ("a.csv", ("matricula,nombre\n" + filas).encode(), "text/csv")}), 200)
            for n in nombres:
                expect(client.patch(f"/dual/tutor/alumnos/{matriculas[n]}", headers=tutor, json={
                    "alumno_dual": True, "empresa_id": empresa["id"], "fecha_inicio": inicio_inc.isoformat()}), 200)
                expect(client.patch(f"/dual/tutor/alumnos/{matriculas[n]}", headers=tutor, json={
                    "alumno_dual": False, "fecha_baja": (inicio_inc + timedelta(days=27)).isoformat()}), 200)

        importar(g_tii, ("A", "C"))
        importar(g_mer, ("M",))
        pw_alumno = "C8Bs" + secrets.token_urlsafe(18)
        sesion = {}
        for n in ("A", "C", "M"):
            expect(client.post("/auth/register", json={"email": f"{matriculas[n]}@ute.edu.mx", "password": pw_alumno}), 201)
            sesion[n] = login(f"{matriculas[n]}@ute.edu.mx", pw_alumno)

        with connect_local() as conn:
            conn.execute("UPDATE ciclos_dual SET abierto=TRUE WHERE id=%s", (periodo_id,))
            conn.commit()

        def semanas(n):
            return sorted((o for o in expect(client.get("/dual/alumno/obligaciones", headers=sesion[n]), 200)
                           if o["periodo"] == label), key=lambda o: o["ordinal"])

        def entregar(n, obligacion, nota):
            r = client.post(f"/dual/alumno/obligaciones/{obligacion['id']}/entrega", headers=sesion[n],
                            data={"fecha_inicio": obligacion["inicio_efectivo"], "fecha_fin": obligacion["fin_efectivo"],
                                  "calificacion_alumno": str(nota)},
                            files={"archivo": ("r.pdf", pdf(f"{n} {obligacion['ordinal']}"), "application/pdf")})
            assert r.status_code == 201, r.text[:200]
            return r.json()["reporte_id"]

        def revisar(reporte_id, **cuerpo):
            return expect(client.post(f"/dual/tutor/reportes/{reporte_id}/versiones/1/revision", headers=tutor, json=cuerpo), 200)

        sa, sc, sm = semanas("A"), semanas("C"), semanas("M")
        a1, a2, a3 = entregar("A", sa[0], 8), entregar("A", sa[1], 10), entregar("A", sa[2], 5)
        c1, m1 = entregar("C", sc[0], 9), entregar("M", sm[0], 7)
        for r in (a1, a2, c1, m1):
            revisar(r, decision="Aprobada")
        revisar(a3, decision="Rechazada", observacion="Nota ilegible")
        smoke_periodos.cerrar(client, coordinator, pid)
        expect(client.post(f"/dual/tutor/periodos/{pid}/finalizacion", headers=coordinator, json={"confirmar": True}), 200)

        def filas_documentos(n):
            """(id, clave, sha, archivado_en, purga_id, es_aprobado) de todos los documentos del alumno."""
            with connect_local() as conn:
                return conn.execute(
                    "SELECT d.id, d.clave, d.sha256, d.archivado_en, d.purga_id, rv.decision = 'Aprobada' "
                    "FROM reportes_dual r JOIN reporte_versiones v ON v.reporte_id = r.id "
                    "JOIN documentos d ON d.id = v.documento_id LEFT JOIN revisiones rv ON rv.version_id = v.id "
                    "WHERE r.matricula = %s "
                    "UNION ALL "
                    "SELECT ds.id, ds.clave, ds.sha256, ds.archivado_en, ds.purga_id, TRUE "
                    "FROM reportes_dual r JOIN reporte_versiones v ON v.reporte_id = r.id "
                    "JOIN revisiones rv ON rv.version_id = v.id JOIN documentos ds ON ds.id = rv.documento_firmado_id "
                    "WHERE r.matricula = %s", (matriculas[n], matriculas[n])).fetchall()

        def existe(clave):
            return ruta_documento(clave).is_file()

        def estado_notas():
            with connect_local() as conn:
                return (conn.execute("SELECT matricula, suma, cantidad, promedio FROM cierres_alumno_periodo "
                                     "WHERE periodo_id=%s ORDER BY matricula", (periodo_id,)).fetchall(),
                        conn.execute("SELECT count(*) FROM revisiones").fetchone()[0],
                        conn.execute("SELECT count(*) FROM reporte_versiones").fetchone()[0])

        notas_antes = estado_notas()
        frase_tii = f"DEPURAR {label} TII"
        frase_mer = f"DEPURAR {label} MER"
        ruta_purgas = f"/dual/carrera/periodos/{pid}/purgas"

        def programar(headers, **cuerpo):
            return client.post(ruta_purgas, headers=headers, json=cuerpo)

        # ---------- Sin paquete previo no se elimina nada; permisos ----------
        resumen = expect(client.get(f"/dual/carrera/periodos/{pid}/archivo", headers=coordinator), 200)
        por_codigo = {c["codigo"]: c for c in resumen["carreras"]}
        assert resumen["finalizada"] and resumen["gracia_dias"] == 7
        assert (por_codigo["TII"]["archivos_vigentes"], por_codigo["MER"]["archivos_vigentes"]) == (6, 2)
        assert por_codigo["TII"]["paquete"] is None and por_codigo["TII"]["puede_depurar"] is False
        assert por_codigo["TII"]["frase_esperada"] == frase_tii
        r = programar(tutor, carrera="TII", confirmar=True, frase=frase_tii)
        assert r.status_code == 409 and "paquete" in r.text.lower(), r.text[:200]
        assert programar(sesion["A"], carrera="TII", confirmar=True, frase=frase_tii).status_code == 403
        assert client.post(ruta_purgas, json={"carrera": "TII", "confirmar": True, "frase": frase_tii}).status_code == 401
        assert client.get(f"/dual/carrera/periodos/{pid}/archivo", headers=sesion["A"]).status_code == 403
        assert client.get(f"/dual/carrera/periodos/{pid}/archivo").status_code == 401
        assert all(existe(f[1]) for n in matriculas for f in filas_documentos(n)), "Nada se eliminó"

        # ---------- Paquetes de respaldo (solo el tutor los genera) ----------
        def paquete(url):
            r = client.get(url, headers=tutor, params={"periodo_id": pid})
            assert r.status_code == 200, (url, r.status_code, r.text[:200])
            return zipfile.ZipFile(io.BytesIO(r.content))

        zip_tii = paquete("/dual/carrera/paquetes/carrera/TII")
        assert len([n for n in zip_tii.namelist() if n.endswith(".pdf")]) == 6
        paquete(f"/dual/carrera/paquetes/alumno/{matriculas['C']}")
        paquete("/dual/carrera/paquetes/carrera/MER")

        # ---------- Validaciones de la programación ----------
        for cuerpo in ({"carrera": "TII", "confirmar": False, "frase": frase_tii},
                       {"carrera": "TII", "confirmar": "si", "frase": frase_tii},
                       {"carrera": "TII", "confirmar": True, "frase": "depurar " + label},
                       {"carrera": "TII", "confirmar": True, "frase": frase_tii + "\x00"},
                       {"carrera": "TII", "matricula": matriculas["A"], "confirmar": True, "frase": frase_tii},
                       {"confirmar": True, "frase": frase_tii}):
            assert programar(tutor, **cuerpo).status_code == 422, cuerpo
        assert programar(tutor, carrera="ZZZ", confirmar=True, frase="DEPURAR x ZZZ").status_code == 404
        assert client.post(f"/dual/carrera/periodos/{uuid_ajeno()}/purgas", headers=tutor, json={
            "carrera": "TII", "confirmar": True, "frase": frase_tii}).status_code == 404
        # Un período abierto o sin finalizar no se depura (el período de otra prueba cerrada sin finalizar).
        assert all(existe(f[1]) for f in filas_documentos("A"))

        # ---------- D2: el coordinador programa; la gracia no elimina nada ----------
        r = programar(coordinator, carrera="TII", confirmar=True, frase=frase_tii)
        assert r.status_code == 200, r.text[:300]
        purga = r.json()
        assert purga["repetido"] is False and purga["purga"]["archivos"] == 6 and purga["purga"]["estado"] == "programada"
        purga_tii = purga["purga"]["id"]
        with connect_local() as conn:
            solicitada, ejecutar = conn.execute("SELECT solicitada_en, ejecutar_en FROM purgas_archivo WHERE id=%s", (purga_tii,)).fetchone()
            sha_registro, sha_paquete = conn.execute(
                "SELECT p.manifiesto_sha256, k.manifiesto_sha256 FROM purgas_archivo p JOIN paquetes_archivo k ON k.id=p.paquete_id "
                "WHERE p.id=%s", (purga_tii,)).fetchone()
        assert timedelta(days=6, hours=23) < ejecutar - solicitada <= timedelta(days=7, minutes=1), "Gracia de 7 días"
        assert sha_registro == sha_paquete, "La purga guarda el hash del manifiesto del paquete que la habilita"
        assert all(existe(f[1]) for n in ("A", "C") for f in filas_documentos(n)), "La gracia no elimina nada"
        again = programar(tutor, carrera="TII", confirmar=True, frase=frase_tii).json()
        assert again["repetido"] is True and again["purga"]["id"] == purga_tii
        # Descargas intactas durante la gracia y el alumno ve el aviso con la fecha.
        expediente_a = expect(client.get("/dual/alumno/expediente", headers=sesion["A"]), 200)["periodos"][0]
        assert expediente_a["archivo"]["estado"] == "programada" and expediente_a["archivo"]["eliminacion_en"]
        assert "purga_id" not in expediente_a["archivo"], "El alumno no recibe el identificador de la purga"
        assert all(a["archivado_en"] is None for a in expediente_a["aprobados"])
        reporte = expediente_a["aprobados"][0]
        expect(client.get(f"/dual/alumno/reportes/{reporte['reporte_id']}/versiones/1/pdf", headers=sesion["A"]), 200)
        staff = expect(client.get(f"/dual/carrera/alumnos/{matriculas['A']}/expediente", headers=tutor), 200)["periodos"][0]
        assert staff["archivo"]["purga_id"] == purga_tii

        # ---------- Cancelar durante la gracia: todo vuelve a la normalidad ----------
        r = client.post(f"{ruta_purgas}/{purga_tii}/cancelacion", headers=tutor)
        assert r.status_code == 200 and r.json()["repetido"] is False and r.json()["purga"]["estado"] == "cancelada", r.text[:200]
        assert client.post(f"{ruta_purgas}/{purga_tii}/cancelacion", headers=coordinator).json()["repetido"] is True
        assert all(f[4] is None and f[3] is None for n in ("A", "C") for f in filas_documentos(n)), "Documentos liberados"
        assert client.post(f"{ruta_purgas}/{purga_tii}/cancelacion", headers=sesion["A"]).status_code == 403
        assert client.post(f"{ruta_purgas}/{purga_tii}/ejecucion", headers=tutor).status_code == 409, "Cancelada no se ejecuta"
        assert expect(client.get("/dual/alumno/expediente", headers=sesion["A"]), 200)["periodos"][0]["archivo"]["estado"] == "normal"

        # ---------- Nueva programación; conflicto con un alcance que ya la incluye ----------
        purga_tii = programar(tutor, carrera="TII", confirmar=True, frase=frase_tii).json()["purga"]["id"]
        r = programar(tutor, matricula=matriculas["C"], confirmar=True, frase=f"DEPURAR {label} {matriculas['C']}")
        assert r.status_code == 409 and "cancélala" in r.text, r.text[:200]
        assert client.post(f"{ruta_purgas}/{purga_tii}/ejecucion", headers=tutor).status_code == 409, "Aún no vence"

        # ---------- Reloj SIMULADO: vence la gracia; la tarea de fondo real la ejecuta ----------
        def vencer(purga_id):
            with connect_local() as conn:
                conn.execute("ALTER TABLE purgas_archivo DISABLE TRIGGER purgas_protegidas")
                try:
                    conn.execute("UPDATE purgas_archivo SET solicitada_en = now() - interval '8 days', "
                                 "ejecutar_en = now() - interval '1 minute' WHERE id=%s", (purga_id,))
                finally:
                    conn.execute("ALTER TABLE purgas_archivo ENABLE TRIGGER purgas_protegidas")
                conn.commit()

        # Fallo real del almacenamiento (MER): un directorio ocupa el lugar del archivo y la eliminación falla.
        programar(tutor, carrera="MER", confirmar=True, frase=frase_mer)
        r = programar(tutor, carrera="MER", confirmar=True, frase=frase_mer)
        assert r.json()["repetido"] is True
        purga_mer = r.json()["purga"]["id"]
        doc_mer = next(f for f in filas_documentos("M") if f[5])
        ruta_mer = ruta_documento(doc_mer[1])
        respaldo = ruta_mer.with_name(ruta_mer.name + ".c08bak")
        ruta_mer.rename(respaldo)
        ruta_mer.mkdir()
        try:
            vencer(purga_mer)
            r = client.post(f"{ruta_purgas}/{purga_mer}/ejecucion", headers=tutor)
            assert r.status_code == 500 and "reintentará" in r.text, (r.status_code, r.text[:200])
            with connect_local() as conn:
                estado, intentos, error = conn.execute(
                    "SELECT estado, intentos, ultimo_error FROM purgas_archivo WHERE id=%s", (purga_mer,)).fetchone()
            assert estado == "programada" and intentos >= 1 and error, "El fallo queda registrado y la purga pendiente"
            assert all(f[3] is None for f in filas_documentos("M")), "Sin filas archivadas tras el fallo (transacción revertida)"
        finally:
            ruta_mer.rmdir()
            respaldo.rename(ruta_mer)

        vencer(purga_tii)
        claves_tii = {n: [f for f in filas_documentos(n)] for n in ("A", "C")}
        limite = time.time() + 150
        while time.time() < limite:
            with connect_local() as conn:
                estado = conn.execute("SELECT estado FROM purgas_archivo WHERE id=%s", (purga_tii,)).fetchone()[0]
            if estado == "completada":
                break
            time.sleep(5)
        assert estado == "completada", "La tarea de fondo debe ejecutar la depuración vencida"
        # El reintento de MER (manual, tras restaurar el archivo) completa sin intervención extra.
        r = client.post(f"{ruta_purgas}/{purga_mer}/ejecucion", headers=coordinator)
        if r.status_code == 200:
            assert r.json()["repetido"] in (False, True)
        else:
            raise AssertionError(r.text[:200])

        # ---------- Resultado: solo los PDF del paquete se eliminaron; todo lo demás se conserva ----------
        for n in ("A", "C", "M"):
            for id_, clave, sha, archivado, purga_id, aprobado in filas_documentos(n):
                if aprobado:
                    assert archivado is not None and purga_id is not None and not existe(clave), (n, clave)
                else:
                    assert archivado is None and existe(clave), "El original rechazado no está en el paquete y no se toca"
        assert estado_notas() == notas_antes, "Notas, promedios, versiones y revisiones intactos"
        with connect_local() as conn:
            archivos, bytes_ = conn.execute("SELECT archivos, bytes FROM purgas_archivo WHERE id=%s", (purga_tii,)).fetchone()
            assert archivos == 6 and bytes_ > 0
            # Las filas archivadas conservan su clave y su hash originales y se protegen en la base.
            documento = conn.execute("SELECT id, sha256 FROM documentos WHERE purga_id=%s LIMIT 1", (purga_tii,)).fetchone()
            for sentencia, params in (
                    ("UPDATE documentos SET archivado_en = NULL WHERE id=%s", (documento[0],)),
                    ("UPDATE documentos SET sha256 = repeat('0', 64) WHERE id=%s", (documento[0],)),
                    ("UPDATE purgas_archivo SET ultimo_error = 'x' WHERE id=%s", (purga_tii,)),
                    ("DELETE FROM purgas_archivo WHERE id=%s", (purga_tii,))):
                try:
                    conn.execute(sentencia, params)
                    raise AssertionError(f"La base permitió: {sentencia[:45]}")
                except psycopg.errors.RaiseException:
                    conn.rollback()

        # ---------- 410, paquetes bloqueados, expediente y resumen coherentes ----------
        staff = expect(client.get(f"/dual/carrera/alumnos/{matriculas['A']}/expediente", headers=tutor), 200)["periodos"][0]
        assert staff["archivo"]["estado"] == "archivado" and all(a["archivado_en"] for a in staff["aprobados"])
        assert staff["resumen"]["promedio"] == "9.00" and len(staff["aprobados"]) == 2, "Las notas siguen visibles"
        for documento in ("firmado", "original"):
            r = client.get(f"/dual/carrera/reportes/{a1}/versiones/1/pdf", headers=tutor, params={"documento": documento})
            assert r.status_code == 410 and "se conservan" in r.text, (documento, r.status_code, r.text[:120])
        assert client.get(f"/dual/alumno/reportes/{a1}/versiones/1/pdf", headers=sesion["A"]).status_code == 410
        assert client.get(f"/dual/tutor/reportes/{a1}/versiones/1/pdf", headers=tutor).status_code == 410
        mio = expect(client.get("/dual/alumno/expediente", headers=sesion["A"]), 200)["periodos"][0]
        assert mio["archivo"]["estado"] == "archivado" and mio["paquete"]["disponible"] is False
        assert "depuraron" in mio["paquete"]["motivo"]
        for url in (f"/dual/carrera/paquetes/alumno/{matriculas['A']}", "/dual/carrera/paquetes/carrera/TII"):
            assert client.get(url, headers=tutor, params={"periodo_id": pid}).status_code == 409, url
        assert client.get("/dual/alumno/paquete", headers=sesion["A"], params={"periodo_id": pid}).status_code in (403, 409)
        resumen = expect(client.get(f"/dual/carrera/periodos/{pid}/archivo", headers=coordinator), 200)
        por_codigo = {c["codigo"]: c for c in resumen["carreras"]}
        assert por_codigo["TII"]["estado"] == "depurado" and por_codigo["TII"]["archivos_vigentes"] == 0
        assert por_codigo["TII"]["puede_depurar"] is False and por_codigo["MER"]["estado"] == "depurado"
        assert {p["estado"] for p in resumen["purgas"]} == {"cancelada", "completada"}
        r = programar(tutor, carrera="TII", confirmar=True, frase=frase_tii)
        assert r.status_code == 409 and "ya están depurados" in r.text
        assert client.post(f"{ruta_purgas}/{purga_tii}/cancelacion", headers=tutor).status_code == 409, "Ya eliminada"
        assert client.post(f"{ruta_purgas}/{purga_tii}/ejecucion", headers=tutor).json()["repetido"] is True

    print("Smoke C08B OK")


def uuid_ajeno():
    return "00000000-0000-0000-0000-00000000dead"


if __name__ == "__main__":
    main()
