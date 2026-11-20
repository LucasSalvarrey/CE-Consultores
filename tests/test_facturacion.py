"""HU-21 y HU-22: facturar por PagoNet (simulado) y gestionar las fallas con una devolución."""
from decimal import Decimal

from ayudas_gestion import GestionBase


class FacturarTest(GestionBase):
    """HU-21: el administrador cobra una factura con un botón."""

    def setUp(self):
        super().setUp()
        self.como_cliente()
        self.sid = self.insertar(cliente_id=1, estado="realizado")
        self.fid = self.insertar_factura(solicitud_id=self.sid)
        self.cambiar_a_admin()

    def test_facturar_una_pendiente_la_deja_pagada(self):
        r = self.facturar(self.fid)
        self.assertEqual(r.status_code, 302)
        factura = self.store.facturas[self.fid]
        self.assertEqual(factura["estado"], "pagada")
        self.assertEqual(factura["intentos"], 1)
        self.assertIn("modificado", factura)

    def test_se_confirma_el_cobro(self):
        self.facturar(self.fid)
        self.assertIn("se cobró correctamente en PagoNet", self.html("/admin/facturas"))

    def test_se_avisa_al_cliente_del_pago(self):
        self.facturar(self.fid)
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "factura_pagada")
        self.assertEqual(aviso["cliente_id"], 1)
        self.assertIn("$ 9.000,00", aviso["mensaje"])

    def test_queda_en_el_registro_de_cambios(self):
        self.facturar(self.fid)
        entrada = self.store.registro[-1]
        self.assertEqual((entrada["accion"], entrada["entidad"], entrada["ref"]), ("Factura cobrada", "factura", self.fid))

    def test_una_factura_pagada_no_se_vuelve_a_cobrar(self):
        self.facturar(self.fid)
        self.facturar(self.fid)
        self.assertEqual(self.store.facturas[self.fid]["intentos"], 1)
        self.assertIn("Solo se pueden facturar facturas pendientes o con falla", self.html("/admin/facturas"))

    def test_una_factura_devuelta_no_se_cobra(self):
        fid = self.insertar_factura(estado="devuelta")
        self.facturar(fid)
        self.assertEqual(self.store.facturas[fid]["estado"], "devuelta")

    def test_una_factura_sin_monto_falla(self):
        fid = self.insertar_factura(monto=None)
        self.facturar(fid)
        factura = self.store.facturas[fid]
        self.assertEqual(factura["estado"], "fallida")
        self.assertIn("costo mensual", factura["motivo_falla"])

    def test_el_cliente_ve_su_factura_en_sus_solicitudes(self):
        self.store.solicitudes[self.sid]["factura_id"] = self.fid
        self.facturar(self.fid)
        self.cambiar_a_cliente()
        html = self.html("/solicitudes")
        self.assertIn(f"Factura #{self.fid}", html)
        self.assertIn("$ 9.000,00", html)
        self.assertIn("Pagada", html)


class FallaPagoNetTest(GestionBase):
    """HU-22: si PagoNet falla hay una alerta y el administrador la gestiona."""

    def setUp(self):
        super().setUp()
        self.como_cliente()
        self.sid = self.insertar(cliente_id=1, estado="realizado")
        self.fid = self.insertar_factura(solicitud_id=self.sid)
        self.cambiar_a_admin()

    def test_simular_una_falla_deja_la_factura_fallida(self):
        self.facturar(self.fid, falla=True)
        factura = self.store.facturas[self.fid]
        self.assertEqual(factura["estado"], "fallida")
        self.assertIn("Falla de comunicación con PagoNet", factura["motivo_falla"])
        self.assertEqual(factura["intentos"], 1)

    def test_la_falla_no_se_avisa_al_cliente_como_pago(self):
        self.facturar(self.fid, falla=True)
        self.assertEqual(len(self.notisys.enviadas), 0)

    def test_aparece_una_alerta_en_el_panel_del_administrador(self):
        self.facturar(self.fid, falla=True)
        html = self.html("/admin/solicitudes")
        self.assertIn("1 factura con falla en PagoNet", html)
        self.assertIn("realizá la devolución", html)

    def test_la_alerta_lleva_al_listado_de_fallidas(self):
        self.facturar(self.fid, falla=True)
        self.assertIn('href="/admin/facturas?estado=fallida"', self.html("/admin"))

    def test_la_alerta_cuenta_varias_facturas(self):
        self.facturar(self.fid, falla=True)
        otra = self.insertar_factura(solicitud_id=self.sid)
        self.facturar(otra, falla=True)
        self.assertIn("2 facturas con falla en PagoNet", self.html("/admin"))

    def test_la_falla_queda_en_el_registro(self):
        self.facturar(self.fid, falla=True)
        entrada = self.store.registro[-1]
        self.assertEqual(entrada["accion"], "Falla en PagoNet")
        self.assertIn("Intento 1", entrada["detalle"])

    def test_el_listado_muestra_el_motivo_y_las_opciones(self):
        self.facturar(self.fid, falla=True)
        html = self.html("/admin/facturas")
        self.assertIn("Falla de comunicación con PagoNet (simulada)", html)
        self.assertIn("Reintentar cobro", html)
        self.assertIn("Realizar devolución", html)

    def test_reintentar_y_que_funcione_la_deja_pagada(self):
        self.facturar(self.fid, falla=True)
        self.facturar(self.fid)
        factura = self.store.facturas[self.fid]
        self.assertEqual(factura["estado"], "pagada")
        self.assertEqual(factura["intentos"], 2)
        self.assertIsNone(factura["motivo_falla"])

    def test_reintentar_y_que_falle_otra_vez_la_deja_fallida(self):
        self.facturar(self.fid, falla=True)
        self.facturar(self.fid, falla=True)
        self.assertEqual(self.store.facturas[self.fid]["estado"], "fallida")
        self.assertEqual(self.store.facturas[self.fid]["intentos"], 2)

    def test_un_reintento_exitoso_avisa_y_apaga_la_alerta(self):
        self.facturar(self.fid, falla=True)
        self.facturar(self.fid)
        self.assertEqual(self.notisys.enviadas[-1]["evento"], "factura_pagada")
        self.assertNotIn("con falla en PagoNet: reintentá", self.html("/admin"))

    def test_una_pendiente_sin_falla_no_genera_alerta(self):
        self.assertNotIn("con falla en PagoNet: reintentá", self.html("/admin"))


