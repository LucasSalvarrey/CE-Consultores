"""US3 a US6: solicitudes de modificación de plan (crear, ver, anular y realizar)."""
import unittest
from decimal import Decimal

from ayudas import PlanesBase, create_app


class SolicitudesBase(PlanesBase):
    """Atajos para los tests de solicitudes."""

    def crear_solicitud(self, **cambios):
        datos = {"plan_id": "2", "detalle": "Quiero más atención prioritaria"}
        datos.update(cambios)
        return self.client.post("/solicitudes/nueva", data=datos)

    def insertar(self, cliente_id=1, estado="pendiente", plan_id=2, detalle="Detalle de prueba"):
        """Carga una solicitud directo en el Store, sin pasar por el formulario."""
        solicitud_id = self.store.siguiente_id("solicitudes")
        self.store.solicitudes[solicitud_id] = {
            "id": solicitud_id, "cliente_id": cliente_id, "plan_id": plan_id,
            "detalle": detalle, "estado": estado, "creado": "2026-01-01T10:00:00",
        }
        return solicitud_id

    def cambiar_a_admin(self):
        self.client.post("/logout")
        self.como_admin()

    def poner_costo(self, plan_id, costo="9000.00"):
        """Le define un costo mensual al plan: sin costo, PagoNet no puede facturarlo."""
        self.store.planes[plan_id]["costo_mensual"] = Decimal(costo)

    def agregar_cliente_ajeno(self):
        """Un segundo cliente, completo, para que el registro de Lucas no se rompa."""
        self.store.clientes[2] = {
            "id": 2, "nombre": "Galo Roselli", "dni": "28999111", "email": "galo@ejemplo.com",
            "telefono": "+54 11 4444-0000", "plan_id": 1,
        }


class CrearSolicitudTest(SolicitudesBase):
    # --- US3: el cliente crea una solicitud ---------------------------------

    def test_el_formulario_exige_sesion(self):
        r = self.client.get("/solicitudes/nueva")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/solicitudes/nueva", r.headers["Location"])

    def test_el_formulario_muestra_el_plan_actual_y_los_planes(self):
        self.como_cliente()
        html = self.client.get("/solicitudes/nueva").get_data(as_text=True)
        self.assertIn("Tu plan actual es", html)
        for nombre in ("Plan Básico", "Plan Estándar", "Plan Premium"):
            self.assertIn(nombre, html)

    def test_crear_una_solicitud_la_deja_pendiente(self):
        self.como_cliente()
        r = self.crear_solicitud()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/solicitudes"))
        self.assertEqual(len(self.store.solicitudes), 1)
        s = self.store.solicitudes[1]
        self.assertEqual(s["estado"], "pendiente")
        self.assertEqual(s["cliente_id"], 1)
        self.assertEqual(s["plan_id"], 2)
        self.assertEqual(s["detalle"], "Quiero más atención prioritaria")
        self.assertIn("creado", s)

    def test_tras_crearla_se_ve_el_aviso(self):
        self.como_cliente()
        self.crear_solicitud()
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("quedó pendiente", html)

    def test_el_plan_es_obligatorio(self):
        self.como_cliente()
        self.assertEqual(self.crear_solicitud(plan_id="").status_code, 400)
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_plan_inexistente_o_invalido(self):
        self.como_cliente()
        self.assertEqual(self.crear_solicitud(plan_id="99").status_code, 400)
        self.assertEqual(self.crear_solicitud(plan_id="abc").status_code, 400)
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_no_se_puede_pedir_el_plan_que_ya_se_tiene(self):
        self.como_cliente()  # Lucas arranca con el plan 1
        r = self.crear_solicitud(plan_id="1")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya tenés contratado ese plan", r.get_data(as_text=True))
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_el_detalle_es_obligatorio(self):
        self.como_cliente()
        self.assertEqual(self.crear_solicitud(detalle="").status_code, 400)
        self.assertEqual(self.crear_solicitud(detalle="    ").status_code, 400)
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_el_detalle_tiene_un_maximo(self):
        self.como_cliente()
        self.assertEqual(self.crear_solicitud(detalle="x" * 501).status_code, 400)
        self.assertEqual(self.crear_solicitud(detalle="x" * 500).status_code, 302)

    def test_el_error_conserva_lo_escrito(self):
        self.como_cliente()
        r = self.crear_solicitud(plan_id="", detalle="Mi detalle importante")
        self.assertIn("Mi detalle importante", r.get_data(as_text=True))

    def test_un_administrador_no_puede_crear_solicitudes(self):
        self.como_admin()
        r = self.crear_solicitud()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_la_solicitud_nueva_aparece_en_el_panel_del_administrador(self):
        self.como_cliente()
        self.crear_solicitud(detalle="Necesito más soporte")
        self.cambiar_a_admin()
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        self.assertIn("Necesito más soporte", html)
        self.assertIn("Lucas Salvarrey", html)
        self.assertIn("Pendiente", html)


