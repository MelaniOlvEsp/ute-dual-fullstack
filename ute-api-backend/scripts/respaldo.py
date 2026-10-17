"""Respaldo y restauración del piloto (C10, DP-11).

Un respaldo vive en el espacio `respaldos` de Drive (contrato de almacenamiento de C10A) y consta de: el volcado de
PostgreSQL (`respaldo-<id>.dump`, formato personalizado), una copia de cada documento no archivado (`doc-<clave>`,
sin repetir los que otro respaldo ya guardó, porque los documentos son de solo escritura) y un manifiesto
(`respaldo-<id>.json`) que se escribe al final: sin manifiesto el respaldo no existe. El volcado lo genera
`scripts/respaldo.ps1` dentro del contenedor de PostgreSQL; este script lo sube, copia los documentos y verifica.

Orden (coherencia): primero la base y después los documentos. Como los documentos nunca se sobrescriben y la
depuración solo elimina, la copia de archivos es un superconjunto de lo que la base referencia; los archivos sin
fila son huérfanos inofensivos. Un archivo que la base referencia, no está archivado y falta en el almacenamiento
se informa como error y el respaldo no se da por bueno. El manifiesto no incluye credenciales ni identificadores de Drive.

Subcomandos: crear, listar, verificar, podar, carpeta-restauracion, restaurar-documentos, verificar-restauracion,
descartar-carpeta, probar-fallos. No imprime credenciales; los identificadores solo viajan por archivos temporales.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.infrastructure.storage.base import ArchivoNoEncontrado
from app.infrastructure.storage.registro import get_storage

ESPACIO, DOCUMENTOS = "respaldos", "documentos"
TMP = Path(os.environ.get("RESPALDO_TMP", "/tmp/respaldo"))
TABLAS = ("usuarios", "alumnos", "ciclos_dual", "documentos", "reportes_dual", "reporte_versiones", "revisiones",
          "cierres_alumno_periodo", "paquetes_archivo", "purgas_archivo", "plantillas_version")
PREFIJO_RESTAURACION = "Formación Dual (restauración"
RETENCION_SEMANALES, RETENCION_MENSUALES = 8, 4
ID_RESPALDO = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9]{1,20}$")


def sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def origen():
    """Almacenamiento que guarda los respaldos: el vivo, o la carpeta indicada para una restauración."""
    carpeta = os.environ.get("RESPALDO_ORIGEN_CARPETA", "").strip()
    if not carpeta:
        return get_storage()
    from app.infrastructure.storage import credenciales
    from app.infrastructure.storage.drive import DriveAlmacenamiento
    return DriveAlmacenamiento(credenciales.fabrica_servicio, carpeta)


def conectar():
    from local_admin import connect_local
    return connect_local()


def conteos(conn) -> dict:
    return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLAS}


def huella(conn) -> str:
    """Huella de lo que no puede cambiar al restaurar: notas congeladas, decisiones de revisión y versiones."""
    partes = [
        conn.execute("SELECT matricula, periodo_id, suma, cantidad, promedio FROM cierres_alumno_periodo ORDER BY 1, 2").fetchall(),
        conn.execute("SELECT id, version_id, decision FROM revisiones ORDER BY id").fetchall(),
        conn.execute("SELECT id, reporte_id, numero, documento_id FROM reporte_versiones ORDER BY id").fetchall()]
    return sha256(json.dumps(partes, default=str, sort_keys=True).encode())


def comparar_huella(ahora: str, huellas: list[str]) -> str:
    """Compara la huella restaurada con la del manifiesto (tomada antes y después del volcado).

    En reposo (las dos iguales) debe coincidir. Si algo cambió durante el respaldo, el volcado pudo captar un estado
    intermedio que no es ninguno de los dos extremos: entonces solo se acepta si coincide con uno y, si no, se
    informa «no_concluyente» (no es un error de la restauración).
    """
    if ahora in huellas:
        return "coincide"
    return "distinta" if len(set(huellas)) == 1 else "no_concluyente"


def migraciones() -> dict:
    base = Path(os.environ.get("RESPALDO_MIGRACIONES", "/workspace/database"))
    archivos = [base / "schema_dual_desde_cero.sql"] + sorted((base / "migrations").glob("*.sql"))
    return {a.name: sha256(a.read_bytes()) for a in archivos if a.is_file()}


def ids_de(alm) -> list[str]:
    nombres = [f["clave"] for f in alm.listar(ESPACIO)]
    return sorted((n[len("respaldo-"):-len(".json")] for n in nombres if n.startswith("respaldo-") and n.endswith(".json")),
                  reverse=True)


def leer_manifiesto(alm, id_: str) -> dict:
    return json.loads(alm.leer(ESPACIO, f"respaldo-{id_}.json"))


def verificar_respaldo(alm, id_: str) -> tuple[list[str], dict | None]:
    """Comprueba manifiesto, volcado y cada documento (existencia y SHA-256). Devuelve (problemas, manifiesto)."""
    problemas: list[str] = []
    try:
        manifiesto = leer_manifiesto(alm, id_)
    except ArchivoNoEncontrado:
        return [f"El respaldo {id_} no tiene manifiesto (incompleto)."], None
    except ValueError:
        return [f"El manifiesto del respaldo {id_} está dañado."], None
    v = manifiesto["volcado"]
    try:
        volcado = alm.leer(ESPACIO, v["clave"])
        if len(volcado) != v["tamano"] or sha256(volcado) != v["sha256"]:
            problemas.append("El volcado de la base no coincide con el manifiesto (tamaño o SHA-256).")
        elif not volcado.startswith(b"PGDMP"):
            problemas.append("El volcado no tiene el formato de pg_dump.")
    except ArchivoNoEncontrado:
        problemas.append("Falta el volcado de la base.")
    for d in manifiesto["documentos"]:
        try:
            if sha256(alm.leer(ESPACIO, "doc-" + d["clave"])) != d["sha256"]:
                problemas.append(f"El documento {d['clave'][:8]}… tiene otro SHA-256.")
        except ArchivoNoEncontrado:
            problemas.append(f"Falta el documento {d['clave'][:8]}… en la copia.")
    return problemas, manifiesto


# ---------------------------------------------------------------------------------------------------------
def tomar_instantanea(conn) -> dict:
    return {"conteos": conteos(conn), "huella": huella(conn), "instante": time.time()}


def instantanea(args) -> int:
    """Conteos y huella ANTES del volcado: `respaldo.ps1` la toma antes de `pg_dump` y se la pasa a `crear`."""
    TMP.mkdir(parents=True, exist_ok=True)
    with conectar() as conn:
        (TMP / args.salida).write_text(json.dumps(tomar_instantanea(conn)), encoding="utf-8")
    return 0


def leer_instantanea(ruta: Path) -> dict:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not {"conteos", "huella", "instante"} <= set(datos) or time.time() - datos["instante"] > 3600:
        raise ValueError("La instantánea previa al volcado no es válida o tiene más de una hora.")
    return datos


def crear(args) -> int:
    alm = origen()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    id_ = f"{ts}-{args.etiqueta}"
    if not ID_RESPALDO.fullmatch(id_):
        print("Etiqueta no válida (minúsculas y números).")
        return 1
    volcado = Path(args.volcado).read_bytes()
    if not volcado.startswith(b"PGDMP"):
        print("El archivo no es un volcado de pg_dump en formato personalizado.")
        return 1
    try:   # la instantánea se toma antes del pg_dump; sin ella no se puede garantizar el intervalo del manifiesto
        previa = leer_instantanea(TMP / args.antes)
    except (OSError, ValueError) as error:
        print(f"RESPALDO RECHAZADO: falta la instantánea previa al volcado ({error}).")
        return 1
    antes, huella_antes, inicio = previa["conteos"], previa["huella"], previa["instante"]
    clave_volcado = f"respaldo-{id_}.dump"
    alm.guardar(ESPACIO, clave_volcado, volcado)
    with conectar() as conn:
        despues, huella_despues, instante_despues = conteos(conn), huella(conn), time.time()
        filas = conn.execute("SELECT clave, sha256, tamano, archivado_en IS NOT NULL FROM documentos ORDER BY created_at").fetchall()
    documentos, depuradas, faltantes, alterados, copiados, reutilizados = [], [], [], [], 0, 0
    for clave, sha, tamano, archivado in filas:
        if archivado:
            depuradas.append(clave)
            continue
        destino = "doc-" + clave
        if alm.existe(ESPACIO, destino):
            reutilizados += 1
        else:
            try:
                contenido = alm.leer(DOCUMENTOS, clave)
            except ArchivoNoEncontrado:
                faltantes.append(clave)
                continue
            if sha256(contenido) != sha:
                alterados.append(clave)
                continue
            alm.guardar(ESPACIO, destino, contenido)
            copiados += 1
        documentos.append({"clave": clave, "sha256": sha, "tamano": tamano})
    if (faltantes or alterados) and not args.permitir_inconsistencias:
        alm.eliminar(ESPACIO, clave_volcado)   # sin manifiesto el respaldo no existe: se retira el volcado suelto
        print(f"RESPALDO RECHAZADO: {len(faltantes)} documento(s) referenciado(s) sin archivo en el almacenamiento y "
              f"{len(alterados)} con otro SHA-256. La base y los archivos no son coherentes; nada se dio por respaldado.")
        return 2
    manifiesto = {
        "version": 1, "id": id_, "etiqueta": args.etiqueta, "creado": ts,
        "instantes": {"conteos_antes_del_volcado": inicio, "conteos_despues_del_volcado": instante_despues, "documentos_listos": time.time()},
        "migraciones": migraciones(),
        "conteos": {"antes": antes, "despues": despues}, "huellas": [huella_antes, huella_despues],
        "volcado": {"clave": clave_volcado, "sha256": sha256(volcado), "tamano": len(volcado)},
        "documentos": documentos, "depuraciones": depuradas,
        "inconsistencias": {"faltantes": faltantes, "alterados": alterados},
        "nota": "Orden: base primero y documentos después; sin credenciales ni identificadores de Drive."}
    alm.guardar(ESPACIO, f"respaldo-{id_}.json", json.dumps(manifiesto, ensure_ascii=False, indent=1).encode())
    print(f"Respaldo {id_} creado: volcado {len(volcado)} bytes, {len(documentos)} documento(s) "
          f"({copiados} copiados, {reutilizados} ya guardados), {len(depuradas)} depurado(s) sin copia.")
    return 0


def listar(args) -> int:
    alm = origen()
    for id_ in ids_de(alm):
        m = leer_manifiesto(alm, id_)
        print(f"{id_}  documentos={len(m['documentos'])}  volcado={m['volcado']['tamano']}")
    return 0


def verificar(args) -> int:
    problemas, _ = verificar_respaldo(origen(), args.id)
    for p in problemas:
        print("PROBLEMA:", p)
    print("Respaldo íntegro." if not problemas else f"Respaldo NO íntegro ({len(problemas)} problema(s)).")
    return 0 if not problemas else 2


def plan_de_retencion(ids: list[str]) -> set[str]:
    """Conserva los 8 respaldos más recientes y el más antiguo de cada uno de los 4 meses más recientes."""
    conservar = set(sorted(ids, reverse=True)[:RETENCION_SEMANALES])
    por_mes: dict[str, str] = {}
    for id_ in sorted(ids):
        por_mes.setdefault(id_[:6], id_)
    for mes in sorted(por_mes, reverse=True)[:RETENCION_MENSUALES]:
        conservar.add(por_mes[mes])
    return conservar


def podar(args) -> int:
    alm = origen()
    ids = ids_de(alm)
    conservar = plan_de_retencion(ids)
    eliminar = [i for i in ids if i not in conservar]
    referenciados = {d["clave"] for i in conservar for d in leer_manifiesto(alm, i)["documentos"]}
    huerfanos = [f["clave"] for f in alm.listar(ESPACIO) if f["clave"].startswith("doc-") and f["clave"][4:] not in referenciados]
    print(f"Respaldos: {len(ids)}; se conservan {len(conservar)}, se eliminarían {len(eliminar)} y {len(huerfanos)} copia(s) de documento sin uso.")
    if not args.aplicar:
        print("Simulación: nada se eliminó (use --aplicar).")
        return 0
    for i in eliminar:
        m = leer_manifiesto(alm, i)
        alm.eliminar(ESPACIO, f"respaldo-{i}.json")   # primero el manifiesto: sin él el respaldo deja de existir
        alm.eliminar(ESPACIO, m["volcado"]["clave"])
    for clave in huerfanos:
        alm.eliminar(ESPACIO, clave)
    print("Poda aplicada.")
    return 0


# ---------------------------------------------------------------------------------------------------------
def carpeta_restauracion(args) -> int:
    from app.infrastructure.storage import credenciales
    nombre = f"{PREFIJO_RESTAURACION} {datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')})"
    carpeta = credenciales.fabrica_servicio().files().create(
        body={"name": nombre, "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "destino.id").write_text(carpeta["id"], encoding="utf-8")
    print(f"Carpeta de destino creada: «{nombre}». Su identificador queda solo en un archivo temporal.")
    return 0


def descartar_carpeta(args) -> int:
    from app.infrastructure.storage import credenciales
    destino = (TMP / "destino.id").read_text(encoding="utf-8").strip()
    drive = credenciales.fabrica_servicio()
    nombre = drive.files().get(fileId=destino, fields="name").execute()["name"]
    if not nombre.startswith(PREFIJO_RESTAURACION) or destino == os.environ.get("RESPALDO_ORIGEN_CARPETA", "").strip():
        print("Se niega a eliminar: la carpeta no es una carpeta de restauración creada por este procedimiento.")
        return 1
    drive.files().delete(fileId=destino).execute()
    (TMP / "destino.id").unlink(missing_ok=True)
    print(f"Carpeta de restauración «{nombre}» eliminada de forma definitiva.")
    return 0


def restaurar_documentos(args) -> int:
    """Se ejecuta con la base restaurada y el almacenamiento (DRIVE_CARPETA_ID) del destino aislado."""
    alm, destino = origen(), get_storage()
    if os.environ.get("RESPALDO_ORIGEN_CARPETA", "").strip() == os.environ.get("DRIVE_CARPETA_ID", "").strip():
        print("Se niega a restaurar sobre la misma carpeta que contiene los respaldos.")
        return 1
    problemas, manifiesto = verificar_respaldo(alm, args.id)
    if problemas:
        for p in problemas:
            print("PROBLEMA:", p)
        print("RESTAURACIÓN RECHAZADA: el respaldo no está íntegro.")
        return 2
    # Registro de depuraciones: el del respaldo más reciente (o el indicado) para que lo eliminado a propósito no reaparezca.
    registro_id = args.registro or ids_de(alm)[0]
    depuradas = set(leer_manifiesto(alm, registro_id)["depuraciones"]) | set(manifiesto["depuraciones"])
    en_manifiesto = {d["clave"] for d in manifiesto["documentos"]}
    with conectar() as conn:
        filas = conn.execute("SELECT clave, sha256, archivado_en IS NOT NULL FROM documentos").fetchall()
    copiados = omitidos = 0
    for clave, sha, archivado in filas:
        if archivado or clave in depuradas:
            omitidos += 1
            continue
        if clave not in en_manifiesto:
            print(f"PROBLEMA: la base restaurada referencia un documento que el respaldo no copió ({clave[:8]}…).")
            return 2
        contenido = alm.leer(ESPACIO, "doc-" + clave)
        destino.guardar(DOCUMENTOS, clave, contenido)
        copiados += 1
    for clave in depuradas:       # lo depurado se elimina de nuevo si reapareciera
        destino.eliminar(DOCUMENTOS, clave)
    print(f"Documentos restaurados: {copiados}; omitidos por archivados o depurados: {omitidos}.")
    return 0


def verificar_restauracion(args) -> int:
    import httpx
    from psycopg.types.json import Jsonb
    from app.infrastructure.security.jwt_passwords import hash_password
    alm, destino = origen(), get_storage()
    manifiesto = leer_manifiesto(alm, args.id)
    registro_id = args.registro or ids_de(alm)[0]
    depuradas = set(leer_manifiesto(alm, registro_id)["depuraciones"]) | set(manifiesto["depuraciones"])
    errores: list[str] = []
    with conectar() as conn:
        actuales, ahora = conteos(conn), huella(conn)
        for tabla, n in actuales.items():
            if not manifiesto["conteos"]["antes"][tabla] <= n <= manifiesto["conteos"]["despues"][tabla]:
                errores.append(f"Conteo de {tabla}: {n} fuera de [{manifiesto['conteos']['antes'][tabla]}, {manifiesto['conteos']['despues'][tabla]}].")
        veredicto = comparar_huella(ahora, manifiesto["huellas"])
        if veredicto == "distinta":
            errores.append("Notas, revisiones o versiones restauradas no coinciden con las del respaldo.")
        elif veredicto == "no_concluyente":
            print("AVISO: notas, revisiones o versiones cambiaron durante el respaldo; la huella no es concluyente "
                  "(los conteos sí se comprobaron). Repite el respaldo en reposo si necesitas la comprobación completa.")
        filas = conn.execute("SELECT clave, sha256, archivado_en IS NOT NULL FROM documentos").fetchall()
        referencias, depurados_despues = 0, 0
        for clave, sha, archivado in filas:
            existe = destino.existe(DOCUMENTOS, clave)
            if archivado or clave in depuradas:
                depurados_despues += not archivado
                if existe:
                    errores.append(f"El documento {clave[:8]}… debería estar eliminado y existe.")
                continue
            referencias += 1
            if not existe:
                errores.append(f"El documento {clave[:8]}… referenciado no existe en la carpeta restaurada.")
            elif sha256(destino.leer(DOCUMENTOS, clave)) != sha:
                errores.append(f"El documento {clave[:8]}… tiene otro SHA-256 tras restaurar.")
        # Descarga de una muestra por la API restaurada (originales y firmados).
        os.environ["LOCAL_ADMIN_PASSWORD"] = clave_tutor = "R" + secrets.token_urlsafe(18)
        correo = f"verificacion.{secrets.token_hex(4)}@ute.edu.mx"
        conn.execute("INSERT INTO usuarios (email,nombre,password_hash,roles) VALUES (%s,%s,%s,%s)",
                     (correo, "Verificación de restauración", hash_password(clave_tutor), Jsonb({"tutor_academico": True})))
        conn.commit()
        muestra = conn.execute(
            "SELECT rd.id, v.numero, d.sha256, ds.sha256, d.clave, ds.clave FROM reportes_dual rd "
            "JOIN reporte_versiones v ON v.reporte_id=rd.id JOIN revisiones rv ON rv.version_id=v.id AND rv.decision='Aprobada' "
            "JOIN documentos d ON d.id=v.documento_id JOIN documentos ds ON ds.id=rv.documento_firmado_id "
            "WHERE d.archivado_en IS NULL AND ds.archivado_en IS NULL ORDER BY d.created_at DESC").fetchall()
    # Lo depurado después del respaldo no tiene archivo (a propósito): no sirve como muestra.
    muestra = [m[:4] for m in muestra if m[4] not in depuradas and m[5] not in depuradas][:3]
    descargas = 0
    with httpx.Client(base_url=args.api, timeout=60, trust_env=False) as c:
        login = c.post("/auth/login", json={"email": correo, "password": clave_tutor})
        if login.status_code != 200:
            errores.append(f"No se pudo iniciar sesión en la API restaurada ({login.status_code}).")
        else:
            cabeceras = {"Authorization": "Bearer " + login.json()["access_token"]}
            for rid, numero, sha_original, sha_firmado in muestra:
                for documento, esperado in (("original", sha_original), ("firmado", sha_firmado)):
                    r = c.get(f"/dual/carrera/reportes/{rid}/versiones/{numero}/pdf", headers=cabeceras, params={"documento": documento})
                    if r.status_code != 200 or sha256(r.content) != esperado:
                        errores.append(f"Descarga {documento} de una muestra: {r.status_code} o SHA-256 distinto.")
                    else:
                        descargas += 1
    for e in errores:
        print("ERROR:", e)
    print(f"Restauración {'VERIFICADA' if not errores else 'CON ERRORES'}: referencias comprobadas {referencias}, "
          f"depurados tras el respaldo {depurados_despues}, descargas de muestra correctas {descargas}.")
    return 0 if not errores else 2


def probar_fallos(args) -> int:
    """AC5: respaldos alterados a propósito (copias del manifiesto) deben detectarse. Se eliminan al terminar."""
    alm = origen()
    base = leer_manifiesto(alm, args.id)
    if not base["documentos"]:
        print("Se necesita un respaldo con al menos un documento.")
        return 1
    creados, resultados = [], {}

    def variante(nombre, cambio, volcado=None):
        id_ = f"{base['creado']}-{nombre}"
        m = json.loads(json.dumps(base))
        m["id"] = id_
        cambio(m)
        if volcado is not None:
            alm.guardar(ESPACIO, f"respaldo-{id_}.dump", volcado)
            m["volcado"] = {"clave": f"respaldo-{id_}.dump", "sha256": sha256(volcado), "tamano": len(volcado)}
        alm.guardar(ESPACIO, f"respaldo-{id_}.json", json.dumps(m).encode())
        creados.append(id_)
        return id_

    try:
        faltante = variante("faltante", lambda m: m["documentos"].append({"clave": "inexistente-" + secrets.token_hex(6) + ".pdf", "sha256": "0" * 64, "tamano": 1}))
        distinto = variante("hash", lambda m: m["documentos"][0].update(sha256="f" * 64))
        danado = variante("danado", lambda m: None, volcado=b"PGDMP" + secrets.token_bytes(64))
        alterado = variante("alterado", lambda m: m["volcado"].update(sha256="e" * 64))
        sin_manifiesto_id = f"{base['creado']}-sinmanifiesto"
        for nombre, id_ in (("documento faltante", faltante), ("SHA-256 distinto", distinto), ("volcado alterado", alterado),
                            ("sin manifiesto", sin_manifiesto_id)):
            problemas, _ = verificar_respaldo(alm, id_)
            resultados[nombre] = bool(problemas)
        print("DANADO_ID", danado)
    finally:
        for id_ in creados:
            if id_ != danado:
                for clave in (f"respaldo-{id_}.json", f"respaldo-{id_}.dump"):
                    alm.eliminar(ESPACIO, clave)
        # el variante «dañado» queda para que respaldo.ps1 pruebe pg_restore --list; lo retira el procedimiento
    for nombre, detectado in resultados.items():
        print(f"  {nombre}: {'detectado' if detectado else 'NO DETECTADO'}")
    return 0 if all(resultados.values()) else 2


def quitar_prueba(args) -> int:
    alm = origen()
    for clave in (f"respaldo-{args.id}.json", f"respaldo-{args.id}.dump"):
        alm.eliminar(ESPACIO, clave)
    return 0


def descargar_volcado(args) -> int:
    alm = origen()
    problemas, manifiesto = verificar_respaldo(alm, args.id) if not args.sin_verificar else ([], leer_manifiesto(alm, args.id))
    if problemas:
        for p in problemas:
            print("PROBLEMA:", p)
        return 2
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "restaurar.dump").write_bytes(alm.leer(ESPACIO, manifiesto["volcado"]["clave"]))
    print(f"Volcado del respaldo {args.id} listo para restaurar.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="orden", required=True)
    s = sub.add_parser("instantanea"); s.add_argument("--salida", default="antes.json"); s.set_defaults(f=instantanea)
    s = sub.add_parser("crear"); s.add_argument("--volcado", required=True); s.add_argument("--etiqueta", default="semanal")
    s.add_argument("--antes", default="antes.json", help="instantánea tomada antes del volcado (en la carpeta temporal)")
    s.add_argument("--permitir-inconsistencias", action="store_true"); s.set_defaults(f=crear)
    sub.add_parser("listar").set_defaults(f=listar)
    s = sub.add_parser("verificar"); s.add_argument("--id", required=True); s.set_defaults(f=verificar)
    s = sub.add_parser("podar"); s.add_argument("--aplicar", action="store_true"); s.set_defaults(f=podar)
    sub.add_parser("carpeta-restauracion").set_defaults(f=carpeta_restauracion)
    sub.add_parser("descartar-carpeta").set_defaults(f=descartar_carpeta)
    s = sub.add_parser("descargar-volcado"); s.add_argument("--id", required=True); s.add_argument("--sin-verificar", action="store_true")
    s.set_defaults(f=descargar_volcado)
    s = sub.add_parser("restaurar-documentos"); s.add_argument("--id", required=True); s.add_argument("--registro"); s.set_defaults(f=restaurar_documentos)
    s = sub.add_parser("verificar-restauracion"); s.add_argument("--id", required=True); s.add_argument("--registro")
    s.add_argument("--api", default="http://api:8000"); s.set_defaults(f=verificar_restauracion)
    s = sub.add_parser("probar-fallos"); s.add_argument("--id", required=True); s.set_defaults(f=probar_fallos)
    s = sub.add_parser("quitar-prueba"); s.add_argument("--id", required=True); s.set_defaults(f=quitar_prueba)
    args = p.parse_args()
    return args.f(args)


if __name__ == "__main__":
    sys.exit(main())
