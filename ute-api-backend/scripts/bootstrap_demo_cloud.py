"""Crea coordinador y fixtures sintéticos en una BD remota nueva de la demo.

Es deliberadamente distinto de local_admin.py: exige confirmar el hostname exacto,
un destino Supabase y una base sin cuentas ni datos académicos. No migra ni limpia.
"""
import argparse
import getpass
import sys

import psycopg
from psycopg.types.json import Jsonb

from app.domain.passwords import validate_password
from app.infrastructure.security.jwt_passwords import hash_password


def password_input(label: str) -> str:
    value = getpass.getpass(label)
    validate_password(value)
    if len(value.encode("utf-8")) > 72:
        raise ValueError("La contraseña excede el límite de bcrypt (72 bytes).")
    return value


def seed_demo(conn, hashed: str) -> None:
    from psycopg import sql

    for table in ("grupos", "alumnos", "alumnos_dual", "empresas"):
        existe = conn.execute(
            sql.SQL("SELECT EXISTS (SELECT 1 FROM {})").format(sql.Identifier(table))
        ).fetchone()[0]
        if existe:
            raise ValueError("Los fixtures requieren tablas académicas vacías; no se modificó nada.")

    conn.execute(
        "INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
        ("tutor.c01@ute.edu.mx", "Tutor sintético C01", hashed, Jsonb({"tutor_academico": True})),
    )
    company = conn.execute(
        "INSERT INTO empresas (nombre) VALUES ('Empresa sintética C01') RETURNING id"
    ).fetchone()[0]
    for index, period in enumerate(("Mayo-Agosto 2026", "Septiembre-Diciembre 2026"), start=1):
        group = conn.execute(
            "INSERT INTO grupos (plan,carrera,carrera_id,zona,modalidad,cuatrimestre,letra,turno,ciclo_ingreso) "
            "VALUES ('26','ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',"
            "(SELECT id FROM carreras WHERE codigo='TII'),1,'intensivo',%s,%s,'Matutino','2026') RETURNING id",
            (index, chr(64 + index)),
        ).fetchone()[0]
        matricula = f"99000000{index}"
        conn.execute(
            "INSERT INTO alumnos (matricula,nombre,email,grupo_id,registro_dual_autorizado) "
            "VALUES (%s,%s,%s,%s,TRUE)",
            (matricula, f"Alumno sintético C01 {index}", f"{matricula}@ute.edu.mx", group),
        )
        conn.execute(
            "INSERT INTO usuarios (email,password_hash,roles,matricula) VALUES (%s,%s,%s,%s)",
            (f"{matricula}@ute.edu.mx", hashed, Jsonb({"alumno": True}), matricula),
        )
        conn.execute(
            "INSERT INTO ciclos_dual (cuatrimestre) VALUES (%s) ON CONFLICT DO NOTHING", (period,)
        )
        conn.execute(
            "INSERT INTO alumnos_dual (matricula,cuatrimestre,empresa_id,fecha_inicio) "
            "VALUES (%s,%s,%s,CURRENT_DATE)",
            (matricula, period, company),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Hostname PostgreSQL del proyecto Supabase")
    parser.add_argument("--database", default="postgres")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--confirm-target", required=True, choices=["SUPABASE-DEMO"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--seed-demo", action="store_true", help="Crea tutor y dos alumnos sintéticos")
    args = parser.parse_args()

    try:
        if not args.host.endswith(("supabase.co", "pooler.supabase.com")):
            raise ValueError("El hostname no parece pertenecer a Supabase; se canceló sin conectar.")
        if args.database != "postgres":
            raise ValueError("Para esta herramienta, la base debe llamarse postgres.")
        if not args.email.lower().endswith("@ute.edu.mx") or len(args.email.split("@")) != 2:
            raise ValueError("El coordinador debe usar un correo @ute.edu.mx.")
        if not args.name.strip():
            raise ValueError("El nombre del coordinador es obligatorio.")
        if input(f"Escribe exactamente el hostname de destino ({args.host}) para continuar: ").strip() != args.host:
            raise ValueError("El hostname no coincidió; se canceló sin conectar.")

        db_password = getpass.getpass("Contraseña de PostgreSQL de Supabase (no se mostrará): ")
        coordinator_password = password_input("Contraseña provisional del coordinador (no se mostrará): ")
        demo_password = password_input("Contraseña común de las cuentas sintéticas (no se mostrará): ") if args.seed_demo else None
        coordinator_hash = hash_password(coordinator_password)
        demo_hash = hash_password(demo_password) if demo_password else None

        with psycopg.connect(
            host=args.host, port=args.port, dbname=args.database, user=args.user,
            password=db_password, sslmode="require", connect_timeout=10,
        ) as conn:
            with conn.transaction():
                public_tables = conn.execute(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
                ).fetchone()[0]
                if public_tables == 0:
                    raise ValueError("No se encontró el esquema; instala antes el esquema y migraciones 003–010.")
                existing_users = conn.execute("SELECT count(*) FROM usuarios").fetchone()[0]
                if existing_users:
                    raise ValueError("La tabla usuarios no está vacía; se canceló sin insertar nada.")
                conn.execute(
                    "INSERT INTO usuarios (email,nombre,password_hash,roles,must_change_password) "
                    "VALUES (%s,%s,%s,%s,TRUE)",
                    (args.email.strip().lower(), args.name.strip(), coordinator_hash,
                     Jsonb({"coordinador_dual": True})),
                )
                if args.seed_demo:
                    seed_demo(conn, demo_hash)
        print("Coordinador creado; deberá cambiar la contraseña provisional al ingresar.")
        if args.seed_demo:
            print("Cuentas sintéticas creadas: tutor.c01@ute.edu.mx, 990000001@ute.edu.mx, 990000002@ute.edu.mx.")
        return 0
    except (ValueError, psycopg.Error) as exc:
        print(f"No se completó la carga: {exc if isinstance(exc, ValueError) else type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

