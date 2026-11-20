"""HU-39: registro de cambios."""
from ayudas import CLIENTE_PASSWORD
from ayudas_gestion import PDF, GestionBase
from auditoria import registrar


class RegistroDeCambiosTest(GestionBase):
    def acciones(self):
        return [e["accion"] for e in self.store.registro]

    def ultima(self):
        return self.store.registro[-1]

    # --- qué se registra --------------------------------------------------------------

    def test_el_alta_de_un_cliente(self):
        self.como_cliente()
        entrada = self.store.registro[0]
        self.assertEqual(entrada["accion"], "Cliente registrado")
        self.assertEqual(entrada["entidad"], "cliente")
        self.assertEqual(entrada["ref"], 1)
        self.assertEqual(entrada["actor"], "Cliente (Lucas Salvarrey)")
        self.assertIn("Plan Básico", entrada["detalle"])

    def test_un_registro_rechazado_no_deja_rastro(self):
        self.client.post("/registro", data={"nombre": "Alguien Inventado", "dni": "11111111",
            "email": "a@b.com", "telefono": "+54 11 5555-0000", "plan_id": "1",
            "password": CLIENTE_PASSWORD, "password2": CLIENTE_PASSWORD})
        self.assertEqual(self.store.registro, [])

    def test_el_cambio_de_perfil_dice_que_cambio(self):
        self.como_cliente()
        self.client.post("/mi-cuenta/editar", data={"email": "nuevo@ejemplo.com", "telefono": "+54 11 5555-1234"})
        entrada = self.ultima()
        self.assertEqual(entrada["accion"], "Perfil modificado")
        self.assertEqual(entrada["detalle"], "email: lucas@ejemplo.com → nuevo@ejemplo.com")

    def test_el_cambio_de_perfil_con_los_dos_campos(self):
        self.como_cliente()
        self.client.post("/mi-cuenta/editar", data={"email": "nuevo@ejemplo.com", "telefono": "+54 11 6666-0000"})
        self.assertIn("email:", self.ultima()["detalle"])
        self.assertIn("telefono:", self.ultima()["detalle"])

    def test_un_perfil_rechazado_no_se_registra(self):
        self.como_cliente()
        antes = len(self.store.registro)
        self.client.post("/mi-cuenta/editar", data={"email": "no-es-un-email", "telefono": "1"})
        self.assertEqual(len(self.store.registro), antes)

    def test_el_alta_de_un_plan(self):
        self.como_admin()
        self.crear_plan()
        entrada = self.ultima()
        self.assertEqual((entrada["accion"], entrada["entidad"]), ("Plan creado", "plan"))
        self.assertIn("Plan Empresarial", entrada["detalle"])
        self.assertIn("$ 12.500,00", entrada["detalle"])
        self.assertEqual(entrada["actor"].split(" (")[0], "Administrador")

    def test_la_modificacion_de_un_plan_muestra_antes_y_despues(self):
        self.como_admin()
        self.editar_plan(1, costo_mensual="9000", sla_horas="48")
        detalle = self.ultima()["detalle"]
        self.assertIn("costo_mensual: sin definir → $ 9.000,00", detalle)
        self.assertIn("sla_horas: sin definir → 48 h", detalle)
        self.editar_plan(1, costo_mensual="10000", sla_horas="48")
        self.assertEqual(self.ultima()["detalle"], "costo_mensual: $ 9.000,00 → $ 10.000,00")

    def test_un_plan_rechazado_no_se_registra(self):
        self.como_admin()
        self.crear_plan(nombre="")
        self.assertEqual(self.store.registro, [])

    def test_el_ciclo_de_una_solicitud(self):
        self.como_cliente()
        self.poner_costo(2)
        self.crear_solicitud(documento=("c.pdf", PDF))
        self.crear_solicitud(plan_id="3", detalle="otra")
        self.client.post("/solicitudes/2/anular")
        self.cambiar_a_admin()
        self.client.post("/admin/solicitudes/1/prioridad", data={"prioridad": "alta"})
        self.client.post("/admin/solicitudes/1/documento/validar")
        self.client.post("/admin/solicitudes/1/realizar")
        self.assertEqual(
            self.acciones()[1:],
            ["Solicitud creada", "Solicitud creada", "Solicitud anulada", "Prioridad asignada",
             "Documentación validada", "Factura generada", "Solicitud aprobada"],
        )

    def test_rechazar_una_solicitud(self):
        self.como_cliente()
        self.crear_solicitud()
        self.cambiar_a_admin()
        self.client.post("/admin/solicitudes/1/rechazar")
        self.assertEqual(self.ultima()["accion"], "Solicitud rechazada")

    def test_el_ciclo_de_una_factura(self):
        self.como_cliente()
        fid = self.insertar_factura()
        self.cambiar_a_admin()
        self.facturar(fid, falla=True)
        self.devolver(fid)
        self.assertEqual(self.acciones()[1:], ["Falla en PagoNet", "Devolución realizada"])
        self.assertEqual({e["entidad"] for e in self.store.registro[1:]}, {"factura"})

    def test_el_ciclo_de_un_reclamo(self):
        self.como_cliente()
        self.crear_reclamo()
        self.crear_reclamo()
        self.client.post("/reclamos/1/mensaje", data={"texto": "hola"})
        self.cambiar_a_admin()
        self.client.post("/admin/reclamos/1/responder", data={"texto": "ok", "accion": "resolver"})
        self.client.post("/admin/reclamos/1/reabrir")
        self.client.post("/admin/reclamos/1/escalar")
        self.assertEqual(
            self.acciones()[1:],
            ["Reclamo ingresado", "Reclamo reiterado", "Mensaje del cliente", "Reclamo resuelto",
             "Reclamo reabierto", "Reclamo escalado"],
        )

    def test_el_actor_es_quien_hizo_el_cambio(self):
        self.como_cliente()
        self.crear_reclamo()
        self.cambiar_a_admin()
        self.client.post("/admin/reclamos/1/escalar")
        self.assertEqual(self.store.registro[1]["actor"], "Cliente (Lucas Salvarrey)")
        self.assertTrue(self.store.registro[2]["actor"].startswith("Administrador ("))

    def test_sin_sesion_el_actor_es_el_sistema(self):
        with self.app.test_request_context():
            entrada = registrar("Algo automático", "sistema")
        self.assertEqual(entrada["actor"], "Sistema")

    def test_se_puede_indicar_el_actor(self):
        with self.app.test_request_context():
            entrada = registrar("Algo", "sistema", actor="Otro")
        self.assertEqual(entrada["actor"], "Otro")

    def test_cada_entrada_tiene_fecha_y_numero_propio(self):
        with self.app.test_request_context():
            for i in range(3):
                registrar(f"Acción {i}", "sistema", actor="Test")
        self.assertEqual([e["id"] for e in self.store.registro], [1, 2, 3])
        self.assertTrue(all(e["fecha"] for e in self.store.registro))

    def test_lo_que_no_cambia_nada_no_se_registra(self):
        self.como_cliente()
        antes = len(self.store.registro)
        self.html("/mi-cuenta")
        self.html("/planes")
        self.html("/solicitudes")
        self.assertEqual(len(self.store.registro), antes)


