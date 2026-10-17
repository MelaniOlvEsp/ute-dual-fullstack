"""Respaldo y restauración del piloto (C10, DP-11; cifrado y endurecimiento en C13).

Un respaldo vive en el espacio `respaldos` de Drive (contrato de almacenamiento de C10A) y consta de: el volcado de
PostgreSQL (`respaldo-<id>.dump.age`), una copia de cada documento no archivado (`doc-<clave>.<huella>.age`, sin repetir
los que otro respaldo ya guardó para el mismo destinatario, porque los documentos son de solo escritura) y un manifiesto
(`respaldo-<id>.json`) que se escribe al final: sin manifiesto el respaldo no existe. El volcado lo genera
`scripts/respaldo.ps1` dentro del contenedor de PostgreSQL; este script lo cifra, lo sube, copia los documentos y verifica.

Cifrado (C13, D1): todo se cifra con age (clave pública del destinatario) ANTES de subirse; Drive solo ve texto cifrado.
La máquina que respalda solo conoce la clave pública; la clave privada la guarda el responsable fuera del equipo y solo
se necesita para restaurar. El manifiesto `version: 2` registra el método, la huella del destinatario, la huella del
texto cifrado (que se verifica sin la clave) y la del contenido (que se verifica al descifrar). Los respaldos sin cifrar
(`version: 1`, solo con `--sin-cifrar`, para datos sintéticos) se siguen pudiendo verificar y restaurar.

Orden (coherencia): primero la base y después los documentos. Como los documentos nunca se sobrescriben y la
depuración solo elimina, la copia de archivos es un superconjunto de lo que la base referencia; los archivos sin
fila son huérfanos inofensivos. Un archivo que la base referencia, no está archivado y falta en el almacenamiento
se informa como error y el respaldo no se da por bueno. El manifiesto no incluye credenciales ni identificadores de Drive.

Subcomandos: generar-clave, instantanea, crear, listar, verificar, podar, carpeta-restauracion, descargar-volcado,
restaurar-documentos, verificar-restauracion, descartar-carpeta, probar-fallos, quitar-prueba. Los que escriben en una
base o en una carpeta de Drive de restauración solo corren dentro de `restaurar.ps1` (variable RESPALDO_ENTORNO).
No imprime credenciales ni la clave privada; los identificadores solo viajan por archivos temporales.
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

from app.infrastructure.storage.base import ArchivoNoEncontrado, ArchivoYaExiste
from app.infrastructure.storage.registro import get_storage

ESPACIO, DOCUMENTOS = "respaldos", "documentos"
TMP = Path(os.environ.get("RESPALDO_TMP", "/tmp/respaldo"))
TABLAS = ("usuarios", "alumnos", "ciclos_dual", "documentos", "reportes_dual", "reporte_versiones", "revisiones",
          "cierres_alumno_periodo", "paquetes_archivo", "purgas_archivo", "plantillas_version")
PREFIJO_RESTAURACION = "Formación Dual (restauración"
RETENCION_SEMANALES, RETENCION_MENSUALES = 8, 4
ID_RESPALDO = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9]{1,20}$")
ETIQUETAS_PRUEBA = frozenset({"faltante", "hash", "danado", "alterado", "sinmanifiesto"})   # variantes de `probar-fallos`
CANDADO = "en-curso.lock"
VIGENCIA_CANDADO = 2 * 3600
ENCABEZADO_AGE = b"age-encryption.org/"


class ClaveNoDisponible(Exception):
    """Falta la clave pública (para cifrar) o la clave privada (para descifrar)."""


class ClaveIncorrecta(Exception):
    """La clave privada no corresponde al destinatario con el que se cifró."""


def sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


# --- cifrado (age) -----------------------------------------------------------------------------------------
def destinatario():
    """Clave pública de age: variable RESPALDO_CLAVE_PUBLICA o el archivo `respaldo_clave_publica.txt` de `.secretos`."""
    from pyrage import x25519
    texto = os.environ.get("RESPALDO_CLAVE_PUBLICA", "").strip()
    if not texto:
        archivo = Path(os.environ.get("RESPALDO_CLAVE_PUBLICA_ARCHIVO", "/secretos/respaldo_clave_publica.txt"))
        if archivo.is_file():
            texto = next((l.strip() for l in archivo.read_text(encoding="utf-8").splitlines() if l.strip().startswith("age1")), "")
    if not texto:
        raise ClaveNoDisponible("Falta la clave pública de cifrado (RESPALDO_CLAVE_PUBLICA o .secretos/respaldo_clave_publica.txt).")
    try:
        return x25519.Recipient.from_str(texto)
    except Exception as error:
        raise ClaveNoDisponible("La clave pública de cifrado no es válida.") from error


def identidad():
    """Clave privada de age (solo para restaurar): el archivo temporal que `restaurar.ps1` deja y borra, o RESPALDO_IDENTIDAD_ARCHIVO."""
    from pyrage import x25519
    ruta = Path(os.environ.get("RESPALDO_IDENTIDAD_ARCHIVO", str(TMP / "identidad.txt")))
    if not ruta.is_file():
        raise ClaveNoDisponible("El respaldo está cifrado y no se proporcionó la clave privada (use -Identidad).")
    linea = next((l.strip() for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip().startswith("AGE-SECRET-KEY-")), "")
    try:
        return x25519.Identity.from_str(linea)
    except Exception as error:
        raise ClaveNoDisponible("El archivo de clave privada no tiene una clave de age válida.") from error


def huella_destinatario(r) -> str:
    return sha256(str(r).encode())[:16]


def cifrar(contenido: bytes, r) -> bytes:
    import pyrage
    return pyrage.encrypt(contenido, [r])


def descifrar(cifrado: bytes, i) -> bytes:
    import pyrage
    try:
        return pyrage.decrypt(cifrado, [i])
    except Exception as error:
        raise ClaveIncorrecta("La clave privada no corresponde a este respaldo (o el contenido está alterado).") from error


# --- utilidades --------------------------------------------------------------------------------------------
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


def exigir_entorno_restauracion(orden: str) -> bool:
    """Los subcomandos que escriben (una base, una carpeta de Drive) solo corren dentro de `restaurar.ps1`."""
    if os.environ.get("RESPALDO_ENTORNO", "") != "restauracion":
        print(f"Se niega a ejecutar «{orden}» fuera de un entorno de restauración: escribiría en la base o en la carpeta de este "
              f"entorno. Use scripts/restaurar.ps1.")
        return False
    if os.environ.get("RESPALDO_ORIGEN_CARPETA", "").strip() == os.environ.get("DRIVE_CARPETA_ID", "").strip():
        print(f"Se niega a ejecutar «{orden}»: el destino es la misma carpeta que contiene los respaldos.")
        return False
    return True


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


def es_prueba(id_: str) -> bool:
    return id_.split("-", 1)[-1] in ETIQUETAS_PRUEBA


def ids_de(alm, incluir_pruebas: bool = False) -> list[str]:
    """Respaldos por manifiesto, del más reciente al más antiguo; las variantes de `probar-fallos` no cuentan."""
    nombres = [f["clave"] for f in alm.listar(ESPACIO)]
    ids = (n[len("respaldo-"):-len(".json")] for n in nombres if n.startswith("respaldo-") and n.endswith(".json"))
    return sorted((i for i in ids if incluir_pruebas or not es_prueba(i)), reverse=True)


def leer_manifiesto(alm, id_: str) -> dict:
    return json.loads(alm.leer(ESPACIO, f"respaldo-{id_}.json"))


def cifrado_de(manifiesto: dict) -> bool:
    return manifiesto.get("version", 1) >= 2 and "cifrado" in manifiesto


def copia_de(documento: dict) -> str:
    """Clave de la copia de un documento en el espacio de respaldos (v1: `doc-<clave>`; v2: `doc-<clave>.<huella>.age`)."""
    return documento.get("copia") or "doc-" + documento["clave"]


def verificar_respaldo(alm, id_: str, clave=None) -> tuple[list[str], dict | None]:
    """Comprueba manifiesto, volcado y cada documento. Devuelve (problemas, manifiesto).

    Sin cifrar: existencia y SHA-256. Cifrado: existencia, formato y SHA-256 del texto cifrado, que no necesitan la clave;
    con la clave privada (`clave`) además se descifra y se compara el SHA-256 del contenido.
    """
    problemas: list[str] = []
    try:
        manifiesto = leer_manifiesto(alm, id_)
    except ArchivoNoEncontrado:
        return [f"El respaldo {id_} no tiene manifiesto (incompleto)."], None
    except ValueError:
        return [f"El manifiesto del respaldo {id_} está dañado."], None
    cifrado = cifrado_de(manifiesto)
    v = manifiesto["volcado"]
    try:
        volcado = alm.leer(ESPACIO, v["clave"])
        if len(volcado) != v["tamano"] or sha256(volcado) != v["sha256"]:
            problemas.append("El volcado de la base no coincide con el manifiesto (tamaño o SHA-256).")
        elif cifrado and not volcado.startswith(ENCABEZADO_AGE):
            problemas.append("El volcado no tiene el formato cifrado esperado.")
        elif not cifrado and not volcado.startswith(b"PGDMP"):
            problemas.append("El volcado no tiene el formato de pg_dump.")
        elif cifrado and clave is not None:
            claro = descifrar(volcado, clave)
            if sha256(claro) != v["sha256_claro"] or not claro.startswith(b"PGDMP"):
                problemas.append("El volcado descifrado no coincide con el manifiesto.")
    except ArchivoNoEncontrado:
        problemas.append("Falta el volcado de la base.")
    for d in manifiesto["documentos"]:
        try:
            copia = alm.leer(ESPACIO, copia_de(d))
        except ArchivoNoEncontrado:
            problemas.append(f"Falta el documento {d['clave'][:8]}… en la copia.")
            continue
        if cifrado:
            if sha256(copia) != d["sha256_cifrado"] or not copia.startswith(ENCABEZADO_AGE):
                problemas.append(f"El documento {d['clave'][:8]}… tiene otro SHA-256 (texto cifrado).")
            elif clave is not None and sha256(descifrar(copia, clave)) != d["sha256"]:
                problemas.append(f"El documento {d['clave'][:8]}… descifrado tiene otro SHA-256.")
        elif sha256(copia) != d["sha256"]:
            problemas.append(f"El documento {d['clave'][:8]}… tiene otro SHA-256.")
    return problemas, manifiesto


# --- candado entre respaldo y poda --------------------------------------------------------------------------
def tomar_candado(alm, ahora: float | None = None) -> bool:
    """Marca que hay un respaldo en curso; falso si hay otro vigente. Un candado de más de 2 horas se considera abandonado."""
    ahora = time.time() if ahora is None else ahora
    for _ in range(2):
        try:
            alm.guardar(ESPACIO, CANDADO, json.dumps({"desde": ahora}).encode())
            return True
        except ArchivoYaExiste:
            if candado_vigente(alm, ahora):
                return False
            alm.eliminar(ESPACIO, CANDADO)   # abandonado: se retira y se reintenta
    return False


def candado_vigente(alm, ahora: float | None = None) -> bool:
    ahora = time.time() if ahora is None else ahora
    try:
        desde = json.loads(alm.leer(ESPACIO, CANDADO)).get("desde", 0)
    except (ArchivoNoEncontrado, ValueError):
        return False
    return ahora - desde < VIGENCIA_CANDADO


def soltar_candado(alm) -> None:
    alm.eliminar(ESPACIO, CANDADO)


# ---------------------------------------------------------------------------------------------------------
def generar_clave(args) -> int:
    """Genera el par de claves de age. La privada queda en un archivo temporal que `respaldo.ps1` mueve a la ruta elegida."""
    from pyrage import x25519
    TMP.mkdir(parents=True, exist_ok=True)
    nueva = x25519.Identity.generate()
    publica = str(nueva.to_public())
    (TMP / "identidad-nueva.txt").write_text(
        f"# Clave privada de respaldo (age). Creada {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"# Clave pública: {publica}\n{nueva}\n", encoding="utf-8")
    (TMP / "clave_publica.txt").write_text(publica + "\n", encoding="utf-8")
    print(f"Par de claves generado. Clave pública: {publica}")
    return 0


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
    if not ID_RESPALDO.fullmatch(id_) or args.etiqueta in ETIQUETAS_PRUEBA:
        print("Etiqueta no válida (minúsculas y números; las etiquetas de las pruebas de fallos están reservadas).")
        return 1
    r = None
    if not args.sin_cifrar:
        try:
            r = destinatario()
        except ClaveNoDisponible as error:
            print(f"RESPALDO RECHAZADO: {error} El cifrado es obligatorio; solo con datos sintéticos se puede usar --sin-cifrar.")
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
    if not tomar_candado(alm):
        print("RESPALDO RECHAZADO: hay otro respaldo en curso (candado vigente en el espacio de respaldos).")
        return 1
    try:
        return _crear(args, alm, ts, id_, r, volcado, previa)
    finally:
        soltar_candado(alm)


def _crear(args, alm, ts, id_, r, volcado, previa) -> int:
    antes, huella_antes, inicio = previa["conteos"], previa["huella"], previa["instante"]
    sufijo = ".dump.age" if r else ".dump"
    clave_volcado = f"respaldo-{id_}{sufijo}"
    almacenado = cifrar(volcado, r) if r else volcado
    alm.guardar(ESPACIO, clave_volcado, almacenado)
    with conectar() as conn:
        despues, huella_despues, instante_despues = conteos(conn), huella(conn), time.time()
        filas = conn.execute("SELECT clave, sha256, tamano, archivado_en IS NOT NULL FROM documentos ORDER BY created_at").fetchall()
    documentos, depuradas, faltantes, alterados, copiados, reutilizados = [], [], [], [], 0, 0
    marca = huella_destinatario(r) if r else ""
    for clave, sha, tamano, archivado in filas:
        if archivado:
            depuradas.append(clave)
            continue
        entrada = {"clave": clave, "sha256": sha, "tamano": tamano}
        if r:
            entrada["copia"] = f"doc-{clave}.{marca}.age"
        destino = copia_de(entrada)
        if alm.existe(ESPACIO, destino):
            reutilizados += 1
            if r:   # el cifrado es aleatorio: la huella del texto cifrado solo se conoce leyendo la copia que ya existe
                entrada["sha256_cifrado"] = sha256(alm.leer(ESPACIO, destino))
        else:
            try:
                contenido = alm.leer(DOCUMENTOS, clave)
            except ArchivoNoEncontrado:
                faltantes.append(clave)
                continue
            if sha256(contenido) != sha:
                alterados.append(clave)
                continue
            guardado = cifrar(contenido, r) if r else contenido
            alm.guardar(ESPACIO, destino, guardado)
            if r:
                entrada["sha256_cifrado"] = sha256(guardado)
            copiados += 1
        documentos.append(entrada)
    if (faltantes or alterados) and not args.permitir_inconsistencias:
        alm.eliminar(ESPACIO, clave_volcado)   # sin manifiesto el respaldo no existe: se retira el volcado suelto
        print(f"RESPALDO RECHAZADO: {len(faltantes)} documento(s) referenciado(s) sin archivo en el almacenamiento y "
              f"{len(alterados)} con otro SHA-256. La base y los archivos no son coherentes; nada se dio por respaldado.")
        return 2
    volcado_info = {"clave": clave_volcado, "sha256": sha256(almacenado), "tamano": len(almacenado)}
    if r:
        volcado_info.update(sha256_claro=sha256(volcado), tamano_claro=len(volcado))
    manifiesto = {
        "version": 2 if r else 1, "id": id_, "etiqueta": args.etiqueta, "creado": ts,
        "instantes": {"conteos_antes_del_volcado": inicio, "conteos_despues_del_volcado": instante_despues, "documentos_listos": time.time()},
        "migraciones": migraciones(),
        "conteos": {"antes": antes, "despues": despues}, "huellas": [huella_antes, huella_despues],
        "volcado": volcado_info,
        "documentos": documentos, "depuraciones": depuradas,
        "inconsistencias": {"faltantes": faltantes, "alterados": alterados},
        "nota": "Orden: base primero y documentos después; sin credenciales ni identificadores de Drive."}
    if r:
        manifiesto["cifrado"] = {"metodo": "age", "destinatario": marca}
    alm.guardar(ESPACIO, f"respaldo-{id_}.json", json.dumps(manifiesto, ensure_ascii=False, indent=1).encode())
    print(f"Respaldo {id_} creado ({'cifrado con age' if r else 'SIN CIFRAR'}): volcado {len(volcado)} bytes, "
          f"{len(documentos)} documento(s) ({copiados} copiados, {reutilizados} ya guardados), {len(depuradas)} depurado(s) sin copia.")
    return 0


def listar(args) -> int:
    alm = origen()
    for id_ in ids_de(alm):
        m = leer_manifiesto(alm, id_)
        print(f"{id_}  {'cifrado' if cifrado_de(m) else 'SIN CIFRAR'}  documentos={len(m['documentos'])}  volcado={m['volcado']['tamano']}")
    return 0


def verificar(args) -> int:
    clave = None
    if args.con_clave:
        try:
            clave = identidad()
        except ClaveNoDisponible as error:
            print(f"PROBLEMA: {error}")
            return 3
    try:
        problemas, _ = verificar_respaldo(origen(), args.id, clave)
    except ClaveIncorrecta as error:
        print(f"PROBLEMA: {error}")
        return 3
    for p in problemas:
        print("PROBLEMA:", p)
    modo = "con la clave privada" if clave is not None else "sin la clave (texto cifrado y huellas)"
    print(f"Respaldo íntegro ({modo})." if not problemas else f"Respaldo NO íntegro ({len(problemas)} problema(s)).")
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
    if candado_vigente(alm):
        print("PODA RECHAZADA: hay un respaldo en curso; eliminar copias ahora podría dejarlo incompleto. Repite al terminar.")
        return 1
    ids = ids_de(alm)
    conservar = plan_de_retencion(ids)
    eliminar = [i for i in ids if i not in conservar]
    referenciados = {copia_de(d) for i in conservar for d in leer_manifiesto(alm, i)["documentos"]}
    huerfanos = [f["clave"] for f in alm.listar(ESPACIO) if f["clave"].startswith("doc-") and f["clave"] not in referenciados]
    print(f"Respaldos: {len(ids)}; se conservan {len(conservar)}, se eliminarían {len(eliminar)} y {len(huerfanos)} copia(s) de documento sin uso.")
    if not args.aplicar:
        print("Simulación: nada se eliminó (use --aplicar).")
        return 0
    if not tomar_candado(alm):   # la poda también marca que trabaja, para que no empiece un respaldo a medias
        print("PODA RECHAZADA: hay un respaldo en curso.")
        return 1
    try:
        for i in eliminar:
            m = leer_manifiesto(alm, i)
            alm.eliminar(ESPACIO, f"respaldo-{i}.json")   # primero el manifiesto: sin él el respaldo deja de existir
            alm.eliminar(ESPACIO, m["volcado"]["clave"])
        for clave in huerfanos:
            alm.eliminar(ESPACIO, clave)
    finally:
        soltar_candado(alm)
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
    if not exigir_entorno_restauracion("descartar-carpeta"):
        return 1
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


def _clave_para(manifiesto: dict):
    """La clave privada, solo si el respaldo está cifrado; con mensaje claro si falta o no corresponde."""
    return identidad() if cifrado_de(manifiesto) else None


def restaurar_documentos(args) -> int:
    """Se ejecuta con la base restaurada y el almacenamiento (DRIVE_CARPETA_ID) del destino aislado."""
    if not exigir_entorno_restauracion("restaurar-documentos"):
        return 1
    alm, destino = origen(), get_storage()
    try:
        manifiesto = leer_manifiesto(alm, args.id)
        clave = _clave_para(manifiesto)
        problemas, manifiesto = verificar_respaldo(alm, args.id, clave)
    except ClaveNoDisponible as error:
        print(f"RESTAURACIÓN RECHAZADA: {error}")
        return 3
    except ClaveIncorrecta as error:
        print(f"RESTAURACIÓN RECHAZADA: {error}")
        return 3
    except ArchivoNoEncontrado:
        print(f"RESTAURACIÓN RECHAZADA: el respaldo {args.id} no tiene manifiesto.")
        return 2
    if problemas:
        for p in problemas:
            print("PROBLEMA:", p)
        print("RESTAURACIÓN RECHAZADA: el respaldo no está íntegro.")
        return 2
    # Registro de depuraciones: el del respaldo más reciente (o el indicado) para que lo eliminado a propósito no reaparezca.
    registro_id = args.registro or ids_de(alm)[0]
    depuradas = set(leer_manifiesto(alm, registro_id)["depuraciones"]) | set(manifiesto["depuraciones"])
    en_manifiesto = {d["clave"]: d for d in manifiesto["documentos"]}
    with conectar() as conn:
        filas = conn.execute("SELECT clave, sha256, archivado_en IS NOT NULL FROM documentos").fetchall()
    copiados = omitidos = 0
    for clave_doc, sha, archivado in filas:
        if archivado or clave_doc in depuradas:
            omitidos += 1
            continue
        if clave_doc not in en_manifiesto:
            print(f"PROBLEMA: la base restaurada referencia un documento que el respaldo no copió ({clave_doc[:8]}…).")
            return 2
        contenido = alm.leer(ESPACIO, copia_de(en_manifiesto[clave_doc]))
        if clave is not None:
            contenido = descifrar(contenido, clave)
        if sha256(contenido) != sha:
            print(f"PROBLEMA: el documento {clave_doc[:8]}… restaurado tiene otro SHA-256 que la base.")
            return 2
        destino.guardar(DOCUMENTOS, clave_doc, contenido)
        copiados += 1
    for clave_doc in depuradas:       # lo depurado se elimina de nuevo si reapareciera
        destino.eliminar(DOCUMENTOS, clave_doc)
    print(f"Documentos restaurados: {copiados}; omitidos por archivados o depurados: {omitidos}.")
    return 0


def verificar_restauracion(args) -> int:
    if not exigir_entorno_restauracion("verificar-restauracion"):
        return 1
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
    print(f"Restauración {'VERIFICADA' if not errores else 'CON ERRORES'}"
          f"{' (respaldo cifrado)' if cifrado_de(manifiesto) else ' (respaldo SIN CIFRAR)'}: referencias comprobadas {referencias}, "
          f"depurados tras el respaldo {depurados_despues}, descargas de muestra correctas {descargas}.")
    return 0 if not errores else 2


def probar_fallos(args) -> int:
    """AC5: respaldos alterados a propósito (copias del manifiesto) deben detectarse. Se eliminan al terminar.

    Las variantes usan etiquetas reservadas: no cuentan para la retención ni como «el más reciente».
    """
    alm = origen()
    base = leer_manifiesto(alm, args.id)
    if not base["documentos"]:
        print("Se necesita un respaldo con al menos un documento.")
        return 1
    creados, resultados = [], {}
    cifrado = cifrado_de(base)

    def variante(nombre, cambio, volcado=None):
        id_ = f"{base['creado']}-{nombre}"
        m = json.loads(json.dumps(base))
        m["id"] = id_
        cambio(m)
        if volcado is not None:
            sufijo = ".dump.age" if cifrado else ".dump"
            alm.guardar(ESPACIO, f"respaldo-{id_}{sufijo}", volcado)
            m["volcado"] = {"clave": f"respaldo-{id_}{sufijo}", "sha256": sha256(volcado), "tamano": len(volcado)}
        alm.guardar(ESPACIO, f"respaldo-{id_}.json", json.dumps(m).encode())
        creados.append((id_, m["volcado"]["clave"]))
        return id_

    def inexistente(m):
        extra = {"clave": "inexistente-" + secrets.token_hex(6) + ".pdf", "sha256": "0" * 64, "tamano": 1}
        if cifrado:
            extra.update(sha256_cifrado="0" * 64, copia=f"doc-{extra['clave']}.x.age")
        m["documentos"].append(extra)

    def otro_hash(m):
        m["documentos"][0].update({"sha256_cifrado" if cifrado else "sha256": "f" * 64})

    try:
        faltante = variante("faltante", inexistente)
        distinto = variante("hash", otro_hash)
        danado = variante("danado", lambda m: None, volcado=(ENCABEZADO_AGE + secrets.token_bytes(64)) if cifrado else b"PGDMP" + secrets.token_bytes(64))
        alterado = variante("alterado", lambda m: m["volcado"].update(sha256="e" * 64))
        sin_manifiesto_id = f"{base['creado']}-sinmanifiesto"
        for nombre, id_ in (("documento faltante", faltante), ("SHA-256 distinto", distinto), ("volcado alterado", alterado),
                            ("sin manifiesto", sin_manifiesto_id)):
            problemas, _ = verificar_respaldo(alm, id_)
            resultados[nombre] = bool(problemas)
        print("DANADO_ID", danado)
    finally:
        for id_, clave_volcado in creados:
            if id_ != danado:
                for clave in (f"respaldo-{id_}.json", clave_volcado):
                    alm.eliminar(ESPACIO, clave)
        # el variante «dañado» queda para que respaldo.ps1 pruebe pg_restore --list; lo retira `quitar-prueba`
    for nombre, detectado in resultados.items():
        print(f"  {nombre}: {'detectado' if detectado else 'NO DETECTADO'}")
    return 0 if all(resultados.values()) else 2


def quitar_prueba(args) -> int:
    alm = origen()
    if not es_prueba(args.id):
        print("Solo se quitan variantes de prueba (etiquetas reservadas de probar-fallos); un respaldo real se elimina con `podar`.")
        return 1
    for sufijo in (".json", ".dump", ".dump.age"):
        alm.eliminar(ESPACIO, f"respaldo-{args.id}{sufijo}")
    return 0


def descargar_volcado(args) -> int:
    """Verifica el respaldo y deja el volcado (descifrado si hace falta) en el archivo temporal para restaurar."""
    alm = origen()
    try:
        manifiesto = leer_manifiesto(alm, args.id)
        clave = _clave_para(manifiesto)
        problemas, manifiesto = verificar_respaldo(alm, args.id, clave) if not args.sin_verificar else ([], manifiesto)
    except ClaveNoDisponible as error:
        print(f"PROBLEMA: {error}")
        return 3
    except ClaveIncorrecta as error:
        print(f"PROBLEMA: {error}")
        return 3
    except ArchivoNoEncontrado:
        print(f"PROBLEMA: el respaldo {args.id} no tiene manifiesto.")
        return 2
    if problemas:
        for p in problemas:
            print("PROBLEMA:", p)
        return 2
    TMP.mkdir(parents=True, exist_ok=True)
    contenido = alm.leer(ESPACIO, manifiesto["volcado"]["clave"])
    if clave is not None:
        contenido = descifrar(contenido, clave)
    (TMP / "restaurar.dump").write_bytes(contenido)
    print(f"Volcado del respaldo {args.id} listo para restaurar ({'descifrado' if clave is not None else 'sin cifrar'}).")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="orden", required=True)
    sub.add_parser("generar-clave").set_defaults(f=generar_clave)
    s = sub.add_parser("instantanea"); s.add_argument("--salida", default="antes.json"); s.set_defaults(f=instantanea)
    s = sub.add_parser("crear"); s.add_argument("--volcado", required=True); s.add_argument("--etiqueta", default="semanal")
    s.add_argument("--antes", default="antes.json", help="instantánea tomada antes del volcado (en la carpeta temporal)")
    s.add_argument("--sin-cifrar", action="store_true", help="solo con datos sintéticos")
    s.add_argument("--permitir-inconsistencias", action="store_true"); s.set_defaults(f=crear)
    sub.add_parser("listar").set_defaults(f=listar)
    s = sub.add_parser("verificar"); s.add_argument("--id", required=True)
    s.add_argument("--con-clave", action="store_true", help="descifra y compara también el contenido (necesita la clave privada)")
    s.set_defaults(f=verificar)
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
