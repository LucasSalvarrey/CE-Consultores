"""HU-11.1: alta de planes por el administrador."""
import unittest
from decimal import Decimal

from ayudas import PlanesBase


class PlanAltaTest(PlanesBase):
    # --- acceso al alta (HU-11.1) -----------------------------------------

    def test_alta_sin_sesion_redirige_al_login(self):
        r = self.client.get("/planes/nuevo")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/planes/nuevo", r.headers["Location"])

    def test_alta_prohibida_para_clientes(self):
        self.como_cliente()
        self.assertEqual(self.client.get("/planes/nuevo").status_code, 403)
        self.assertEqual(self.crear_plan().status_code, 403)
        self.assertEqual(len(self.store.planes), 3)

    def test_admin_ve_el_formulario(self):
        self.como_admin()
        r = self.client.get("/planes/nuevo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Costo mensual", r.get_data(as_text=True))

    # --- alta válida ------------------------------------------------------

    def test_alta_valida_crea_el_plan(self):
        self.como_admin()
        r = self.crear_plan()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/planes"))
        self.assertEqual(len(self.store.planes), 4)
        plan = self.store.planes[4]  # los precargados ocupan 1, 2 y 3
        self.assertEqual(plan["nombre"], "Plan Empresarial")
        self.assertEqual(plan["costo_mensual"], Decimal("12500.00"))
        self.assertEqual(plan["sla_horas"], 24)

    def test_no_pisa_los_planes_precargados(self):
        self.como_admin()
        self.crear_plan()
        self.assertEqual(self.store.planes[1]["nombre"], "Plan Básico")
        self.assertEqual(self.store.planes[3]["nombre"], "Plan Premium")

    def test_el_plan_nuevo_aparece_en_el_catalogo_con_formato(self):
        self.como_admin()
        r = self.client.post("/planes/nuevo", follow_redirects=True, data={
            "nombre": "Plan Empresarial", "descripcion": "Atención prioritaria",
            "costo_mensual": "1234567,5", "sla_horas": "24"})
        html = r.get_data(as_text=True)
        self.assertIn("Se creó el plan", html)
        self.assertIn("Plan Empresarial", html)
        self.assertIn("$ 1.234.567,50", html)
        self.assertIn("24 h", html)

    def test_el_plan_nuevo_se_puede_elegir_al_registrarse(self):
        self.como_admin()
        self.crear_plan()
        self.client.post("/logout")
        html = self.client.get("/registro").get_data(as_text=True)
        self.assertIn("Plan Empresarial", html)

    def test_costo_con_coma_o_punto(self):
        self.como_admin()
        self.crear_plan(nombre="A", costo_mensual="12500,5")
        self.crear_plan(nombre="B", costo_mensual="99.99")
        self.assertEqual(self.store.planes[4]["costo_mensual"], Decimal("12500.50"))
        self.assertEqual(self.store.planes[5]["costo_mensual"], Decimal("99.99"))

    def test_nombre_se_guarda_sin_espacios_de_mas(self):
        self.como_admin()
        self.crear_plan(nombre="  Plan    Oro ")
        self.assertEqual(self.store.planes[4]["nombre"], "Plan Oro")

    def test_los_textos_se_escapan_en_la_pagina(self):
        self.como_admin()
        self.crear_plan(nombre="<script>alert(1)</script>")
        html = self.client.get("/planes").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    # --- alta inválida ----------------------------------------------------

    def test_campos_vacios(self):
        self.como_admin()
        r = self.client.post("/planes/nuevo", data={})
        self.assertEqual(r.status_code, 400)
        html = r.get_data(as_text=True)
        for mensaje in ("nombre del plan", "una descripción", "costo mayor a cero", "número entero de horas"):
            self.assertIn(mensaje, html)
        self.assertEqual(len(self.store.planes), 3)

    def test_costos_invalidos(self):
        self.como_admin()
        # "12.500" y "12,500" son ambiguos: se rechazan en vez de adivinar.
        for malo in ("abc", "0", "0,00", "-5", "12.500", "12,500", "1e5", " "):
            self.assertEqual(self.crear_plan(costo_mensual=malo).status_code, 400, malo)
        self.assertEqual(len(self.store.planes), 3)

    def test_sla_invalidos(self):
        self.como_admin()
        for malo in ("0", "-3", "abc", "1.5", "10000", "²", ""):
            self.assertEqual(self.crear_plan(sla_horas=malo).status_code, 400, malo)
        self.assertEqual(len(self.store.planes), 3)

    def test_nombre_repetido_sin_importar_mayusculas(self):
        self.como_admin()
        r = self.crear_plan(nombre="plan básico")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya existe un plan", r.get_data(as_text=True))
        self.assertEqual(len(self.store.planes), 3)

    def test_nombre_y_descripcion_demasiado_largos(self):
        self.como_admin()
        self.assertEqual(self.crear_plan(nombre="x" * 61).status_code, 400)
        self.assertEqual(self.crear_plan(descripcion="x" * 301).status_code, 400)

    def test_error_conserva_lo_escrito_y_no_guarda(self):
        self.como_admin()
        html = self.crear_plan(costo_mensual="abc", descripcion="Mi texto").get_data(as_text=True)
        self.assertIn("Plan Empresarial", html)
        self.assertIn("Mi texto", html)
        self.assertEqual(len(self.store.planes), 3)


if __name__ == "__main__":
    unittest.main()