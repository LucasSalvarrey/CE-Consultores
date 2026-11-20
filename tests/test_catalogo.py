"""HU-08.1: catálogo de planes."""
import unittest

from ayudas import PlanesBase


class CatalogoTest(PlanesBase):
    # --- catálogo (HU-08.1) -----------------------------------------------

    def test_catalogo_exige_sesion(self):
        r = self.client.get("/planes")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/planes", r.headers["Location"])

    def test_cliente_ve_los_planes_precargados(self):
        self.como_cliente()
        html = self.client.get("/planes").get_data(as_text=True)
        for nombre in ("Plan Básico", "Plan Estándar", "Plan Premium"):
            self.assertIn(nombre, html)
        self.assertIn("A definir", html)  # no se inventan costos ni SLA

    def test_cliente_no_ve_el_boton_de_nuevo_plan(self):
        self.como_cliente()
        self.assertNotIn("Nuevo plan", self.client.get("/planes").get_data(as_text=True))

    def test_admin_ve_el_boton_de_nuevo_plan(self):
        self.como_admin()
        self.assertIn("Nuevo plan", self.client.get("/planes").get_data(as_text=True))

    def test_menu_del_cliente_tiene_planes(self):
        self.como_cliente()
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn('href="/planes"', html)


if __name__ == "__main__":
    unittest.main()