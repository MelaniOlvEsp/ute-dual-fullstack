"""Administración explícita de la base local C01; nunca migra una BD existente."""
import argparse
import getpass
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg.types.json import Jsonb
from app.infrastructure.config.settings import settings
from app.infrastructure.security.jwt_passwords import hash_password
from app.domain.passwords import validate_password

ROOT = Path(__file__).resolve().parents[2]


def connect_local():
    db = settings.db
    allowed_hosts = ("localhost", "127.0.0.1", "::1")
    if os.environ.get("C01_LOCAL_COMPOSE") == "true":
        allowed_hosts += ("postgres",)
    if db.host not in allowed_hosts or db.name != "ute_dual_c01":
        raise ValueError("Solo se permite la BD local ute_dual_c01; revisa DB_HOST/DB_NAME")
    return psycopg.connect(db.db_dsn, connect_timeout=10)


def password_input(variable):
    value = os.environ.get(variable) or getpass.getpass("Contraseña (no se mostrará): ")
    validate_password(value)
    if len(value.encode("utf-8")) > 72:
        raise ValueError("bcrypt admite hasta 72 bytes")
    return value


def init_schema():
    with connect_local() as conn:
        # El SQL controla transacción, bloqueo y verificación de base vacía.
        conn.autocommit = True
        conn.execute((ROOT / "database/schema_dual_desde_cero.sql").read_text(encoding="utf-8"))
    print("Esquema C01 instalado en base vacía.")


def create_coordinator(email, name):
    email = email.strip().lower()
    if not email.endswith("@ute.edu.mx") or len(email.split("@")) != 2:
        raise ValueError("Se requiere correo institucional")
    if not name.strip():
        raise ValueError("Nombre obligatorio")
    password = password_input("LOCAL_ADMIN_PASSWORD")
    with connect_local() as conn:
        conn.execute(
            "INSERT INTO usuarios (email,nombre,password_hash,roles,must_change_password) "
            "VALUES (%s,%s,%s,%s,TRUE)",
            (email, name.strip(), hash_password(password), Jsonb({"coordinador_dual": True})),
        )
    print("Coordinador creado; deberá cambiar la contraseña al ingresar.")


def seed_demo():
    password = password_input("C01_FIXTURE_PASSWORD")
    hashed = hash_password(password)
    with connect_local() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(19862)")
        for table in ("grupos", "alumnos", "alumnos_dual", "empresas"):
            from psycopg import sql
            if conn.execute(sql.SQL("SELECT EXISTS (SELECT 1 FROM {})").format(sql.Identifier(table))).fetchone()[0]:
                raise ValueError("Fixtures requieren tablas académicas vacías; no se sobrescribe nada.")
        conn.execute(
            "INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
            ("tutor.c01@ute.edu.mx", "Tutor sintético C01", hashed, Jsonb({"tutor_academico": True})),
        )
        company = conn.execute("INSERT INTO empresas (nombre) VALUES ('Empresa sintética C01') RETURNING id").fetchone()[0]
        for index, period in enumerate(("Mayo-Agosto 2026", "Septiembre-Diciembre 2026"), start=1):
            group = conn.execute(
                "INSERT INTO grupos (plan,carrera,zona,modalidad,cuatrimestre,letra,turno,ciclo_ingreso) "
                "VALUES ('26','ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',1,'intensivo',%s,%s,'Matutino','2026') RETURNING id",
                (index, chr(64 + index)),
            ).fetchone()[0]
            matricula = f"99000000{index}"
            conn.execute(
                "INSERT INTO alumnos (matricula,nombre,email,grupo_id,registro_dual_autorizado) VALUES (%s,%s,%s,%s,TRUE)",
                (matricula, f"Alumno sintético C01 {index}", f"{matricula}@ute.edu.mx", group),
            )
            conn.execute(
                "INSERT INTO usuarios (email,password_hash,roles,matricula) VALUES (%s,%s,%s,%s)",
                (f"{matricula}@ute.edu.mx", hashed, Jsonb({"alumno": True}), matricula),
            )
            conn.execute("INSERT INTO ciclos_dual (cuatrimestre) VALUES (%s) ON CONFLICT DO NOTHING", (period,))
            conn.execute(
                "INSERT INTO alumnos_dual (matricula,cuatrimestre,empresa_id) VALUES (%s,%s,%s)",
                (matricula, period, company),
            )
    print("Fixtures: un tutor y dos alumnos sintéticos en grupos/períodos distintos. Claves no impresas.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init-schema")
    coordinator = sub.add_parser("create-coordinator")
    coordinator.add_argument("--email", required=True)
    coordinator.add_argument("--name", required=True)
    sub.add_parser("seed-demo")
    args = parser.parse_args()
    try:
        if args.action == "init-schema":
            init_schema()
        elif args.action == "seed-demo":
            seed_demo()
        else:
            create_coordinator(args.email, args.name)
    except (ValueError, psycopg.Error) as exc:
        # No imprimir DSN, contraseñas ni valores de filas en errores SQL.
        print(f"No se completó la operación: {exc if isinstance(exc, ValueError) else type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