class MisSolicitudesTest(SolicitudesBase):
    # --- US5: el cliente ve el estado de sus solicitudes ----------------------

    def test_exige_sesion(self):
        r = self.client.get("/solicitudes")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/solicitudes", r.headers["Location"])

    def test_sin_solicitudes_se_avisa(self):
        self.como_cliente()
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("Todavía no hiciste ninguna solicitud", html)

    def test_se_ve_la_solicitud_con_su_estado(self):
        self.como_cliente()
        self.insertar(detalle="Pedido pendiente", estado="pendiente")
        self.insertar(detalle="Pedido hecho", estado="realizado")
        self.insertar(detalle="Pedido anulado", estado="anulada")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        for texto in ("Pedido pendiente", "Pedido hecho", "Pedido anulado"):
            self.assertIn(texto, html)
        for estado in ("Pendiente", "Realizado", "Anulada"):
            self.assertIn(estado, html)

    def test_se_ve_el_nombre_del_plan_pedido(self):
        self.como_cliente()
        self.insertar(plan_id=3)
        self.assertIn("Plan Premium", self.client.get("/solicitudes").get_data(as_text=True))

    def test_no_se_ven_las_solicitudes_de_otro_cliente(self):
        self.como_cliente()
        self.insertar(cliente_id=1, detalle="PEDIDO-PROPIO")
        self.insertar(cliente_id=2, detalle="PEDIDO-AJENO")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("PEDIDO-PROPIO", html)
        self.assertNotIn("PEDIDO-AJENO", html)

    def test_las_mas_nuevas_van_primero(self):
        self.como_cliente()
        self.insertar(detalle="PRIMERA-VIEJA")
        self.insertar(detalle="SEGUNDA-NUEVA")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertLess(html.index("SEGUNDA-NUEVA"), html.index("PRIMERA-VIEJA"))

    def test_el_detalle_no_inyecta_html(self):
        self.como_cliente()
        self.insertar(detalle="<script>alert(1)</script>")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_solo_las_pendientes_tienen_boton_de_anular(self):
        self.como_cliente()
        self.insertar(estado="realizado")
        self.assertNotIn("Anular solicitud", self.client.get("/solicitudes").get_data(as_text=True))
        self.insertar(estado="pendiente")
        self.assertIn("Anular solicitud", self.client.get("/solicitudes").get_data(as_text=True))


class AnularSolicitudTest(SolicitudesBase):
    # --- US6: el cliente anula una solicitud pendiente ------------------------

    def test_exige_sesion(self):
        sid = self.insertar()
        r = self.client.post(f"/solicitudes/{sid}/anular")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_anular_una_pendiente(self):
        self.como_cliente()
        sid = self.insertar()
        r = self.client.post(f"/solicitudes/{sid}/anular")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "anulada")
        self.assertIn("modificado", self.store.solicitudes[sid])

    def test_se_avisa_al_anular(self):
        self.como_cliente()
        sid = self.insertar()
        self.client.post(f"/solicitudes/{sid}/anular")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("La solicitud se anuló", html)

    def test_una_realizada_no_se_puede_anular(self):
        self.como_cliente()
        sid = self.insertar(estado="realizado")
        self.client.post(f"/solicitudes/{sid}/anular")
        self.assertEqual(self.store.solicitudes[sid]["estado"], "realizado")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("Solo se pueden anular solicitudes pendientes", html)

    def test_una_anulada_no_se_puede_anular_de_nuevo(self):
        self.como_cliente()
        sid = self.insertar(estado="anulada")
        self.client.post(f"/solicitudes/{sid}/anular")
        self.assertEqual(self.store.solicitudes[sid]["estado"], "anulada")

    def test_no_se_puede_anular_la_de_otro_cliente(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=2)
        r = self.client.post(f"/solicitudes/{sid}/anular")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_solicitud_inexistente(self):
        self.como_cliente()
        self.assertEqual(self.client.post("/solicitudes/99/anular").status_code, 404)

    def test_anular_no_funciona_con_get(self):
        self.como_cliente()
        sid = self.insertar()
        self.assertEqual(self.client.get(f"/solicitudes/{sid}/anular").status_code, 405)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")


