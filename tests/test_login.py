import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

EMAIL = "lucas@ejemplo.com"
PASSWORD = "clave-segura-1"


class LoginTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "CARGAR_DATOS": False})
        self.client = self.app.test_client()
        # Lucas Salvarrey figura en el padrón de prueba de VeriCheck.
        self.client.post("/registro", data={
            "nombre": "Lucas Salvarrey", "dni": "45786322", "email": EMAIL,
            "telefono": "+54 11 5555-1234", "plan_id": "1",
            "password": PASSWORD, "password2": PASSWORD,
        }
        )
        self.client.post("/logout")

    def login(self, email=EMAIL, password=PASSWORD, **extra):
        return self.client.post("/login", data={"email": email, "password": password, **extra})

    def cliente_en_sesion(self):
        with self.client.session_transaction() as s:
            return s.get("cliente_id")

    def test_pagina_de_login(self):
        r = self.client.get("/login")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Ingresar", r.get_data(as_text=True))

    def test_login_correcto_inicia_sesion(self):
        r = self.login()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))
        self.assertEqual(self.cliente_en_sesion(), 1)

    def test_email_no_distingue_mayusculas(self):
        self.assertEqual(self.login(email="LUCAS@EJEMPLO.COM ").status_code, 302)

    def test_contrasena_incorrecta(self):
        r = self.login(password="otra-clave-123")
        self.assertEqual(r.status_code, 401)
        self.assertIn("Email o contraseña incorrectos", r.get_data(as_text=True))
        self.assertIsNone(self.cliente_en_sesion())

    def test_email_inexistente_da_el_mismo_mensaje(self):
        r = self.login(email="nadie@ejemplo.com")
        self.assertEqual(r.status_code, 401)
        self.assertIn("Email o contraseña incorrectos", r.get_data(as_text=True))
        self.assertIsNone(self.cliente_en_sesion())

    def test_error_conserva_email_pero_no_contrasena(self):
        html = self.login(password="mala-clave-999").get_data(as_text=True)
        self.assertIn(EMAIL, html)
        self.assertNotIn("mala-clave-999", html)

    def test_mi_cuenta_sin_sesion_redirige_al_login(self):
        r = self.client.get("/mi-cuenta")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/mi-cuenta", r.headers["Location"])

    def test_mi_cuenta_con_sesion_muestra_los_datos(self):
        self.login()
        r = self.client.get("/mi-cuenta")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        for dato in ("Lucas Salvarrey", "45786322", EMAIL, "Plan Básico"):
            self.assertIn(dato, html)
        self.assertNotIn("password", html.lower().replace("contraseña", ""))

    def test_vuelve_a_la_pagina_que_queria_ver(self):
        r = self.login(next="/mi-cuenta")
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))

    def test_next_hacia_otro_sitio_se_ignora(self):
        for malo in ("https://sitio-malo.com", "//sitio-malo.com", "/\\sitio-malo.com"):
            self.client.post("/logout")
            r = self.login(next=malo)
            self.assertEqual(r.status_code, 302, malo)
            self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"), malo)

    def test_menu_cambia_segun_la_sesion(self):
        html = self.client.get("/login").get_data(as_text=True)
        self.assertIn("Registrarme", html)
        self.assertNotIn("Salir", html)
        self.login()
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn("Hola, Lucas Salvarrey", html)
        self.assertIn("Salir", html)

    def test_logout_cierra_la_sesion(self):
        self.login()
        r = self.client.post("/logout")
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(self.cliente_en_sesion())
        self.assertEqual(self.client.get("/mi-cuenta").status_code, 302)

    def test_logout_solo_por_post(self):
        self.login()
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.cliente_en_sesion(), 1)

    def test_con_sesion_iniciada_el_login_redirige(self):
        self.login()
        r = self.client.get("/login")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))

    def test_sesion_de_cliente_que_ya_no_existe(self):
        # Pasa si el servidor se reinicia: la cookie queda pero la memoria no.
        with self.client.session_transaction() as s:
            s["cliente_id"] = 999
        self.assertEqual(self.client.get("/mi-cuenta").status_code, 302)
        self.assertEqual(self.client.get("/login").status_code, 200)

    def test_inicio_lleva_a_mi_cuenta(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))


if __name__ == "__main__":
    unittest.main()