import hashlib
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import respaldo  # noqa: E402
from pyrage import x25519  # noqa: E402
from app.infrastructure.storage.memoria import MemoriaAlmacenamiento  # noqa: E402


def sha(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def respaldo_cifrado_en(alm, id_, documentos, r, volcado=b"PGDMP" + b"x" * 60):
    """Réplica de lo que deja `crear` con cifrado: volcado y copias cifrados y manifiesto versión 2."""
    cifrado_volcado = respaldo.cifrar(volcado, r)
    clave_volcado = f"respaldo-{id_}.dump.age"
    alm.guardar("respaldos", clave_volcado, cifrado_volcado)
    entradas = []
    for clave, contenido in documentos.items():
        copia = f"doc-{clave}.{respaldo.huella_destinatario(r)}.age"
        cif = respaldo.cifrar(contenido, r)
        alm.guardar("respaldos", copia, cif)
        entradas.append({"clave": clave, "sha256": sha(contenido), "tamano": len(contenido), "copia": copia, "sha256_cifrado": sha(cif)})
    manifiesto = {
        "version": 2, "id": id_, "creado": id_[:16], "cifrado": {"metodo": "age", "destinatario": respaldo.huella_destinatario(r)},
        "volcado": {"clave": clave_volcado, "sha256": sha(cifrado_volcado), "tamano": len(cifrado_volcado),
                    "sha256_claro": sha(volcado), "tamano_claro": len(volcado)},
        "documentos": entradas, "depuraciones": []}
    alm.guardar("respaldos", f"respaldo-{id_}.json", json.dumps(manifiesto).encode())
    return manifiesto


class CifradoTest(unittest.TestCase):
    def setUp(self):
        self.i = x25519.Identity.generate()
        self.r = self.i.to_public()

    def test_ida_y_vuelta_y_clave_incorrecta(self):
        cifrado = respaldo.cifrar(b"contenido sensible", self.r)
        self.assertTrue(cifrado.startswith(respaldo.ENCABEZADO_AGE))
        self.assertNotIn(b"sensible", cifrado)
        self.assertEqual(respaldo.descifrar(cifrado, self.i), b"contenido sensible")
        with self.assertRaises(respaldo.ClaveIncorrecta):
            respaldo.descifrar(cifrado, x25519.Identity.generate())

    def test_el_cifrado_es_aleatorio(self):
        self.assertNotEqual(respaldo.cifrar(b"igual", self.r), respaldo.cifrar(b"igual", self.r))

    def test_clave_publica_ausente_o_invalida(self):
        with mock.patch.dict(os.environ, {"RESPALDO_CLAVE_PUBLICA": "", "RESPALDO_CLAVE_PUBLICA_ARCHIVO": "/no/existe.txt"}):
            with self.assertRaises(respaldo.ClaveNoDisponible):
                respaldo.destinatario()
        with mock.patch.dict(os.environ, {"RESPALDO_CLAVE_PUBLICA": "no-es-una-clave"}):
            with self.assertRaises(respaldo.ClaveNoDisponible):
                respaldo.destinatario()
        with mock.patch.dict(os.environ, {"RESPALDO_CLAVE_PUBLICA": str(self.r)}):
            self.assertEqual(str(respaldo.destinatario()), str(self.r))

    def test_clave_privada_desde_archivo(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "identidad.txt"
            ruta.write_text(f"# comentario\n{self.i}\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"RESPALDO_IDENTIDAD_ARCHIVO": str(ruta)}):
                self.assertEqual(str(respaldo.identidad().to_public()), str(self.r))
            ruta.write_text("sin clave\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"RESPALDO_IDENTIDAD_ARCHIVO": str(ruta)}):
                with self.assertRaises(respaldo.ClaveNoDisponible):
                    respaldo.identidad()
        with mock.patch.dict(os.environ, {"RESPALDO_IDENTIDAD_ARCHIVO": "/no/existe.txt"}):
            with self.assertRaises(respaldo.ClaveNoDisponible):
                respaldo.identidad()


class VerificacionCifradaTest(unittest.TestCase):
    """AC1 a AC4: lo que hay en el almacenamiento está cifrado, se verifica sin la clave y se descifra con ella."""

    def setUp(self):
        self.i = x25519.Identity.generate()
        self.r = self.i.to_public()
        self.alm = MemoriaAlmacenamiento()
        self.docs = {"a" * 32 + ".pdf": b"%PDF-1.4 uno", "b" * 32 + ".pdf": b"%PDF-1.4 dos"}
        self.id = "20261017T100000Z-semanal"
        self.m = respaldo_cifrado_en(self.alm, self.id, self.docs, self.r)

    def test_nada_legible_en_el_almacenamiento(self):
        for f in self.alm.listar("respaldos"):
            contenido = self.alm.leer("respaldos", f["clave"])
            if f["clave"].endswith(".age"):
                self.assertTrue(contenido.startswith(respaldo.ENCABEZADO_AGE), f["clave"])
                self.assertNotIn(b"%PDF", contenido)
                self.assertNotIn(b"PGDMP", contenido)

    def test_integro_sin_clave_y_con_clave(self):
        self.assertEqual(respaldo.verificar_respaldo(self.alm, self.id)[0], [])
        self.assertEqual(respaldo.verificar_respaldo(self.alm, self.id, self.i)[0], [])

    def test_clave_incorrecta_se_rechaza(self):
        with self.assertRaises(respaldo.ClaveIncorrecta):
            respaldo.verificar_respaldo(self.alm, self.id, x25519.Identity.generate())

    def test_texto_cifrado_alterado_se_detecta_sin_la_clave(self):
        copia = self.m["documentos"][0]["copia"]
        self.alm.eliminar("respaldos", copia)
        self.alm.guardar("respaldos", copia, respaldo.ENCABEZADO_AGE + b"alterado")
        self.assertTrue(any("SHA-256" in p for p in respaldo.verificar_respaldo(self.alm, self.id)[0]))

    def test_documento_o_volcado_ausente(self):
        self.alm.eliminar("respaldos", self.m["documentos"][1]["copia"])
        self.alm.eliminar("respaldos", self.m["volcado"]["clave"])
        problemas = respaldo.verificar_respaldo(self.alm, self.id)[0]
        self.assertTrue(any("Falta el documento" in p for p in problemas))
        self.assertIn("Falta el volcado de la base.", problemas)

    def test_volcado_sin_formato_cifrado(self):
        clave = self.m["volcado"]["clave"]
        self.alm.eliminar("respaldos", clave)
        falso = b"PGDMP" + b"claro" * 10
        self.alm.guardar("respaldos", clave, falso)
        m = dict(self.m, volcado=dict(self.m["volcado"], sha256=sha(falso), tamano=len(falso)))
        self.alm.eliminar("respaldos", f"respaldo-{self.id}.json")
        self.alm.guardar("respaldos", f"respaldo-{self.id}.json", json.dumps(m).encode())
        self.assertTrue(any("formato cifrado" in p for p in respaldo.verificar_respaldo(self.alm, self.id)[0]))

    def test_respaldo_sin_cifrar_version_1_sigue_verificandose(self):
        v1 = b"PGDMP" + b"y" * 40
        self.alm.guardar("respaldos", "respaldo-20261016T100000Z-semanal.dump", v1)
        self.alm.guardar("respaldos", "doc-" + "c" * 32 + ".pdf", b"%PDF-1.4 viejo")
        manifiesto = {"version": 1, "id": "20261016T100000Z-semanal", "creado": "20261016T100000Z",
                      "volcado": {"clave": "respaldo-20261016T100000Z-semanal.dump", "sha256": sha(v1), "tamano": len(v1)},
                      "documentos": [{"clave": "c" * 32 + ".pdf", "sha256": sha(b"%PDF-1.4 viejo"), "tamano": 14}], "depuraciones": []}
        self.alm.guardar("respaldos", "respaldo-20261016T100000Z-semanal.json", json.dumps(manifiesto).encode())
        self.assertFalse(respaldo.cifrado_de(manifiesto))
        self.assertEqual(respaldo.verificar_respaldo(self.alm, "20261016T100000Z-semanal")[0], [])
        self.assertEqual(respaldo.copia_de(manifiesto["documentos"][0]), "doc-" + "c" * 32 + ".pdf")

    def test_listar_distingue_cifrado_y_variantes_de_prueba_no_cuentan(self):
        respaldo_cifrado_en(self.alm, "20261017T110000Z-danado", {}, self.r)
        respaldo_cifrado_en(self.alm, "20261017T120000Z-faltante", {}, self.r)
        self.assertEqual(respaldo.ids_de(self.alm), [self.id])
        self.assertEqual(len(respaldo.ids_de(self.alm, incluir_pruebas=True)), 3)
        self.assertTrue(respaldo.es_prueba("20261017T110000Z-danado") and not respaldo.es_prueba(self.id))


class EndurecimientoTest(unittest.TestCase):
    """AC5: guardas, candado entre respaldo y poda, y variantes de prueba fuera de la retención."""

    def test_candado_unico_y_abandonado(self):
        alm = MemoriaAlmacenamiento()
        self.assertTrue(respaldo.tomar_candado(alm, ahora=1000.0))
        self.assertFalse(respaldo.tomar_candado(alm, ahora=1500.0), "Hay otro respaldo en curso")
        self.assertTrue(respaldo.candado_vigente(alm, ahora=1500.0))
        self.assertTrue(respaldo.tomar_candado(alm, ahora=1000.0 + respaldo.VIGENCIA_CANDADO + 1), "Un candado abandonado se retira")
        respaldo.soltar_candado(alm)
        self.assertFalse(respaldo.candado_vigente(alm))

    def test_la_poda_se_niega_con_un_respaldo_en_curso(self):
        alm = MemoriaAlmacenamiento()
        respaldo.tomar_candado(alm)
        with mock.patch.object(respaldo, "origen", return_value=alm):
            self.assertEqual(respaldo.podar(Namespace(aplicar=True)), 1)
            self.assertEqual(respaldo.podar(Namespace(aplicar=False)), 1)
        respaldo.soltar_candado(alm)
        with mock.patch.object(respaldo, "origen", return_value=alm):
            self.assertEqual(respaldo.podar(Namespace(aplicar=False)), 0)

    def test_subcomandos_que_escriben_solo_en_entorno_de_restauracion(self):
        with mock.patch.dict(os.environ, {"RESPALDO_ENTORNO": "", "RESPALDO_ORIGEN_CARPETA": "a", "DRIVE_CARPETA_ID": "b"}):
            self.assertFalse(respaldo.exigir_entorno_restauracion("restaurar-documentos"))
        with mock.patch.dict(os.environ, {"RESPALDO_ENTORNO": "restauracion", "RESPALDO_ORIGEN_CARPETA": "a", "DRIVE_CARPETA_ID": "a"}):
            self.assertFalse(respaldo.exigir_entorno_restauracion("restaurar-documentos"), "Misma carpeta que los respaldos")
        with mock.patch.dict(os.environ, {"RESPALDO_ENTORNO": "restauracion", "RESPALDO_ORIGEN_CARPETA": "a", "DRIVE_CARPETA_ID": "b"}):
            self.assertTrue(respaldo.exigir_entorno_restauracion("restaurar-documentos"))
        for f, args in ((respaldo.restaurar_documentos, Namespace(id="x", registro=None)),
                        (respaldo.verificar_restauracion, Namespace(id="x", registro=None, api="http://x")),
                        (respaldo.descartar_carpeta, Namespace())):
            with mock.patch.dict(os.environ, {"RESPALDO_ENTORNO": ""}):
                self.assertEqual(f(args), 1)

    def test_crear_sin_clave_publica_se_rechaza_antes_de_tocar_nada(self):
        alm = MemoriaAlmacenamiento()
        args = Namespace(etiqueta="semanal", sin_cifrar=False, volcado="/no/existe", antes="antes.json", permitir_inconsistencias=False)
        with mock.patch.object(respaldo, "origen", return_value=alm), \
                mock.patch.dict(os.environ, {"RESPALDO_CLAVE_PUBLICA": "", "RESPALDO_CLAVE_PUBLICA_ARCHIVO": "/no/existe.txt"}):
            self.assertEqual(respaldo.crear(args), 1)
        self.assertEqual(alm.listar("respaldos"), [], "No se subió nada ni se tomó el candado")

    def test_etiquetas_de_prueba_reservadas(self):
        args = Namespace(etiqueta="danado", sin_cifrar=True, volcado="/no/existe", antes="antes.json", permitir_inconsistencias=False)
        with mock.patch.object(respaldo, "origen", return_value=MemoriaAlmacenamiento()):
            self.assertEqual(respaldo.crear(args), 1)

    def test_quitar_prueba_solo_variantes(self):
        alm = MemoriaAlmacenamiento()
        alm.guardar("respaldos", "respaldo-20261017T100000Z-semanal.json", b"{}")
        with mock.patch.object(respaldo, "origen", return_value=alm):
            self.assertEqual(respaldo.quitar_prueba(Namespace(id="20261017T100000Z-semanal")), 1)
            self.assertTrue(alm.existe("respaldos", "respaldo-20261017T100000Z-semanal.json"))
            alm.guardar("respaldos", "respaldo-20261017T100000Z-danado.json", b"{}")
            self.assertEqual(respaldo.quitar_prueba(Namespace(id="20261017T100000Z-danado")), 0)
            self.assertFalse(alm.existe("respaldos", "respaldo-20261017T100000Z-danado.json"))

    def test_la_retencion_ignora_las_variantes_porque_ids_de_las_excluye(self):
        alm = MemoriaAlmacenamiento()
        for id_ in ("20261001T020000Z-semanal", "20261008T020000Z-danado"):
            alm.guardar("respaldos", f"respaldo-{id_}.json", b"{}")
        self.assertEqual(respaldo.ids_de(alm), ["20261001T020000Z-semanal"])


if __name__ == "__main__":
    unittest.main()