class PantallaDelRegistroTest(GestionBase):
    def cargar(self):
        with self.app.test_request_context():
            registrar("Plan creado", "plan", ref=1, detalle="PLAN-A", actor="Administrador (Ana)")
            registrar("Solicitud creada", "solicitud", ref=2, detalle="PEDIDO-B", actor="Cliente (Beto)")
            registrar("Reclamo ingresado", "reclamo", ref=3, detalle="QUEJA-C", actor="Cliente (Beto)")

    def test_exige_ser_administrador(self):
        r = self.client.get("/admin/registro")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/admin/registro", r.headers["Location"])
        self.como_cliente()
        self.assertEqual(self.client.get("/admin/registro").status_code, 403)

    def test_sin_cambios_se_informa(self):
        self.como_admin()
        self.assertIn("No hay cambios registrados", self.html("/admin/registro"))

    def test_se_muestran_quien_que_y_sobre_que(self):
        self.cargar()
        self.como_admin()
        html = self.html("/admin/registro")
        for texto in ("Administrador (Ana)", "Plan creado", "Plan #1", "PLAN-A", "Solicitud #2", "Cliente (Beto)"):
            self.assertIn(texto, html)

    def test_lo_mas_reciente_va_primero(self):
        self.cargar()
        self.como_admin()
        html = self.html("/admin/registro")
        self.assertLess(html.index("QUEJA-C"), html.index("PEDIDO-B"))
        self.assertLess(html.index("PEDIDO-B"), html.index("PLAN-A"))

    def test_filtrar_por_entidad(self):
        self.cargar()
        self.como_admin()
        html = self.html("/admin/registro?entidad=solicitud")
        self.assertIn("PEDIDO-B", html)
        self.assertNotIn("PLAN-A", html)
        self.assertNotIn("QUEJA-C", html)

    def test_una_entidad_invalida_se_ignora(self):
        self.cargar()
        self.como_admin()
        html = self.html("/admin/registro?entidad=inventada")
        self.assertIn("PLAN-A", html)
        self.assertIn("QUEJA-C", html)

    def test_buscar_por_texto(self):
        self.cargar()
        self.como_admin()
        self.assertNotIn("PLAN-A", self.html("/admin/registro?q=beto"))
        self.assertIn("PEDIDO-B", self.html("/admin/registro?q=beto"))
        self.assertIn("QUEJA-C", self.html("/admin/registro?q=BETO"))
        self.assertIn("PLAN-A", self.html("/admin/registro?q=plan creado"))

    def test_filtro_y_busqueda_se_combinan(self):
        self.cargar()
        self.como_admin()
        html = self.html("/admin/registro?entidad=reclamo&q=beto")
        self.assertIn("QUEJA-C", html)
        self.assertNotIn("PEDIDO-B", html)

    def test_un_filtro_sin_resultados_lo_explica(self):
        self.cargar()
        self.como_admin()
        self.assertIn("No hay cambios registrados con ese filtro", self.html("/admin/registro?q=nadie"))

    def test_se_muestran_como_maximo_300_cambios(self):
        with self.app.test_request_context():
            for i in range(305):
                registrar("Acción", "sistema", detalle=f"N-{i:03d}", actor="Test")
        self.como_admin()
        html = self.html("/admin/registro")
        self.assertIn("Se muestran los 300 cambios más recientes de 305", html)
        self.assertIn("N-304", html)
        self.assertNotIn("N-004", html)

    def test_el_filtro_de_entidades_ofrece_todas(self):
        self.como_admin()
        html = self.html("/admin/registro")
        for texto in ("Cliente", "Plan", "Solicitud", "Factura", "Reclamo", "Sistema"):
            self.assertIn(f">{texto}</option>", html)

    def test_el_texto_del_detalle_no_inyecta_html(self):
        with self.app.test_request_context():
            registrar("Acción", "sistema", detalle="<script>alert(1)</script>", actor="Test")
        self.como_admin()
        self.assertNotIn("<script>alert(1)</script>", self.html("/admin/registro"))