class PanelAdminTest(SolicitudesBase):
    # --- US4: el administrador pasa las solicitudes a «realizado» -------------

    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()
        self.poner_costo(2)  # PagoNet solo acepta facturar planes con costo

    def test_el_panel_exige_sesion(self):
        r = self.client.get("/admin/solicitudes")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/admin/solicitudes", r.headers["Location"])

    def test_un_cliente_no_entra_al_panel(self):
        self.como_cliente()
        self.assertEqual(self.client.get("/admin/solicitudes").status_code, 403)

    def test_el_admin_ve_las_solicitudes_de_todos_los_clientes(self):
        self.como_admin()
        self.store.clientes[1] = {
            "id": 1, "nombre": "Lucas Salvarrey", "dni": "45786322", "email": "lucas@ejemplo.com",
            "telefono": "+54 11 5555-1234", "plan_id": 1,
        }
        self.insertar(cliente_id=1, detalle="PEDIDO-DE-LUCAS")
        self.insertar(cliente_id=2, detalle="PEDIDO-DE-GALO")
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        for texto in ("PEDIDO-DE-LUCAS", "PEDIDO-DE-GALO", "Lucas Salvarrey", "Galo Roselli"):
            self.assertIn(texto, html)

    def test_sin_solicitudes_se_avisa(self):
        self.como_admin()
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        self.assertIn("Todavía no hay solicitudes", html)

    def test_las_pendientes_van_primero(self):
        self.como_admin()
        self.insertar(cliente_id=2, estado="realizado", detalle="YA-REALIZADA")
        self.insertar(cliente_id=2, estado="pendiente", detalle="TODAVIA-PENDIENTE")
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        self.assertLess(html.index("TODAVIA-PENDIENTE"), html.index("YA-REALIZADA"))

    def test_marcar_como_realizada(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        r = self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.assertEqual(r.status_code, 302)
        s = self.store.solicitudes[sid]
        self.assertEqual(s["estado"], "realizado")
        self.assertEqual(s["resuelto_por"], 1)
        self.assertIn("modificado", s)

    def test_el_cambio_queda_guardado_y_se_ve(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2, detalle="PEDIDO-DE-GALO")
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        self.assertIn("La solicitud quedó como realizada", html)
        self.assertIn("Realizado", html)
        self.assertNotIn("Marcar como realizada", html)

    def test_el_cliente_ve_su_solicitud_realizada(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1, detalle="PEDIDO-DE-LUCAS")
        self.cambiar_a_admin()
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.client.post("/logout")
        self.login("lucas@ejemplo.com", "clave-segura-1")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("Realizado", html)

    def test_solo_se_realizan_las_pendientes(self):
        self.como_admin()
        anulada = self.insertar(cliente_id=2, estado="anulada")
        hecha = self.insertar(cliente_id=2, estado="realizado")
        self.client.post(f"/admin/solicitudes/{anulada}/realizar")
        self.client.post(f"/admin/solicitudes/{hecha}/realizar")
        self.assertEqual(self.store.solicitudes[anulada]["estado"], "anulada")
        self.assertEqual(self.store.solicitudes[hecha]["estado"], "realizado")
        self.assertNotIn("resuelto_por", self.store.solicitudes[anulada])

    def test_un_cliente_no_puede_marcar_como_realizada(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        r = self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_sin_sesion_no_se_puede_realizar(self):
        sid = self.insertar(cliente_id=2)
        r = self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_solicitud_inexistente(self):
        self.como_admin()
        self.assertEqual(self.client.post("/admin/solicitudes/99/realizar").status_code, 404)

    def test_realizar_no_funciona_con_get(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.assertEqual(self.client.get(f"/admin/solicitudes/{sid}/realizar").status_code, 405)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")


class FacturacionTest(SolicitudesBase):
    """Al aprobar una solicitud se factura el plan nuevo en PagoNet (simulado)."""

    def setUp(self):
        super().setUp()
        self.poner_costo(2)  # el plan 3 queda sin costo a propósito

    def solicitud_de_lucas(self, plan_id=2):
        """Lucas (plan 1) pide `plan_id`; deja la sesión iniciada como administrador."""
        self.como_cliente()
        solicitud_id = self.insertar(cliente_id=1, plan_id=plan_id)
        self.cambiar_a_admin()
        return solicitud_id

    def realizar(self, solicitud_id):
        return self.client.post(f"/admin/solicitudes/{solicitud_id}/realizar")

    def test_si_el_cobro_se_acepta_el_cliente_cambia_de_plan(self):
        sid = self.solicitud_de_lucas()
        self.realizar(sid)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "realizado")
        self.assertEqual(self.store.clientes[1]["plan_id"], 2)

    def test_se_registra_una_factura_aprobada(self):
        sid = self.solicitud_de_lucas()
        self.realizar(sid)
        factura = self.store.facturas[self.store.solicitudes[sid]["factura_id"]]
        self.assertEqual(factura["estado"], "aprobado")
        self.assertEqual(factura["monto"], Decimal("9000.00"))
        self.assertEqual((factura["cliente_id"], factura["plan_id"]), (1, 2))
        self.assertEqual(factura["solicitud_id"], sid)

    def test_si_el_plan_no_tiene_costo_pagonet_rechaza(self):
        sid = self.solicitud_de_lucas(plan_id=3)
        self.realizar(sid)
        s = self.store.solicitudes[sid]
        self.assertEqual(s["estado"], "rechazada")
        self.assertIn("PagoNet rechazó la facturación", s["motivo"])
        self.assertIn("costo mensual", s["motivo"])
        self.assertEqual(self.store.facturas[s["factura_id"]]["estado"], "rechazado")

    def test_si_pagonet_rechaza_el_plan_del_cliente_no_cambia(self):
        sid = self.solicitud_de_lucas(plan_id=3)
        self.realizar(sid)
        self.assertEqual(self.store.clientes[1]["plan_id"], 1)

    def test_el_administrador_ve_por_que_se_rechazo(self):
        sid = self.solicitud_de_lucas(plan_id=3)
        self.realizar(sid)
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        self.assertIn("PagoNet rechazó la facturación", html)
        self.assertIn("Rechazada", html)

    def test_el_cliente_ve_el_motivo_del_rechazo(self):
        sid = self.solicitud_de_lucas(plan_id=3)
        self.realizar(sid)
        self.client.post("/logout")
        self.login("lucas@ejemplo.com", "clave-segura-1")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("Rechazada", html)
        self.assertIn("PagoNet rechazó la facturación", html)

    def test_una_solicitud_ya_resuelta_no_se_factura_dos_veces(self):
        sid = self.solicitud_de_lucas()
        self.realizar(sid)
        self.realizar(sid)
        self.assertEqual(len(self.store.facturas), 1)

    def test_una_solicitud_anulada_no_se_factura(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1, estado="anulada")
        self.cambiar_a_admin()
        self.realizar(sid)
        self.assertEqual(len(self.store.facturas), 0)
        self.assertEqual(self.store.clientes[1]["plan_id"], 1)


class RechazoTest(SolicitudesBase):
    """El administrador puede rechazar una solicitud pendiente, sin facturar."""

    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    def rechazar(self, solicitud_id):
        return self.client.post(f"/admin/solicitudes/{solicitud_id}/rechazar")

    def test_rechazar_una_pendiente(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        r = self.rechazar(sid)
        self.assertEqual(r.status_code, 302)
        s = self.store.solicitudes[sid]
        self.assertEqual(s["estado"], "rechazada")
        self.assertEqual(s["motivo"], "El administrador rechazó la solicitud.")
        self.assertEqual(s["resuelto_por"], 1)
        self.assertIn("modificado", s)

    def test_rechazar_no_factura_ni_cambia_el_plan(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.rechazar(sid)
        self.assertEqual(len(self.store.facturas), 0)
        self.assertEqual(self.store.clientes[2]["plan_id"], 1)

    def test_se_avisa_al_rechazar(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.rechazar(sid)
        html = self.client.get("/admin/solicitudes").get_data(as_text=True)
        self.assertIn("La solicitud quedó como rechazada", html)

    def test_solo_se_rechazan_las_pendientes(self):
        self.como_admin()
        for estado in ("realizado", "anulada", "rechazada"):
            sid = self.insertar(cliente_id=2, estado=estado)
            self.rechazar(sid)
            self.assertEqual(self.store.solicitudes[sid]["estado"], estado)
            self.assertNotIn("resuelto_por", self.store.solicitudes[sid])

    def test_solo_las_pendientes_tienen_boton_de_rechazar(self):
        self.como_admin()
        self.insertar(cliente_id=2, estado="realizado")
        self.assertNotIn("Rechazar", self.client.get("/admin/solicitudes").get_data(as_text=True))
        self.insertar(cliente_id=2, estado="pendiente")
        self.assertIn("Rechazar", self.client.get("/admin/solicitudes").get_data(as_text=True))

    def test_un_cliente_no_puede_rechazar(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        self.assertEqual(self.rechazar(sid).status_code, 403)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_sin_sesion_no_se_puede_rechazar(self):
        sid = self.insertar(cliente_id=2)
        self.assertEqual(self.rechazar(sid).status_code, 302)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_solicitud_inexistente(self):
        self.como_admin()
        self.assertEqual(self.rechazar(99).status_code, 404)

    def test_rechazar_no_funciona_con_get(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.assertEqual(self.client.get(f"/admin/solicitudes/{sid}/rechazar").status_code, 405)
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")

    def test_el_cliente_ve_su_solicitud_rechazada(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        self.cambiar_a_admin()
        self.rechazar(sid)
        self.client.post("/logout")
        self.login("lucas@ejemplo.com", "clave-segura-1")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("Rechazada", html)
        self.assertIn("El administrador rechazó la solicitud", html)


class AvisosTest(SolicitudesBase):
    """NotiSys (simulado) avisa al cliente cuando su solicitud cambia de estado."""

    def setUp(self):
        super().setUp()
        self.poner_costo(2)

    @property
    def notisys(self):
        return self.app.extensions["notisys"]

    def test_crear_una_solicitud_avisa_que_quedo_pendiente(self):
        self.como_cliente()
        self.crear_solicitud()
        self.assertEqual(len(self.notisys.enviadas), 1)
        aviso = self.notisys.enviadas[0]
        self.assertEqual((aviso["cliente_id"], aviso["solicitud_id"]), (1, 1))
        self.assertEqual(aviso["evento"], "pendiente")
        self.assertIn("quedó pendiente", aviso["mensaje"])

    def test_el_cliente_ve_sus_avisos(self):
        self.como_cliente()
        self.crear_solicitud()
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("Avisos", html)
        self.assertIn("Tu solicitud #1 quedó pendiente.", html)

    def test_sin_avisos_no_se_muestra_la_caja(self):
        self.como_cliente()
        self.assertNotIn("Avisos", self.client.get("/solicitudes").get_data(as_text=True))

    def test_realizar_avisa_con_el_plan_nuevo(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1, plan_id=2)
        self.cambiar_a_admin()
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "realizado")
        self.assertIn("fue realizada", aviso["mensaje"])
        self.assertIn("Plan Estándar", aviso["mensaje"])

    def test_el_rechazo_de_pagonet_avisa_con_el_motivo(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1, plan_id=3)  # el plan 3 no tiene costo
        self.cambiar_a_admin()
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "rechazada")
        self.assertIn("PagoNet rechazó la facturación", aviso["mensaje"])

    def test_rechazar_avisa(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        self.cambiar_a_admin()
        self.client.post(f"/admin/solicitudes/{sid}/rechazar")
        self.assertEqual(self.notisys.enviadas[-1]["evento"], "rechazada")

    def test_anular_no_envia_aviso(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        self.client.post(f"/solicitudes/{sid}/anular")
        self.assertEqual(len(self.notisys.enviadas), 0)

    def test_no_se_ven_los_avisos_de_otro_cliente(self):
        self.como_cliente()
        self.notisys.enviar(2, 5, "pendiente", "AVISO-AJENO")
        self.notisys.enviar(1, 6, "pendiente", "AVISO-PROPIO")
        html = self.client.get("/solicitudes").get_data(as_text=True)
        self.assertIn("AVISO-PROPIO", html)
        self.assertNotIn("AVISO-AJENO", html)


class MenuYMiCuentaTest(SolicitudesBase):
    def test_menu_del_cliente_tiene_solicitudes(self):
        self.como_cliente()
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn('href="/solicitudes"', html)

    def test_menu_del_admin_tiene_solicitudes(self):
        self.como_admin()
        html = self.client.get("/planes").get_data(as_text=True)
        self.assertIn('href="/admin/solicitudes"', html)

    def test_mi_cuenta_sin_datos_del_plan_dice_a_definir(self):
        # US2: los planes precargados nacen sin descripción, costo ni SLA.
        self.como_cliente()
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn("Plan Básico", html)
        self.assertIn("A definir", html)

    def test_mi_cuenta_muestra_descripcion_costo_y_sla_del_plan(self):
        # US2: el cliente ve qué tiene contratado.
        self.como_cliente()
        self.store.planes[1].update(
            descripcion="Soporte por mail", costo_mensual=Decimal("9000.00"),
            sla_horas=48,
        )
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn("Soporte por mail", html)
        self.assertIn("9.000", html)
        self.assertIn("48 h", html)


class DatosDemoSolicitudTest(unittest.TestCase):
    def test_se_carga_una_solicitud_pendiente_de_ejemplo(self):
        app = create_app({"TESTING": True, "CARGAR_DATOS": True})
        store = app.extensions["store"]
        self.assertEqual(len(store.solicitudes), 1)
        s = store.solicitudes[1]
        self.assertEqual(s["cliente_id"], 1)
        self.assertEqual(s["estado"], "pendiente")
        self.assertIn(s["plan_id"], store.planes)

    def test_basico_y_estandar_de_ejemplo_traen_costo_y_sla(self):
        app = create_app({"TESTING": True, "CARGAR_DATOS": True})
        planes = app.extensions["store"].planes
        for plan_id in (1, 2):
            self.assertTrue(planes[plan_id]["costo_mensual"] > 0)
            self.assertTrue(planes[plan_id]["sla_horas"] > 0)
            self.assertTrue(planes[plan_id]["descripcion"])

    def test_el_premium_de_ejemplo_queda_sin_costo(self):
        # A propósito: es el plan que muestra el rechazo de PagoNet.
        app = create_app({"TESTING": True, "CARGAR_DATOS": True})
        premium = app.extensions["store"].planes[3]
        self.assertIsNone(premium["costo_mensual"])
        self.assertIsNone(premium["sla_horas"])

    def test_la_demo_muestra_el_rechazo_de_pagonet_con_el_premium(self):
        app = create_app({"TESTING": True, "CARGAR_DATOS": True})
        client = app.test_client()
        store = app.extensions["store"]
        client.post("/login", data={"email": "lucas@ejemplo.com", "password": "clave-segura-2"})
        client.post("/solicitudes/nueva", data={"plan_id": "3", "detalle": "Quiero el Premium"})
        client.post("/logout")
        client.post("/login", data={
            "email": app.config["ADMIN_EMAIL"], "password": app.config["ADMIN_PASSWORD"]})
        client.post("/admin/solicitudes/2/realizar")
        self.assertEqual(store.solicitudes[2]["estado"], "rechazada")
        self.assertIn("costo mensual", store.solicitudes[2]["motivo"])
        self.assertEqual(store.clientes[1]["plan_id"], 1)

    def test_la_demo_funciona_de_punta_a_punta(self):
        # Es el guion del README: el administrador aprueba la solicitud de Lucas.
        app = create_app({"TESTING": True, "CARGAR_DATOS": True})
        client = app.test_client()
        store = app.extensions["store"]
        client.post("/login", data={
            "email": app.config["ADMIN_EMAIL"], "password": app.config["ADMIN_PASSWORD"]})
        r = client.post("/admin/solicitudes/1/realizar")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(store.solicitudes[1]["estado"], "realizado")
        self.assertEqual(store.clientes[1]["plan_id"], 2)
        self.assertEqual(store.facturas[1]["estado"], "aprobado")

    def test_sin_datos_de_ejemplo_no_hay_solicitudes(self):
        app = create_app({"TESTING": True, "CARGAR_DATOS": False})
        self.assertEqual(len(app.extensions["store"].solicitudes), 0)


if __name__ == "__main__":
    unittest.main()
