import os
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path

from app.application.errors import ApplicationError
from app.infrastructure.documents import dual_reports
from app.infrastructure.documents import paquetes as constructor
from app.infrastructure.storage import registro
from app.infrastructure.storage.local import LocalAlmacenamiento

from test_c08_expediente import pdf_bytes


class PaqueteParaleloTest(unittest.IsolatedAsyncioTestCase):
    """C14-AC3: las lecturas del paquete van en paralelo (ventana acotada) sin cambiar el orden ni la integridad."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.almacen = LocalAlmacenamiento(self.tmp.name)
        self.contexto = registro.usar(self.almacen)
        self.contexto.__enter__()
        self.destino = Path(self.tmp.name) / "salida.zip"

    def tearDown(self):
        self.contexto.__exit__(None, None, None)
        self.tmp.cleanup()

    async def _entradas(self, n):
        entradas, contenidos = [], {}
        for i in range(n):
            texto = f"doc{i:02d}"
            contenido = pdf_bytes(texto)
            g = await dual_reports.guardar_documento(contenido)
            entradas.append({"ruta": f"TII/p/g/{i}/{texto}.pdf", "clave": g["clave"], "sha256": g["sha256"],
                             "tamano": g["tamano"], "etiqueta": texto})
            contenidos[texto] = contenido
        return entradas, contenidos

    async def test_muchos_documentos_conservan_orden_y_contenido(self):
        entradas, contenidos = await self._entradas(25)
        estadisticas = constructor.construir_zip(entradas, b"{}", b"", self.destino)
        self.assertEqual(estadisticas["archivos"], 25)
        with zipfile.ZipFile(self.destino) as z:
            self.assertEqual(z.namelist()[2:], [e["ruta"] for e in entradas])
            for e in entradas:
                self.assertEqual(z.read(e["ruta"]), contenidos[e["etiqueta"]])
            self.assertIsNone(z.testzip())

    async def test_las_lecturas_se_solapan_pero_no_superan_los_lectores(self):
        entradas, _ = await self._entradas(12)
        original, activos, maximo, cerrojo = self.almacen.leer, [0], [0], threading.Lock()

        def lenta(espacio, clave):
            with cerrojo:
                activos[0] += 1
                maximo[0] = max(maximo[0], activos[0])
            time.sleep(0.05)
            try:
                return original(espacio, clave)
            finally:
                with cerrojo:
                    activos[0] -= 1

        self.almacen.leer = lenta
        constructor.construir_zip(entradas, b"{}", b"", self.destino)
        self.assertGreater(maximo[0], 1)
        self.assertLessEqual(maximo[0], constructor._LECTORES)

    async def test_un_documento_faltante_al_final_falla_todo_el_paquete(self):
        entradas, _ = await self._entradas(10)
        os.unlink(Path(self.tmp.name) / "documentos" / entradas[-1]["clave"][:2] / entradas[-1]["clave"])
        with self.assertRaises(ApplicationError) as caught:
            constructor.construir_zip(entradas, b"{}", b"", self.destino)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn(entradas[-1]["etiqueta"], caught.exception.detail)


if __name__ == "__main__":
    unittest.main()
