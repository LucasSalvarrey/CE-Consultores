"""HU-13: dar de baja el plan (no adquirir ninguno)."""
from ayudas_gestion import GestionBase


class BajaPlanTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.poner_costo(2)

    def pedir_baja(self, **cambios):
        datos = {"plan_id": "ninguno", "detalle": "Quiero dar de baja mi plan por ahora"}
        datos.update(cambios)
        return self.crear_solicitud(**datos)

    def aprobar_baja_de_lucas(self):
        """Lucas pide la baja y el administrador la aprueba. Devuelve el id de la solicitud."""
        self.como_cliente()
        self.pedir_baja()
        self.cambiar_a_admin()
        self.client.post("/admin/solicitudes/1/realizar")
        return 1

    # --- el pedido -------------------------------------------------------------

    def test_el_formulario_ofrece_la_baja_si_el_cliente_tiene_plan(self):
        self.como_cliente()
        self.assertIn("Ninguno (dar de baja mi plan)", self.html("/solicitudes/nueva"))

    def test_sin_plan_el_formulario_no_ofrece_la_baja(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        self.assertNotIn("Ninguno (dar de baja mi plan)", self.html("/solicitudes/nueva"))

    def test_pedir_la_baja_crea_una_solicitud_de_baja_pendiente(self):
        self.como_cliente()
        r = self.pedir_baja()
        self.assertEqual(r.status_code, 302)
        s = self.store.solicitudes[1]
        self.assertEqual(s["tipo"], "baja")
        self.assertIsNone(s["plan_id"])
        self.assertEqual(s["estado"], "pendiente")

    def test_pedir_la_baja_no_cambia_el_plan_todavia(self):
        self.como_cliente()
        self.pedir_baja()
        self.assertEqual(self.store.clientes[1]["plan_id"], 1)

    def test_no_se_puede_pedir_la_baja_sin_tener_plan(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        r = self.pedir_baja()
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya no tenés un plan contratado", r.get_data(as_text=True))
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_la_baja_tambien_pide_detalle(self):
        self.como_cliente()
        self.assertEqual(self.pedir_baja(detalle="").status_code, 400)

    # --- la aprobación -------------------------------------------------------------

    def test_aprobar_la_baja_deja_al_cliente_sin_plan(self):
        self.aprobar_baja_de_lucas()
        self.assertIsNone(self.store.clientes[1]["plan_id"])
        self.assertEqual(self.store.solicitudes[1]["estado"], "realizado")

    def test_aprobar_la_baja_no_genera_factura(self):
        self.aprobar_baja_de_lucas()
        self.assertEqual(len(self.store.facturas), 0)
        self.assertNotIn("factura_id", self.store.solicitudes[1])

    def test_la_baja_no_depende_del_costo_de_ningun_plan(self):
        for plan in self.store.planes.values():
            plan["costo_mensual"] = None
        self.aprobar_baja_de_lucas()
        self.assertIsNone(self.store.clientes[1]["plan_id"])

    def test_se_avisa_al_cliente_que_su_plan_fue_dado_de_baja(self):
        self.aprobar_baja_de_lucas()
        self.assertIn("dado de baja", self.notisys.enviadas[-1]["mensaje"])
        self.assertEqual(self.notisys.enviadas[-1]["evento"], "realizado")

    def test_el_mensaje_del_administrador_explica_que_no_hay_plan(self):
        self.aprobar_baja_de_lucas()
        self.assertIn("ya no tiene un plan contratado", self.html("/admin/solicitudes"))

    def test_la_baja_queda_en_el_registro_de_cambios(self):
        self.aprobar_baja_de_lucas()
        entrada = [e for e in self.store.registro if e["accion"] == "Solicitud aprobada"][0]
        self.assertIn("sin plan", entrada["detalle"])

    # --- cómo se ve ---------------------------------------------------------------

    def test_mi_cuenta_sin_plan_lo_dice(self):
        self.aprobar_baja_de_lucas()
        self.cambiar_a_cliente()
        html = self.html("/mi-cuenta")
        self.assertIn("No tenés un plan contratado", html)
        self.assertIn("Pedir un plan", html)

    def test_el_cliente_ve_su_baja_en_sus_solicitudes(self):
        self.como_cliente()
        self.pedir_baja()
        html = self.html("/solicitudes")
        self.assertIn("Baja de plan", html)
        self.assertIn("Sin plan", html)

    def test_el_administrador_ve_la_baja_en_el_panel(self):
        self.como_cliente()
        self.pedir_baja()
        self.cambiar_a_admin()
        html = self.html("/admin/solicitudes")
        self.assertIn("Baja de plan", html)
        self.assertIn("Sin plan", html)

    def test_el_formulario_sigue_funcionando_sin_plan(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        html = self.html("/solicitudes/nueva")
        self.assertIn("no tenés un plan contratado", html)

    def test_el_catalogo_se_ve_sin_plan(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        r = self.client.get("/planes")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("Tu plan", r.get_data(as_text=True))

    # --- volver a tener un plan ------------------------------------------------------

    def test_sin_plan_se_puede_pedir_un_alta(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        r = self.crear_solicitud(plan_id="2")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.store.solicitudes[1]["tipo"], "alta")

    def test_aprobar_un_alta_asigna_el_plan_y_genera_la_factura(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        self.crear_solicitud(plan_id="2")
        self.cambiar_a_admin()
        self.client.post("/admin/solicitudes/1/realizar")
        self.assertEqual(self.store.clientes[1]["plan_id"], 2)
        self.assertEqual(len(self.store.facturas), 1)

    def test_sin_plan_no_se_puede_pedir_ninguno(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        self.assertEqual(self.crear_solicitud(plan_id="").status_code, 400)

    def test_el_tipo_de_solicitud_se_deduce_de_lo_que_se_elige(self):
        self.como_cliente()
        self.crear_solicitud(plan_id="2")       # tiene el 1 y pide el 2
        self.pedir_baja()                       # pide ninguno
        self.assertEqual(self.store.solicitudes[1]["tipo"], "cambio")
        self.assertEqual(self.store.solicitudes[2]["tipo"], "baja")
