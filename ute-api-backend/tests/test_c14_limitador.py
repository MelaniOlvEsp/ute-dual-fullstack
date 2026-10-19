import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from app.infrastructure.security.jwt_passwords import crear_token
from app.presentation.middleware.security import (
    RateLimitMiddleware, SecurityHeadersMiddleware, ip_del_cliente, redes_de_confianza, usuario_del_token)


def token(id_):
    return {"Authorization": "Bearer " + crear_token({"id": id_, "sub": f"{id_}@ute.edu.mx"})}


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def crear_app(reloj, **limites):
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    # Mismo orden que `main.py`: el limitador es el más interno.
    app.add_middleware(RateLimitMiddleware, reloj=reloj, **limites)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET"], allow_headers=["Authorization"])
    return app


class LimitadorTest(unittest.TestCase):
    """C14-AC1: al pasar el límite hay un 429 real con Retry-After (no un 500), por usuario y con respaldo por IP."""

    def setUp(self):
        self.reloj = Reloj()
        self.cliente = TestClient(crear_app(self.reloj, limite_usuario=5, limite_ip_anonima=3, limite_ip_total=20, proxies=""),
                                  raise_server_exceptions=False)

    def test_sin_sesion_el_limite_es_por_ip_y_responde_429_con_retry_after(self):
        estados = [self.cliente.get("/ping").status_code for _ in range(5)]
        self.assertEqual(estados, [200, 200, 200, 429, 429])
        r = self.cliente.get("/ping")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()["detail"], "Demasiadas solicitudes. Intenta de nuevo en unos segundos.")
        self.assertTrue(r.headers["Retry-After"].isdigit() and 1 <= int(r.headers["Retry-After"]) <= 61)

    def test_el_429_lleva_las_cabeceras_de_seguridad_y_de_cors(self):
        for _ in range(3):
            self.cliente.get("/ping")
        r = self.cliente.get("/ping", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://localhost:5173")

    def test_los_usuarios_no_se_limitan_entre_si_aunque_compartan_la_ip(self):
        for _ in range(5):
            self.assertEqual(self.cliente.get("/ping", headers=token("ana")).status_code, 200)
        self.assertEqual(self.cliente.get("/ping", headers=token("ana")).status_code, 429)
        self.assertEqual(self.cliente.get("/ping", headers=token("luis")).status_code, 200)

    def test_tope_de_respaldo_por_ip(self):
        pequeno = TestClient(crear_app(self.reloj, limite_usuario=50, limite_ip_anonima=50, limite_ip_total=6, proxies=""),
                             raise_server_exceptions=False)
        estados = [pequeno.get("/ping", headers=token(f"u{i}")).status_code for i in range(8)]
        self.assertEqual(estados, [200] * 6 + [429, 429])

    def test_la_ventana_se_renueva(self):
        for _ in range(3):
            self.cliente.get("/ping")
        self.assertEqual(self.cliente.get("/ping").status_code, 429)
        self.reloj.t += 61
        self.assertEqual(self.cliente.get("/ping").status_code, 200)

    def test_health_no_cuenta(self):
        for _ in range(50):
            self.assertEqual(self.cliente.get("/health").status_code, 200)
        self.assertEqual(self.cliente.get("/ping").status_code, 200)

    def test_token_invalido_o_vencido_cuenta_como_anonimo(self):
        for _ in range(3):
            self.cliente.get("/ping", headers={"Authorization": "Bearer no-es-un-token"})
        self.assertEqual(self.cliente.get("/ping", headers={"Authorization": "Bearer no-es-un-token"}).status_code, 429)
        self.assertIsNone(usuario_del_token("Bearer basura"))
        self.assertIsNone(usuario_del_token(""))
        self.assertEqual(usuario_del_token(token("ana")["Authorization"]), "ana")

    def test_sin_trazas_ni_500_bajo_rafaga(self):
        estados = {self.cliente.get("/ping").status_code for _ in range(60)}
        self.assertEqual(estados, {200, 429})


class IpDelClienteTest(unittest.TestCase):
    def pet(self, ip, xff=None):
        return SimpleNamespace(client=SimpleNamespace(host=ip), headers={"x-forwarded-for": xff} if xff else {})

    def test_sin_proxies_configurados_se_ignora_x_forwarded_for(self):
        self.assertEqual(ip_del_cliente(self.pet("10.0.0.9", "1.2.3.4"), []), "10.0.0.9")

    def test_proxy_de_confianza_usa_la_direccion_mas_a_la_derecha_que_no_es_de_confianza(self):
        redes = redes_de_confianza("172.18.0.0/16, 10.0.0.5")
        self.assertEqual(ip_del_cliente(self.pet("172.18.0.2", "9.9.9.9, 8.8.8.8, 172.18.0.7"), redes), "8.8.8.8")
        self.assertEqual(ip_del_cliente(self.pet("172.18.0.2", "172.18.0.7"), redes), "172.18.0.2")

    def test_si_el_socket_no_es_de_confianza_nadie_puede_falsear_la_ip(self):
        redes = redes_de_confianza("172.18.0.0/16")
        self.assertEqual(ip_del_cliente(self.pet("203.0.113.5", "1.1.1.1"), redes), "203.0.113.5")

    def test_valores_no_validos_no_rompen(self):
        redes = redes_de_confianza("172.18.0.0/16")
        self.assertEqual(ip_del_cliente(self.pet("172.18.0.2", "no-es-ip, tampoco"), redes), "tampoco")


if __name__ == "__main__":
    unittest.main()
