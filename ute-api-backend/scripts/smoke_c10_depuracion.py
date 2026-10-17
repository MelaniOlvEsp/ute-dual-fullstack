"""C10: ejecuta una depuración vencida del último período que tuvo una purga programada (y cancelada) por `smoke_c10.py`.

Sirve para la prueba de recuperación: respaldo previo a la depuración → esta depuración → respaldo posterior →
restauración del respaldo previo con el registro del posterior. Igual que C08B, el reloj se simula con SQL (la
gracia real es de 7 días) y la ejecución es la real de la API, que elimina los archivos del almacenamiento.
Datos sintéticos; no imprime credenciales ni claves de archivo.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from psycopg.types.json import Jsonb

from app.infrastructure.security.jwt_passwords import hash_password
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, almacen, existe_doc, expect


def main():
    sufijo, clave = secrets.token_hex(4), "C10d" + secrets.token_urlsafe(18)
    correo_coord, correo_tutor = f"cd10.{sufijo}@ute.edu.mx", f"td10.{sufijo}@ute.edu.mx"
    os.environ["LOCAL_ADMIN_PASSWORD"] = clave
    create_coordinator(correo_coord, "Coordinador sintético C10 depuración")
    with connect_local() as conn:
        periodo_id, carrera = conn.execute(
            "SELECT periodo_id, carrera FROM purgas_archivo WHERE estado='cancelada' AND alcance='carrera' "
            "ORDER BY solicitada_en DESC LIMIT 1").fetchone()
        etiqueta = conn.execute("SELECT periodo_label FROM ciclos_dual WHERE id=%s", (periodo_id,)).fetchone()[0]
        conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (correo_coord,))
        conn.execute("INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                     (correo_tutor, "Tutor sintético C10 depuración", hash_password(clave), Jsonb({"tutor_academico": True})))
        conn.commit()
    pid = str(periodo_id)
    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as c:
        def login(correo):
            return {"Authorization": "Bearer " + expect(c.post("/auth/login", json={"email": correo, "password": clave}), 200)["access_token"]}

        coord, tutor = login(correo_coord), login(correo_tutor)
        ruta = f"/dual/carrera/periodos/{pid}/purgas"
        purga = expect(c.post(ruta, headers=coord, json={"carrera": carrera, "confirmar": True,
                                                         "frase": f"DEPURAR {etiqueta} {carrera}"}), 200)["purga"]["id"]
        with connect_local() as conn:
            conn.execute("ALTER TABLE purgas_archivo DISABLE TRIGGER purgas_protegidas")
            try:
                conn.execute("UPDATE purgas_archivo SET solicitada_en = now() - interval '8 days', "
                             "ejecutar_en = now() - interval '1 minute' WHERE id=%s", (purga,))
            finally:
                conn.execute("ALTER TABLE purgas_archivo ENABLE TRIGGER purgas_protegidas")
            conn.commit()
        resultado = expect(c.post(f"{ruta}/{purga}/ejecucion", headers=tutor), 200)
        with connect_local() as conn:
            estado, archivos = conn.execute("SELECT estado, archivos FROM purgas_archivo WHERE id=%s", (purga,)).fetchone()
            archivados = [f[0] for f in conn.execute("SELECT clave FROM documentos WHERE purga_id=%s", (purga,)).fetchall()]
        assert estado == "completada" and archivos > 0 and len(archivados) == archivos, (estado, archivos, len(archivados))
        assert not any(existe_doc(k) for k in archivados), "Los archivos depurados ya no están en el almacenamiento"
    print(f"Depuración vencida ejecutada ({archivos} archivos eliminados de {almacen().nombre}); resultado:", resultado.get("repetido"))


if __name__ == "__main__":
    main()
