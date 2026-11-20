"""Datos de ejemplo que se cargan al iniciar la app."""
import os
import unittest
from unittest import mock

from ayudas import create_app
from datos import CLIENTE_DEMO, PASSWORD_DEMO


class DatosDemoTest(unittest.TestCase):
    """Datos de ejemplo que se cargan al iniciar la app."""

    def crear_app(self, **config):
        app = create_app({"TESTING": True, **config})
        return app.test_client(), app.extensions["store"]

    def registrar(self, client, **cambios):
        datos = {
            "nombre": "Galo Roselli", "dni": "28999111", "email": "galo@ejemplo.com",
            "telefono": "+54 11 4444-0000", "plan_id": "1",
            "password": "clave-segura-1", "password2": "clave-segura-1",
        }
        datos.update(cambios)
        return client.post("/registro", data=datos)

    def test_se_carga_un_cliente_de_ejemplo(self):
        _, store = self.crear_app(CARGAR_DATOS=True)
        self.assertEqual(len(store.clientes), 1)
        c = store.clientes[1]
        self.assertEqual(c["nombre"], CLIENTE_DEMO["nombre"])
        self.assertEqual(c["dni"], CLIENTE_DEMO["dni"])
        self.assertEqual(c["estado"], "habilitada")
        self.assertIn(c["plan_id"], store.planes)

    def test_se_puede_apagar_con_la_configuracion(self):
        _, store = self.crear_app(CARGAR_DATOS=False)
        self.assertEqual(len(store.clientes), 0)

    def test_por_defecto_esta_activado(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CARGAR_DATOS", None)
            _, store = self.crear_app()
        self.assertEqual(len(store.clientes), 1)

    def test_la_variable_de_entorno_lo_apaga(self):
        with mock.patch.dict(os.environ, {"CARGAR_DATOS": "0"}):
            _, store = self.crear_app()
        self.assertEqual(len(store.clientes), 0)

    def test_el_cliente_de_ejemplo_puede_iniciar_sesion(self):
        client, _ = self.crear_app(CARGAR_DATOS=True)
        r = client.post("/login", data={
            "email": CLIENTE_DEMO["email"], "password": PASSWORD_DEMO})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))
        self.assertIn(CLIENTE_DEMO["nombre"], client.get("/mi-cuenta").get_data(as_text=True))

    def test_la_contrasena_de_ejemplo_no_se_guarda_en_texto_plano(self):
        _, store = self.crear_app(CARGAR_DATOS=True)
        c = store.clientes[1]
        self.assertNotIn("password", c)
        self.assertNotEqual(c["password_hash"], PASSWORD_DEMO)

    def test_no_se_puede_registrar_de_nuevo_a_la_persona_de_ejemplo(self):
        client, store = self.crear_app(CARGAR_DATOS=True)
        r = self.registrar(
            client, nombre=CLIENTE_DEMO["nombre"], dni=CLIENTE_DEMO["dni"],
            email=CLIENTE_DEMO["email"], telefono=CLIENTE_DEMO["telefono"])
        self.assertEqual(r.status_code, 400)
        self.assertIn("ese DNI", r.get_data(as_text=True))
        self.assertEqual(len(store.clientes), 1)

    def test_otras_personas_del_padron_si_pueden_registrarse(self):
        client, store = self.crear_app(CARGAR_DATOS=True)
        r = self.registrar(client)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(store.clientes), 2)
        self.assertEqual(store.clientes[2]["nombre"], "Galo Roselli")  # id 2: sigue al de ejemplo

    def test_cada_app_tiene_sus_propios_datos(self):
        client1, store1 = self.crear_app(CARGAR_DATOS=True)
        _, store2 = self.crear_app(CARGAR_DATOS=True)
        self.registrar(client1)
        self.assertEqual(len(store1.clientes), 2)
        self.assertEqual(len(store2.clientes), 1)


if __name__ == "__main__":
    unittest.main()