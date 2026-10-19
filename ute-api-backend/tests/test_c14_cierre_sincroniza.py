import unittest
from datetime import date
from uuid import uuid4

from app.application.use_cases.dual import cierres
from app.domain import calendar

from test_c07_cierre import (ALUMNOS, APROBADAS, CONTEOS, COORDINADOR, ScriptCursor, periodo, runtime_con)

ATRASADA = {"id": uuid4(), "matricula": "111", "fecha_inicio": date(2015, 1, 5), "fecha_baja": date(2015, 2, 1),
            "activo": False, "ultima": None}


def cursor_con_alta_retroactiva(antes, despues=None):
    return ScriptCursor(
        uno={"dual.cierres.bloquear_exclusivo": [antes], "dual.cierres.periodo": [antes, despues or antes],
             "dual.cierres.conteos": [CONTEOS]},
        todos={"dual.cierres.alumnos": ALUMNOS, "dual.cierres.aprobadas": APROBADAS,
               "dual.obligaciones.candidates": [ATRASADA]})


class CierreSincronizaTest(unittest.IsolatedAsyncioTestCase):
    """C14-D3: las altas retroactivas (historial no creado al alta) se completan antes de contar o cerrar."""

    async def test_el_resumen_crea_las_semanas_faltantes_antes_de_contar(self):
        cursor = cursor_con_alta_retroactiva(periodo(abierto=True))
        await cierres.resumen(uuid4(), COORDINADOR, runtime=runtime_con(cursor))
        claves = cursor.claves
        subidas = [i for i, c in enumerate(claves) if c == "dual.obligaciones.upsert"]
        self.assertEqual(len(subidas), len(calendar.semanas_incorporacion(ATRASADA["fecha_inicio"], ATRASADA["fecha_baja"], calendar.hoy())))
        self.assertLess(max(subidas), claves.index("dual.cierres.conteos"))

    async def test_el_cierre_sincroniza_antes_de_tomar_el_bloqueo_exclusivo_y_no_toca_obligaciones_despues(self):
        cursor = cursor_con_alta_retroactiva(periodo(abierto=True), periodo(cerrado=True))
        await cierres.cerrar_recepcion(uuid4(), COORDINADOR, runtime=runtime_con(cursor))
        claves = cursor.claves
        bloqueo = claves.index("dual.cierres.bloquear_exclusivo")
        self.assertIn("dual.obligaciones.upsert", claves[:bloqueo])
        self.assertFalse([c for c in claves[bloqueo:] if c.startswith("dual.obligaciones.")])


if __name__ == "__main__":
    unittest.main()
