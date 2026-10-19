import unittest
from datetime import date
from uuid import uuid4

from app.application.use_cases.dual import obligaciones
from app.domain import calendar

from test_c04_calendar import Cursor

HOY = date(2026, 10, 21)


def alta(inicio, baja=None):
    return {"id": uuid4(), "fecha_inicio": inicio, "fecha_baja": baja}


class AltaRetroactivaTest(unittest.IsolatedAsyncioTestCase):
    """C14-AC5 (D3): un alta con inicio muy antiguo no crea su historial al instante; luego se acota a min(hoy, baja)."""

    async def test_alta_reciente_genera_al_instante(self):
        cursor = Cursor()
        n = await obligaciones.generar_al_alta(cursor, alta(date(2026, 9, 7)), HOY)
        self.assertEqual(n, 7)
        self.assertEqual(sum(c[0] == "dual.obligaciones.upsert" for c in cursor.calls), 7)

    async def test_alta_retroactiva_no_genera_nada_al_instante(self):
        cursor = Cursor()
        n = await obligaciones.generar_al_alta(cursor, alta(date(2015, 1, 5)), HOY)
        self.assertEqual(n, 0)
        self.assertEqual(cursor.calls, [])

    async def test_baja_posterior_acota_la_creacion_a_la_baja(self):
        inc = alta(date(2015, 1, 5), date(2015, 3, 1))
        await obligaciones.generar_al_alta(Cursor(), inc, HOY)   # el alta no creó nada
        cursor = Cursor(many=[[{**inc, "matricula": "1", "activo": False, "ultima": None}]])
        await obligaciones.sincronizar(cursor, HOY)
        subidas = [c[1] for c in cursor.calls if c[0] == "dual.obligaciones.upsert"]
        self.assertEqual(len(subidas), len(calendar.semanas_incorporacion(inc["fecha_inicio"], inc["fecha_baja"], HOY)))
        self.assertLessEqual(len(subidas), 9)
        self.assertTrue(all(s[1] <= date(2015, 3, 1) for s in subidas))   # ninguna semana posterior a la baja

    async def test_sin_baja_sincronizar_completa_hasta_hoy(self):
        inc = alta(date(2026, 1, 5))
        cursor = Cursor(many=[[{**inc, "matricula": "1", "activo": True, "ultima": None}]])
        await obligaciones.sincronizar(cursor, HOY)
        self.assertEqual(sum(c[0] == "dual.obligaciones.upsert" for c in cursor.calls), 42)


if __name__ == "__main__":
    unittest.main()
