"""Smoke C10A: almacenamiento privado con Drive (o el adaptador local de regresión), HTTP y PostgreSQL reales.

Parte A (siempre): `/health` informa el estado del almacenamiento sin secretos y, si el almacenamiento no está
disponible, una publicación de plantilla falla con 503 sin dejar filas ni archivos. Parte B (solo con Drive
autorizado, `ALMACENAMIENTO=drive`): guardar, leer con verificación de hash, listar y eliminar de forma
definitiva contra la cuenta de pruebas real, sin dejar nada en la papelera ni en disco. Sin credenciales la
parte B queda NO_VERIFICADA y el script lo dice. Datos sintéticos; no se imprimen credenciales.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import secrets
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx

from app.infrastructure.config.settings import settings
from app.infrastructure.storage.base import ArchivoNoEncontrado, ArchivoYaExiste
from app.infrastructure.storage.registro import get_storage
from local_admin import connect_local, create_coordinator
from smoke_c05 import BASE, expect, pdf

TIPO = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def docx(marca: str) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", f'<Types><Override PartName="/word/document.xml" ContentType="{TIPO}"/></Types>')
        z.writestr("word/document.xml", f"<w:document>{marca}</w:document>")
    return memoria.getvalue()


def main():
    suffix = secrets.token_hex(5)
    password = "C10a" + secrets.token_urlsafe(18)
    email = f"c10a.{suffix}@ute.edu.mx"
    os.environ["LOCAL_ADMIN_PASSWORD"] = password
    create_coordinator(email, "Coordinador sintético C10A")
    with connect_local() as conn:
        conn.execute("UPDATE usuarios SET must_change_password=FALSE WHERE email=%s", (email,))
        conn.commit()

    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        # ---------- Parte A: salud sin secretos y falla cerrada ----------
        salud = expect(client.get("/health"), 200)
        texto = str(salud).lower()
        assert salud["almacenamiento"]["estado"] and salud["almacenamiento"]["tipo"] == settings.almacenamiento
        for prohibido in ("token", "secret", "client", "refresh", "carpeta_id", "drive_config", "key"):
            assert prohibido not in texto, f"/health expone '{prohibido}'"
        assert set(salud["almacenamiento"]) == {"tipo", "estado"}, salud

        data = expect(client.post("/auth/login", json={"email": email, "password": password}), 200)
        cabeceras = {"Authorization": "Bearer " + data["access_token"]}
        with connect_local() as conn:
            filas_antes = conn.execute("SELECT count(*) FROM plantillas_version").fetchone()[0]
        r = client.post("/dual/plantillas/", headers=cabeceras, files={
            "word": ("a.docx", docx(suffix), "application/octet-stream"), "pdf": ("a.pdf", pdf("c10a"), "application/pdf")})
        if salud["almacenamiento"]["estado"] == "ok":
            assert r.status_code == 201, r.text[:200]
            print("Almacenamiento disponible: la publicación de la plantilla se guardó.")
        else:
            assert r.status_code == 503 and "no está disponible" in r.text, (r.status_code, r.text[:200])
            with connect_local() as conn:
                assert conn.execute("SELECT count(*) FROM plantillas_version").fetchone()[0] == filas_antes, "Sin filas a medias"
            assert not re.search(r"(?i)token|secret|drive\.google|googleapis", r.text), "El error no expone detalles internos"
            print(f"Almacenamiento {salud['almacenamiento']['estado']}: falla cerrada con 503, sin filas ni archivos.")

    # ---------- Parte B: Drive real (solo con la cuenta de pruebas autorizada) ----------
    almacen = get_storage()
    if almacen.nombre != "drive" or almacen.estado()["estado"] != "ok":
        print("Parte B (Drive real): NO_VERIFICADA (Drive no está autorizado en este entorno).")
        print("Smoke C10A OK (parte A)")
        return
    clave = secrets.token_hex(16) + ".pdf"
    contenido = pdf("prueba drive " + suffix, 2)
    otro = pdf("otro " + suffix)
    temporales_antes = len(list(Path(tempfile.gettempdir()).glob("*.pdf")))
    try:
        guardado = almacen.guardar("documentos", clave, contenido)
        assert guardado == {"tamano": len(contenido), "sha256": hashlib.sha256(contenido).hexdigest()}
        assert almacen.existe("documentos", clave) and not almacen.existe("plantillas", clave)
        assert almacen.leer("documentos", clave) == contenido, "Lectura byte a byte"
        assert almacen.guardar("documentos", clave, contenido)["tamano"] == len(contenido), "Reintento idempotente"
        try:
            almacen.guardar("documentos", clave, otro)
            raise AssertionError("Las claves son de solo escritura")
        except ArchivoYaExiste:
            pass
        assert clave in {f["clave"] for f in almacen.listar("documentos")}
        # Verificación de hash en la lectura de la aplicación (502 si no coincide).
        import asyncio
        from app.application.errors import ApplicationError
        from app.infrastructure.documents import dual_reports
        assert asyncio.run(dual_reports.leer_documento(clave, guardado["sha256"])) == contenido
        try:
            asyncio.run(dual_reports.leer_documento(clave, "0" * 64))
            raise AssertionError("Un contenido con otra huella no debe entregarse")
        except ApplicationError as error:
            assert error.status_code == 502
        # Archivo grande (reanudable): más de 5 MB.
        grande_clave = secrets.token_hex(16) + ".pdf"
        grande = b"%PDF-1.4\n" + secrets.token_bytes(6 * 1024 * 1024)
        try:
            almacen.guardar("documentos", grande_clave, grande)
            assert almacen.leer("documentos", grande_clave) == grande, "Subida reanudable íntegra"
        finally:
            almacen.eliminar("documentos", grande_clave)
    finally:
        eliminado = almacen.eliminar("documentos", clave)
    assert eliminado and not almacen.existe("documentos", clave)
    assert almacen.eliminar("documentos", clave) is False, "Eliminar es idempotente"
    try:
        almacen.leer("documentos", clave)
        raise AssertionError("El archivo eliminado no debe leerse")
    except ArchivoNoEncontrado:
        pass
    # Eliminación definitiva: tampoco queda en la papelera.
    servicio = almacen._servicio()
    papelera = servicio.files().list(q=f"name = '{clave}' and trashed = true", fields="files(id)").execute()["files"]
    assert papelera == [], "No debe quedar en la papelera"
    assert len(list(Path(tempfile.gettempdir()).glob("*.pdf"))) == temporales_antes, "Sin temporales persistentes"
    print("Parte B (Drive real) REAL: guardar, leer con hash, reintento, clave de solo escritura, listado, archivo grande, "
          "eliminación definitiva sin papelera y sin temporales.")
    print("Smoke C10A OK")


if __name__ == "__main__":
    main()
