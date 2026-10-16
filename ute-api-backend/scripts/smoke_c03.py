"""Smoke C03 con HTTP y PostgreSQL reales sobre Compose local.

Crea fixtures sintéticos identificables, conserva su historial y no imprime secretos.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx

from local_admin import connect_local, create_coordinator


BASE = os.environ.get("API_URL", "http://api:8000")
if BASE not in ("http://api:8000", "http://127.0.0.1:8001"):
    raise SystemExit("Destino HTTP no permitido para C03")


def expect(response, status):
    if response.status_code != status:
        raise AssertionError(
            f"{response.request.method} {response.request.url.path}: "
            f"esperado {status}, recibido {response.status_code}: {response.text[:300]}"
        )
    return response.json()


def main():
    suffix = secrets.token_hex(5)
    password = "C03a" + secrets.token_urlsafe(18)
    changed = "C03b" + secrets.token_urlsafe(18)
    coordinator_email = f"c03.{suffix}@ute.edu.mx"
    tutor_email = f"t03.{suffix}@ute.edu.mx"
    matricula = str(secrets.randbelow(900000000) + 100000000)
    year = 3000 + secrets.randbelow(6000)
    period_one = f"Enero-Abril {year}"
    period_two = f"Mayo-Agosto {year}"
    plan = str(secrets.randbelow(90) + 10)
    zone = secrets.randbelow(30000) + 1
    # C04: los períodos no pueden solaparse; fechas canónicas por etiqueta y año aleatorio único.
    today = date(year, 2, 2)

    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(coordinator_email, "Coordinador sintético C03")
    with connect_local() as conn:
        first_period = conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (period_one, period_one, date(year, 1, 1), date(year, 4, 30)),
        ).fetchone()[0]
        second_period = conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (period_two, period_two, date(year, 5, 1), date(year, 8, 31)),
        ).fetchone()[0]

        earlier_label = f"Septiembre-Diciembre {year - 1}"
        earlier_period = conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre,periodo_label,fecha_inicio,fecha_fin) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (earlier_label, earlier_label, date(year - 1, 9, 1), date(year - 1, 12, 31)),
        ).fetchone()[0]

    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
        def login(email, secret):
            data = expect(client.post("/auth/login", json={"email": email, "password": secret}), 200)
            return {"Authorization": "Bearer " + data["access_token"]}

        coordinator_temp = login(coordinator_email, password)
        expect(
            client.post(
                "/auth/cambiar-password",
                headers=coordinator_temp,
                json={"password_actual": password, "password_nueva": changed},
            ),
            200,
        )
        coordinator = login(coordinator_email, changed)
        created_tutor = expect(
            client.post(
                "/auth/tutores",
                headers=coordinator,
                json={"nombre": "Tutor sintético C03", "email": tutor_email},
            ),
            201,
        )
        tutor_temp = login(tutor_email, created_tutor["password_temporal"])
        expect(
            client.post(
                "/auth/cambiar-password",
                headers=tutor_temp,
                json={
                    "password_actual": created_tutor["password_temporal"],
                    "password_nueva": changed,
                },
            ),
            200,
        )
        tutor = login(tutor_email, changed)

        careers = expect(client.get("/dual/carrera/carreras", headers=tutor), 200)
        assert [(item["codigo"], item["nombre"]) for item in careers] == [
            ("LOG", "ING. NME LOGISTICA"),
            ("MER", "LIC. NME MERCADOTECNIA"),
            ("TII", "ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL"),
        ]
        invalid_group = {
            "carrera": "LIC. NME EDUCACIÓN", "cuatrimestre": 1,
            "modalidad": "intensivo", "letra": "A", "turno": "Matutino",
            "plan": plan, "zona": zone,
        }
        expect(client.post("/dual/carrera/grupos", headers=tutor, json=invalid_group), 422)

        source_body = {
            "carrera": "TII", "cuatrimestre": 1, "modalidad": "intensivo",
            "letra": "A", "turno": "Matutino", "plan": plan, "zona": zone,
        }
        expect(client.post("/dual/carrera/grupos", headers=coordinator, json=source_body), 403)
        source = expect(client.post("/dual/carrera/grupos", headers=tutor, json=source_body), 201)
        target = expect(
            client.post(
                "/dual/carrera/grupos",
                headers=tutor,
                json={**source_body, "carrera": "MER", "cuatrimestre": 2, "letra": "B"},
            ),
            201,
        )
        assert source["nomenclatura"] == f"{plan}TII-{zone}-I-1A"
        assert target["nomenclatura"] == f"{plan}MER-{zone}-I-2B"

        csv_bytes = f"matricula,nombre\n{matricula},Alumno sintético C03\n".encode()
        upload = {"file": ("alumnos.csv", csv_bytes, "text/csv")}
        preview = expect(
            client.post(
                f"/dual/carrera/grupos/{source['id']}/alumnos/preview",
                headers=tutor, data={"periodo_id": str(first_period)}, files=upload,
            ),
            200,
        )
        assert preview["puede_aplicar"] and len(preview["validos"]) == 1
        applied = expect(
            client.post(
                f"/dual/carrera/grupos/{source['id']}/alumnos",
                headers=tutor, data={"periodo_id": str(first_period)}, files=upload,
            ),
            200,
        )
        assert len(applied["insertados"]) == 1
        repeated = expect(
            client.post(
                f"/dual/carrera/grupos/{source['id']}/alumnos",
                headers=tutor, data={"periodo_id": str(first_period)}, files=upload,
            ),
            200,
        )
        assert len(repeated["repetidos"]) == 1

        conflict_upload = {
            "file": ("conflicto.csv", f"matricula,nombre\n{matricula},Nombre incompatible\n".encode(), "text/csv")
        }
        conflict = expect(
            client.post(
                f"/dual/carrera/grupos/{target['id']}/alumnos/preview",
                headers=tutor, data={"periodo_id": str(second_period)}, files=conflict_upload,
            ),
            200,
        )
        assert not conflict["puede_aplicar"] and len(conflict["errores"]) == 1
        expect(
            client.post(
                f"/dual/carrera/grupos/{target['id']}/alumnos",
                headers=tutor, data={"periodo_id": str(second_period)}, files=conflict_upload,
            ),
            409,
        )

        promotion = {
            "grupo_origen_id": source["id"], "periodo_origen_id": str(first_period),
            "grupo_destino_id": target["id"], "periodo_destino_id": str(second_period),
        }
        promotion_preview = expect(
            client.post("/dual/carrera/grupos/promociones/preview", headers=tutor, json=promotion), 200
        )
        assert promotion_preview["puede_aplicar"] and len(promotion_preview["validos"]) == 1
        expect(client.post("/dual/carrera/grupos/promociones", headers=tutor, json=promotion), 200)
        history = expect(
            client.get(f"/dual/carrera/alumnos/{matricula}/grupos", headers=tutor), 200
        )
        assert len(history) == 2
        assert {item["nomenclatura"] for item in history} == {
            source["nomenclatura"], target["nomenclatura"]
        }

        # H1: registrar un período anterior no debe cambiar el grupo vigente.
        with connect_local() as conn:
            current = conn.execute("SELECT grupo_id FROM alumnos WHERE matricula=%s", (matricula,)).fetchone()[0]
        assert str(current) == target["id"], "El grupo vigente debe ser el del período más reciente"
        expect(
            client.post(
                f"/dual/carrera/grupos/{source['id']}/alumnos",
                headers=tutor, data={"periodo_id": str(earlier_period)}, files=upload,
            ),
            200,
        )
        with connect_local() as conn:
            current = conn.execute("SELECT grupo_id FROM alumnos WHERE matricula=%s", (matricula,)).fetchone()[0]
        assert str(current) == target["id"], "Un período anterior no debe retroceder el grupo vigente"
        assert len(expect(
            client.get(f"/dual/carrera/alumnos/{matricula}/grupos", headers=tutor), 200
        )) == 3

        student_password = "C03s" + secrets.token_urlsafe(18)
        expect(
            client.post(
                "/auth/register",
                json={"email": f"{matricula}@ute.edu.mx", "password": student_password},
            ),
            201,
        )
        student = login(f"{matricula}@ute.edu.mx", student_password)
        expect(client.get("/dual/carrera/grupos", headers=student), 403)
        expect(client.get(f"/dual/tutor/alumnos/{matricula}", headers=student), 403)

        first_company = expect(
            client.post(
                "/dual/tutor/empresas", headers=tutor,
                json={"nombre": f"Empresa C03 A {suffix}"},
            ),
            201,
        )
        second_company = expect(
            client.post(
                "/dual/tutor/empresas", headers=tutor,
                json={"nombre": f"Empresa C03 B {suffix}"},
            ),
            201,
        )
        expect(
            client.patch(
                f"/dual/tutor/alumnos/{matricula}", headers=tutor,
                json={"alumno_dual": True, "empresa_id": first_company["id"],
                      "fecha_inicio": today.isoformat()},
            ),
            200,
        )
        expect(
            client.patch(
                f"/dual/tutor/alumnos/{matricula}", headers=tutor,
                json={"alumno_dual": True, "empresa_id": second_company["id"],
                      "fecha_inicio": today.isoformat()},
            ),
            409,
        )
        expect(
            client.patch(
                f"/dual/tutor/alumnos/{matricula}", headers=tutor,
                json={"alumno_dual": False, "fecha_baja": today.isoformat()},
            ),
            200,
        )
        expect(
            client.patch(
                f"/dual/tutor/alumnos/{matricula}", headers=tutor,
                json={"alumno_dual": True, "empresa_id": second_company["id"],
                      "fecha_inicio": (today + timedelta(days=1)).isoformat()},
            ),
            200,
        )
        incorporation_history = expect(
            client.get(f"/dual/tutor/alumnos/{matricula}/incorporaciones", headers=tutor), 200
        )
        assert len(incorporation_history) == 2
        assert sum(1 for item in incorporation_history if item["activo"]) == 1
        # M1: la incorporación se asigna a períodos por fechas, no por el texto cuatrimestre.
        first_rows = expect(
            client.get("/dual/tutor/asignaciones", headers=tutor, params={"cuatrimestre": period_one}), 200)
        mine = [r for r in first_rows if r["matricula"] == matricula]
        assert len(mine) == 2 and {r["cuatrimestre"] for r in mine} == {period_one}
        second_rows = expect(
            client.get("/dual/tutor/asignaciones", headers=tutor, params={"cuatrimestre": period_two}), 200)
        mine = [r for r in second_rows if r["matricula"] == matricula]
        assert len(mine) == 1 and mine[0]["activo"] and mine[0]["empresa_id"] == second_company["id"]
        # Los pendientes por obligación semanal se verifican en smoke_c04.py (C04).
        listing = expect(client.get("/dual/carrera/alumnos", headers=tutor), 200)
        assert sum(1 for r in listing if r["matricula"] == matricula) == 1, "Una fila por alumno"
        expect(client.get("/auth/me", headers=student), 200)

    with connect_local() as conn:
        assert conn.execute("SELECT count(*) FROM carreras WHERE activo").fetchone()[0] == 3
        assert conn.execute(
            "SELECT count(*) FROM alumno_grupo_periodo WHERE matricula=%s", (matricula,)
        ).fetchone()[0] == 3
        # H2: la empresa de la bandeja de reportes es la incorporación vigente.
        from app.infrastructure.database.queries.dual_coordinador_dual import QUERIES
        conn.execute(
            "INSERT INTO reportes_dual (matricula,cuatrimestre,semana,calificacion_alumno) "
            "VALUES (%s,%s,1,8)", (matricula, period_two),
        )
        report_sql = QUERIES["dual.coordinador_dual.q000"]["sql"].replace(
            "{where}", "WHERE r.matricula = %s")
        company = conn.execute(report_sql, (matricula,)).fetchone()
        company_name = dict(zip([d.name for d in conn.execute(report_sql, (matricula,)).description],
                                company))["empresa"]
        assert company_name == f"Empresa C03 B {suffix}", "Debe mostrar la incorporación vigente"
        assert conn.execute(
            "SELECT count(*) FROM alumnos_dual WHERE matricula=%s", (matricula,)
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT count(*) FROM alumnos_dual WHERE matricula=%s AND activo", (matricula,)
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM alumnos_dual WHERE matricula=%s AND cuatrimestre IS NOT NULL", (matricula,)
        ).fetchone()[0] == 0, "La incorporación no debe guardar el grado como cuatrimestre"
        assert conn.execute(
            "SELECT activo FROM usuarios WHERE matricula=%s", (matricula,)
        ).fetchone() == (True,)

    print(
        "PASS C03: catálogo cerrado, nomenclatura, permisos, preview/aplicación CSV, "
        "conflicto atómico, promoción e historias de grupo/incorporación. HTTP y PostgreSQL REALES."
    )
    print("Datos sintéticos conservados. Integraciones externas y móvil físico: NO_VERIFICADAS.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f"FAIL C03: {exc}", file=sys.stderr)
        raise SystemExit(1)
