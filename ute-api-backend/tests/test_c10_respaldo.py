import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import respaldo  # noqa: E402
from app.infrastructure.storage.memoria import MemoriaAlmacenamiento  # noqa: E402


def sha(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def respaldo_en(alm, id_, documentos, volcado=b"PGDMP" + b"x" * 40):
    for clave, contenido in documentos.items():
        alm.guardar("respaldos", "doc-" + clave, contenido)
    alm.guardar("respaldos", f"respaldo-{id_}.dump", volcado)
    manifiesto = {"id": id_, "creado": id_[:16], "volcado": {"clave": f"respaldo-{id_}.dump", "sha256": sha(volcado), "tamano": len(volcado)},
                  "documentos": [{"clave": c, "sha256": sha(b), "tamano": len(b)} for c, b in documentos.items()], "depuraciones": []}
    alm.guardar("respaldos", f"respaldo-{id_}.json", json.dumps(manifiesto).encode())


class RetencionTest(unittest.TestCase):
    """DP-11: 8 respaldos semanales recientes y el más antiguo de cada uno de los 4 meses más recientes."""

    def test_conserva_ocho_recientes_y_cuatro_mensuales(self):
        ids = [f"2026{mes:02d}{dia:02d}T020000Z-semanal" for mes in range(1, 11) for dia in (3, 10, 17, 24)]
        conservar = respaldo.plan_de_retencion(ids)
        recientes = sorted(ids, reverse=True)[:8]
        mensuales = {f"2026{mes:02d}03T020000Z-semanal" for mes in (7, 8, 9, 10)}
        self.assertEqual(conservar, set(recientes) | mensuales)
        self.assertLessEqual(len(conservar), 12)
        self.assertNotIn("20260110T020000Z-semanal", conservar)

    def test_con_pocos_respaldos_se_conserva_todo(self):
        ids = ["20261001T020000Z-semanal", "20261008T020000Z-periodo"]
        self.assertEqual(respaldo.plan_de_retencion(ids), set(ids))
        self.assertEqual(respaldo.plan_de_retencion([]), set())


class VerificacionTest(unittest.TestCase):
    """AC5: un respaldo incompleto o alterado se detecta con un motivo."""

    def setUp(self):
        self.alm = MemoriaAlmacenamiento()
        self.docs = {"a" * 32 + ".pdf": b"%PDF-1.4 uno", "b" * 32 + ".pdf": b"%PDF-1.4 dos"}
        respaldo_en(self.alm, "20261017T100000Z-semanal", self.docs)

    def problemas(self, id_="20261017T100000Z-semanal"):
        return respaldo.verificar_respaldo(self.alm, id_)[0]

    def test_respaldo_integro(self):
        self.assertEqual(self.problemas(), [])

    def test_documento_faltante(self):
        self.alm.eliminar("respaldos", "doc-" + "a" * 32 + ".pdf")
        self.assertTrue(any("Falta el documento" in p for p in self.problemas()))

    def test_documento_con_otro_hash(self):
        self.alm.eliminar("respaldos", "doc-" + "b" * 32 + ".pdf")
        self.alm.guardar("respaldos", "doc-" + "b" * 32 + ".pdf", b"%PDF-1.4 alterado")
        self.assertTrue(any("otro SHA-256" in p for p in self.problemas()))

    def test_volcado_alterado_o_ausente(self):
        clave = "respaldo-20261017T100000Z-semanal.dump"
        self.alm.eliminar("respaldos", clave)
        self.assertIn("Falta el volcado de la base.", self.problemas())
        self.alm.guardar("respaldos", clave, b"PGDMP" + b"y" * 40)
        self.assertTrue(any("no coincide con el manifiesto" in p for p in self.problemas()))

    def test_sin_manifiesto_el_respaldo_esta_incompleto(self):
        self.alm.guardar("respaldos", "respaldo-20261017T110000Z-semanal.dump", b"PGDMP" + b"z" * 40)
        self.assertTrue(any("incompleto" in p for p in self.problemas("20261017T110000Z-semanal")))

    def test_los_respaldos_se_listan_por_manifiesto(self):
        respaldo_en(self.alm, "20261018T100000Z-periodo", {})
        self.assertEqual(respaldo.ids_de(self.alm), ["20261018T100000Z-periodo", "20261017T100000Z-semanal"])


class HuellaTest(unittest.TestCase):
    """M2: la huella no da falsos errores si hubo cambios durante el respaldo."""

    def test_en_reposo_debe_coincidir(self):
        self.assertEqual(respaldo.comparar_huella("a", ["a", "a"]), "coincide")
        self.assertEqual(respaldo.comparar_huella("b", ["a", "a"]), "distinta")

    def test_con_cambios_durante_el_respaldo(self):
        self.assertEqual(respaldo.comparar_huella("a", ["a", "c"]), "coincide")
        self.assertEqual(respaldo.comparar_huella("c", ["a", "c"]), "coincide")
        self.assertEqual(respaldo.comparar_huella("intermedia", ["a", "c"]), "no_concluyente")


class InstantaneaTest(unittest.TestCase):
    """M1: los conteos y la huella se toman antes del volcado y el respaldo se rechaza sin ellos."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = Path(self.dir.name) / "antes.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_instantanea_valida(self):
        datos = {"conteos": {"documentos": 3}, "huella": "h", "instante": __import__("time").time()}
        self.ruta.write_text(json.dumps(datos), encoding="utf-8")
        self.assertEqual(respaldo.leer_instantanea(self.ruta)["conteos"], {"documentos": 3})

    def test_instantanea_vieja_incompleta_o_ausente_se_rechaza(self):
        self.ruta.write_text(json.dumps({"conteos": {}, "huella": "h", "instante": 1}), encoding="utf-8")
        with self.assertRaises(ValueError):
            respaldo.leer_instantanea(self.ruta)
        self.ruta.write_text(json.dumps({"conteos": {}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            respaldo.leer_instantanea(self.ruta)
        with self.assertRaises(OSError):
            respaldo.leer_instantanea(Path(self.dir.name) / "no-existe.json")

    def test_el_volcado_va_despues_de_la_instantanea_en_el_procedimiento(self):
        ruta = Path(__file__).resolve().parents[2] / "scripts" / "respaldo.ps1"
        if not ruta.is_file():
            self.skipTest("El procedimiento PowerShell no está en la imagen del backend.")
        texto = ruta.read_text(encoding="utf-8-sig")
        self.assertLess(texto.index("'instantanea'"), texto.index("pg_dump"))


if __name__ == "__main__":
    unittest.main()
