"""HU-12.1: modificación de un plan por el administrador."""
import unittest
from decimal import Decimal

from ayudas import ADMIN_EMAIL, ADMIN_PASSWORD, PlanesBase


class PlanEdicionTest(PlanesBase):
    # --- modificar un plan (HU-12.1): acceso ------------------------------

    def test_editar_sin_sesion_redirige_al_login(self):
        r = self.client.get("/planes/1/editar")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/planes/1/editar", r.headers["Location"])

    def test_editar_prohibido_para_clientes(self):
        self.como_cliente()
        antes = dict(self.store.planes[1])
        self.assertEqual(self.client.get("/planes/1/editar").status_code, 403)
        self.assertEqual(self.editar_plan().status_code, 403)
        self.assertEqual(self.store.planes[1], antes)

    def test_editar_un_plan_inexistente_da_404(self):
        self.como_admin()
        self.assertEqual(self.client.get("/planes/99/editar").status_code, 404)
        self.assertEqual(self.editar_plan(plan_id=99).status_code, 404)

    def test_el_admin_ve_el_link_de_editar_en_cada_plan(self):
        self.como_admin()
        html = self.client.get("/planes").get_data(as_text=True)
        for plan_id in (1, 2, 3):
            self.assertIn(f"/planes/{plan_id}/editar", html)

    def test_el_cliente_no_ve_links_de_editar(self):
        self.como_cliente()
        html = self.client.get("/planes").get_data(as_text=True)
        self.assertNotIn("/planes/1/editar", html)

    # --- modificar un plan: formulario ------------------------------------

    def test_el_formulario_viene_con_los_datos_del_plan(self):
        self.como_admin()
        self.crear_plan(costo_mensual="12500,5")  # plan 4
        html = self.client.get("/planes/4/editar").get_data(as_text=True)
        self.assertIn("Editar plan", html)
        self.assertIn('value="Plan Empresarial"', html)
        self.assertIn("Atención prioritaria", html)
        self.assertIn('value="12500,50"', html)
        self.assertIn('value="24"', html)

    def test_el_formulario_de_un_plan_precargado_viene_sin_costo_ni_sla(self):
        self.como_admin()
        html = self.client.get("/planes/1/editar").get_data(as_text=True)
        self.assertIn('value="Plan Básico"', html)
        self.assertIn('name="costo_mensual" value=""', html)
        self.assertIn('name="sla_horas" value=""', html)

    # --- modificar un plan: cambios válidos -------------------------------

    def test_modifica_el_plan(self):
        self.como_admin()
        r = self.editar_plan(nombre="Plan Básico Plus")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/planes"))
        plan = self.store.planes[1]
        self.assertEqual(plan["id"], 1)
        self.assertEqual(plan["nombre"], "Plan Básico Plus")
        self.assertEqual(plan["descripcion"], "Descripción nueva")
        self.assertEqual(plan["costo_mensual"], Decimal("9000.00"))
        self.assertEqual(plan["sla_horas"], 48)
        self.assertIn("modificado", plan)

    def test_completar_un_plan_precargado_se_ve_en_el_catalogo(self):
        self.como_admin()
        r = self.client.post("/planes/1/editar", follow_redirects=True, data={
            "nombre": "Plan Básico", "descripcion": "Descripción nueva",
            "costo_mensual": "9000", "sla_horas": "48"})
        html = r.get_data(as_text=True)
        self.assertIn("Se actualizó el plan", html)
        self.assertIn("$ 9.000,00", html)
        self.assertIn("48 h", html)

    def test_no_afecta_a_los_otros_planes(self):
        self.como_admin()
        antes = dict(self.store.planes[2])
        self.editar_plan(nombre="Otro nombre")
        self.assertEqual(self.store.planes[2], antes)
        self.assertEqual(len(self.store.planes), 3)

    def test_puede_conservar_su_propio_nombre(self):
        self.como_admin()
        self.assertEqual(self.editar_plan(costo_mensual="9500").status_code, 302)
        self.assertEqual(self.store.planes[1]["costo_mensual"], Decimal("9500.00"))

    def test_puede_cambiar_solo_las_mayusculas_de_su_nombre(self):
        self.como_admin()
        self.assertEqual(self.editar_plan(nombre="PLAN BÁSICO").status_code, 302)
        self.assertEqual(self.store.planes[1]["nombre"], "PLAN BÁSICO")

    def test_sin_cambios_lo_avisa_y_no_modifica(self):
        self.como_admin()
        self.editar_plan()  # completa el plan por primera vez
        antes = dict(self.store.planes[1])
        r = self.client.post("/planes/1/editar", follow_redirects=True, data={
            "nombre": "Plan Básico", "descripcion": "Descripción nueva",
            "costo_mensual": "9000", "sla_horas": "48"})
        self.assertIn("No hiciste ningún cambio", r.get_data(as_text=True))
        self.assertEqual(self.store.planes[1], antes)

    def test_el_nombre_nuevo_se_ve_en_mi_cuenta_del_cliente(self):
        self.como_cliente()  # Lucas queda registrado con el plan 1
        admin = self.app.test_client()
        admin.post("/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        admin.post("/planes/1/editar", data={
            "nombre": "Plan Básico Plus", "descripcion": "Descripción nueva",
            "costo_mensual": "9000", "sla_horas": "48"})
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn("Plan Básico Plus", html)

    def test_el_nombre_nuevo_se_ve_al_registrarse(self):
        self.como_admin()
        self.editar_plan(nombre="Plan Básico Plus")
        self.client.post("/logout")
        html = self.client.get("/registro").get_data(as_text=True)
        self.assertIn("Plan Básico Plus", html)

    # --- modificar un plan: cambios inválidos -----------------------------

    def test_nombre_de_otro_plan_sin_importar_mayusculas(self):
        self.como_admin()
        antes = dict(self.store.planes[1])
        r = self.editar_plan(nombre="plan estándar")  # ya lo usa el plan 2
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya existe un plan", r.get_data(as_text=True))
        self.assertEqual(self.store.planes[1], antes)

    def test_una_edicion_invalida_no_guarda_nada(self):
        self.como_admin()
        antes = dict(self.store.planes[1])
        invalidas = [
            {"nombre": ""}, {"descripcion": ""}, {"costo_mensual": "12.500"},
            {"costo_mensual": "0"}, {"sla_horas": "0"}, {"sla_horas": "abc"},
        ]
        for cambios in invalidas:
            self.assertEqual(self.editar_plan(**cambios).status_code, 400, cambios)
        self.assertEqual(self.store.planes[1], antes)

    def test_error_al_editar_conserva_lo_escrito(self):
        self.como_admin()
        html = self.editar_plan(costo_mensual="abc", descripcion="Mi texto").get_data(as_text=True)
        self.assertIn("Mi texto", html)
        self.assertIn('value="abc"', html)


if __name__ == "__main__":
    unittest.main()