"""Login del administrador y separación de permisos entre administrador y cliente."""
import unittest

from ayudas import ADMIN_EMAIL, CLIENTE_PASSWORD, PlanesBase


class PlanesLoginTest(PlanesBase):
    # --- login del administrador ------------------------------------------

    def test_admin_inicia_sesion_y_va_a_su_panel(self):
        r = self.como_admin()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/admin"))
        with self.client.session_transaction() as s:
            self.assertEqual(s.get("admin_id"), 1)
            self.assertNotIn("cliente_id", s)

    def test_admin_con_contrasena_incorrecta(self):
        r = self.login(ADMIN_EMAIL, "otra-clave-123")
        self.assertEqual(r.status_code, 401)
        self.assertIn("Email o contraseña incorrectos", r.get_data(as_text=True))

    def test_menu_del_administrador(self):
        self.como_admin()
        html = self.client.get("/planes").get_data(as_text=True)
        self.assertIn("(administrador)", html)
        self.assertIn("Salir", html)
        self.assertNotIn("Mi cuenta", html)

    def test_admin_cierra_sesion(self):
        self.como_admin()
        self.client.post("/logout")
        self.assertEqual(self.client.get("/planes").status_code, 302)

    def test_admin_no_entra_a_paginas_de_cliente(self):
        self.como_admin()
        r = self.client.get("/mi-cuenta")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_un_cliente_no_puede_registrarse_con_el_email_del_admin(self):
        r = self.client.post("/registro", data={
            "nombre": "Lucas Salvarrey", "dni": "45786322", "email": ADMIN_EMAIL,
            "telefono": "+54 11 5555-1234", "plan_id": "1",
            "password": CLIENTE_PASSWORD, "password2": CLIENTE_PASSWORD,
        })
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.store.clientes), 0)

    def test_un_cliente_no_puede_cambiar_su_email_al_del_admin(self):
        self.como_cliente()
        r = self.client.post("/mi-cuenta/editar", data={
            "email": ADMIN_EMAIL, "telefono": "+54 11 5555-1234"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.store.clientes[1]["email"], "lucas@ejemplo.com")


if __name__ == "__main__":
    unittest.main()