class DevolucionTest(GestionBase):
    """HU-22: el administrador realiza una devolución al cliente por la falla."""

    def setUp(self):
        super().setUp()
        self.como_cliente()
        self.sid = self.insertar(cliente_id=1, estado="realizado")
        self.fid = self.insertar_factura(solicitud_id=self.sid)
        self.cambiar_a_admin()
        self.facturar(self.fid, falla=True)

    def test_devolver_una_factura_fallida(self):
        r = self.devolver(self.fid)
        self.assertEqual(r.status_code, 302)
        factura = self.store.facturas[self.fid]
        self.assertEqual(factura["estado"], "devuelta")
        self.assertEqual(factura["devolucion_id"], 1)

    def test_se_registra_la_devolucion(self):
        self.devolver(self.fid)
        devolucion = self.store.devoluciones[1]
        self.assertEqual(devolucion["factura_id"], self.fid)
        self.assertEqual(devolucion["cliente_id"], 1)
        self.assertEqual(devolucion["monto"], Decimal("9000.00"))
        self.assertEqual(devolucion["admin_id"], 1)
        self.assertIn("fecha", devolucion)

    def test_se_avisa_al_cliente_de_la_devolucion(self):
        self.devolver(self.fid)
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "factura_devuelta")
        self.assertEqual(aviso["cliente_id"], 1)
        self.assertIn("devolución de $ 9.000,00", aviso["mensaje"])

    def test_el_cliente_lo_ve_en_sus_avisos(self):
        self.devolver(self.fid)
        self.cambiar_a_cliente()
        self.assertIn("Realizamos la devolución", self.html("/avisos"))

    def test_la_alerta_desaparece_al_devolver(self):
        self.devolver(self.fid)
        self.assertNotIn("con falla en PagoNet: reintentá", self.html("/admin"))

    def test_el_listado_muestra_la_devolucion(self):
        self.devolver(self.fid)
        html = self.html("/admin/facturas")
        self.assertIn("Devuelta", html)
        self.assertIn("Devolución #1", html)
        self.assertNotIn("Realizar devolución", html)

    def test_la_devolucion_queda_en_el_registro(self):
        self.devolver(self.fid)
        entrada = self.store.registro[-1]
        self.assertEqual(entrada["accion"], "Devolución realizada")
        self.assertIn("$ 9.000,00", entrada["detalle"])

    def test_no_se_devuelve_dos_veces(self):
        self.devolver(self.fid)
        self.devolver(self.fid)
        self.assertEqual(len(self.store.devoluciones), 1)

    def test_solo_se_devuelve_una_factura_con_falla(self):
        pendiente = self.insertar_factura(estado="pendiente")
        pagada = self.insertar_factura(estado="pagada")
        for fid in (pendiente, pagada):
            self.devolver(fid)
        self.assertEqual(len(self.store.devoluciones), 0)
        self.assertEqual(self.store.facturas[pendiente]["estado"], "pendiente")
        self.assertEqual(self.store.facturas[pagada]["estado"], "pagada")
        self.assertIn("Solo se puede devolver", self.html("/admin/facturas"))

    def test_una_factura_devuelta_ya_no_se_puede_reintentar(self):
        self.devolver(self.fid)
        self.facturar(self.fid)
        self.assertEqual(self.store.facturas[self.fid]["estado"], "devuelta")


class AccesoYListadoTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    def test_el_listado_exige_sesion(self):
        r = self.client.get("/admin/facturas")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/admin/facturas", r.headers["Location"])

    def test_un_cliente_no_ve_la_facturacion(self):
        self.como_cliente()
        self.assertEqual(self.client.get("/admin/facturas").status_code, 403)

    def test_un_cliente_no_puede_facturar_ni_devolver(self):
        self.como_cliente()
        fid = self.insertar_factura(estado="fallida")
        self.assertEqual(self.facturar(fid).status_code, 403)
        self.assertEqual(self.devolver(fid).status_code, 403)
        self.assertEqual(self.store.facturas[fid]["estado"], "fallida")

    def test_sin_sesion_no_se_puede_facturar_ni_devolver(self):
        fid = self.insertar_factura()
        self.assertEqual(self.facturar(fid).status_code, 302)
        self.assertEqual(self.devolver(fid).status_code, 302)
        self.assertEqual(self.store.facturas[fid]["estado"], "pendiente")

    def test_factura_inexistente(self):
        self.como_admin()
        self.assertEqual(self.facturar(99).status_code, 404)
        self.assertEqual(self.devolver(99).status_code, 404)

    def test_facturar_y_devolver_no_funcionan_con_get(self):
        self.como_admin()
        fid = self.insertar_factura()
        self.assertEqual(self.client.get(f"/admin/facturas/{fid}/facturar").status_code, 405)
        self.assertEqual(self.client.get(f"/admin/facturas/{fid}/devolver").status_code, 405)

    def test_sin_facturas_se_informa(self):
        self.como_admin()
        self.assertIn("Todavía no hay facturas", self.html("/admin/facturas"))

    def test_las_facturas_con_falla_van_primero(self):
        self.como_admin()
        self.insertar_factura(estado="pagada", cliente_id=2, monto="1111.00")
        self.insertar_factura(estado="pendiente", cliente_id=2, monto="2222.00")
        self.insertar_factura(estado="fallida", cliente_id=2, monto="3333.00")
        html = self.html("/admin/facturas")
        self.assertLess(html.index("3.333,00"), html.index("2.222,00"))
        self.assertLess(html.index("2.222,00"), html.index("1.111,00"))

    def test_filtrar_por_estado(self):
        self.como_admin()
        self.insertar_factura(estado="pagada", cliente_id=2, monto="1111.00")
        self.insertar_factura(estado="fallida", cliente_id=2, monto="3333.00")
        html = self.html("/admin/facturas?estado=fallida")
        self.assertIn("3.333,00", html)
        self.assertNotIn("1.111,00", html)

    def test_un_estado_invalido_se_ignora(self):
        self.como_admin()
        self.insertar_factura(estado="pagada", cliente_id=2, monto="1111.00")
        self.assertIn("1.111,00", self.html("/admin/facturas?estado=inventado"))

    def test_un_filtro_sin_resultados_lo_explica(self):
        self.como_admin()
        self.insertar_factura(estado="pagada", cliente_id=2)
        self.assertIn("No hay facturas con ese estado", self.html("/admin/facturas?estado=devuelta"))

    def test_los_filtros_muestran_las_cantidades(self):
        self.como_admin()
        self.insertar_factura(estado="pagada", cliente_id=2)
        self.insertar_factura(estado="pagada", cliente_id=2)
        self.insertar_factura(estado="fallida", cliente_id=2)
        html = self.html("/admin/facturas")
        self.assertIn("Pagadas <small>2</small>", html)
        self.assertIn("Con falla <small>1</small>", html)
        self.assertIn("Todas <small>3</small>", html)

    def test_se_vuelve_al_filtro_donde_se_estaba(self):
        self.como_admin()
        fid = self.insertar_factura(cliente_id=2)
        r = self.client.post(f"/admin/facturas/{fid}/facturar", data={"volver": "/admin/facturas?estado=pendiente"})
        self.assertTrue(r.headers["Location"].endswith("/admin/facturas?estado=pendiente"))

    def test_un_destino_externo_se_ignora(self):
        self.como_admin()
        fid = self.insertar_factura(cliente_id=2)
        r = self.client.post(f"/admin/facturas/{fid}/facturar", data={"volver": "http://malicioso.com"})
        self.assertTrue(r.headers["Location"].endswith("/admin/facturas"))

    def test_el_panel_de_solicitudes_ofrece_cobrar_una_factura_pendiente(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2, estado="realizado")
        fid = self.insertar_factura(cliente_id=2, solicitud_id=sid)
        self.store.solicitudes[sid]["factura_id"] = fid
        html = self.html("/admin/solicitudes")
        self.assertIn("Facturar en PagoNet", html)
        self.assertIn("Simular falla", html)
        self.client.post(f"/admin/facturas/{fid}/facturar", data={"volver": "/admin/solicitudes"})
        self.assertNotIn("Facturar en PagoNet", self.html("/admin/solicitudes"))
