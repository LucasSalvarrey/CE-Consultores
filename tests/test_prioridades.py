"""HU-19: asignar y filtrar por prioridades las solicitudes de los clientes."""
from ayudas_gestion import GestionBase


class AsignarPrioridadTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    def prioridad(self, solicitud_id, valor, **extra):
        return self.client.post(
            f"/admin/solicitudes/{solicitud_id}/prioridad", data={"prioridad": valor, **extra}
        )

    def test_una_solicitud_nueva_nace_con_prioridad_media(self):
        self.como_cliente()
        self.crear_solicitud()
        self.assertEqual(self.store.solicitudes[1]["prioridad"], "media")

    def test_el_administrador_asigna_la_prioridad(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        r = self.prioridad(sid, "alta")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.store.solicitudes[sid]["prioridad"], "alta")
        self.assertIn("modificado", self.store.solicitudes[sid])

    def test_se_puede_pasar_por_las_tres_prioridades(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        for valor in ("alta", "baja", "media"):
            self.prioridad(sid, valor)
            self.assertEqual(self.store.solicitudes[sid]["prioridad"], valor)

    def test_el_panel_confirma_el_cambio(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.prioridad(sid, "alta")
        self.assertIn("quedó con prioridad alta", self.html("/admin/solicitudes"))

    def test_una_prioridad_invalida_no_cambia_nada(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        for valor in ("urgente", "", "ALTA"):
            self.prioridad(sid, valor)
        self.assertEqual(self.store.solicitudes[sid]["prioridad"], "media")
        self.assertIn("Elegí una prioridad válida", self.html("/admin/solicitudes"))

    def test_asignar_la_misma_prioridad_no_registra_un_cambio(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.prioridad(sid, "media")
        self.assertEqual(len(self.store.registro), 0)
        self.assertIn("ya tenía esa prioridad", self.html("/admin/solicitudes"))

    def test_solo_se_cambia_la_prioridad_de_las_pendientes(self):
        self.como_admin()
        for estado in ("realizado", "rechazada", "anulada"):
            sid = self.insertar(cliente_id=2, estado=estado)
            self.prioridad(sid, "alta")
            self.assertEqual(self.store.solicitudes[sid]["prioridad"], "media")
        self.assertIn("Solo se puede cambiar la prioridad", self.html("/admin/solicitudes"))

    def test_el_cambio_queda_en_el_registro(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.prioridad(sid, "alta")
        entrada = self.store.registro[-1]
        self.assertEqual(entrada["accion"], "Prioridad asignada")
        self.assertEqual(entrada["ref"], sid)
        self.assertIn("media → alta", entrada["detalle"])

    def test_un_cliente_no_puede_asignar_prioridades(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        self.assertEqual(self.prioridad(sid, "alta").status_code, 403)
        self.assertEqual(self.store.solicitudes[sid]["prioridad"], "media")

    def test_sin_sesion_no_se_puede_asignar(self):
        sid = self.insertar(cliente_id=2)
        self.assertEqual(self.prioridad(sid, "alta").status_code, 302)
        self.assertEqual(self.store.solicitudes[sid]["prioridad"], "media")

    def test_solicitud_inexistente(self):
        self.como_admin()
        self.assertEqual(self.prioridad(99, "alta").status_code, 404)

    def test_asignar_no_funciona_con_get(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.assertEqual(self.client.get(f"/admin/solicitudes/{sid}/prioridad").status_code, 405)

    def test_despues_de_asignar_se_vuelve_al_filtro_donde_se_estaba(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        r = self.prioridad(sid, "alta", volver="/admin/solicitudes?estado=pendiente")
        self.assertTrue(r.headers["Location"].endswith("/admin/solicitudes?estado=pendiente"))

    def test_un_destino_externo_se_ignora(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        for destino in ("http://malicioso.com", "//malicioso.com", "\\\\malicioso"):
            r = self.prioridad(sid, "alta", volver=destino)
            self.assertTrue(r.headers["Location"].endswith("/admin/solicitudes"), destino)


class FiltrarYOrdenarTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()
        self.como_admin()

    def cargar(self):
        """Cuatro solicitudes con detalles fáciles de buscar."""
        self.insertar(cliente_id=2, prioridad="baja", detalle="X-BAJA")
        self.insertar(cliente_id=2, prioridad="alta", detalle="X-ALTA")
        self.insertar(cliente_id=2, prioridad="media", detalle="X-MEDIA")
        self.insertar(cliente_id=2, prioridad="alta", estado="realizado", detalle="X-ALTA-REALIZADA")

    def test_las_pendientes_se_ordenan_por_prioridad(self):
        self.cargar()
        html = self.html("/admin/solicitudes")
        self.assertLess(html.index("X-ALTA<"), html.index("X-MEDIA"))
        self.assertLess(html.index("X-MEDIA"), html.index("X-BAJA"))

    def test_las_pendientes_van_antes_que_las_resueltas_aunque_tengan_menos_prioridad(self):
        self.cargar()
        html = self.html("/admin/solicitudes")
        self.assertLess(html.index("X-BAJA"), html.index("X-ALTA-REALIZADA"))

    def test_a_igual_prioridad_va_primero_la_mas_vieja(self):
        self.insertar(cliente_id=2, detalle="X-PRIMERA")
        self.insertar(cliente_id=2, detalle="X-SEGUNDA")
        html = self.html("/admin/solicitudes")
        self.assertLess(html.index("X-PRIMERA"), html.index("X-SEGUNDA"))

    def test_filtrar_por_prioridad(self):
        self.cargar()
        html = self.html("/admin/solicitudes?prioridad=alta")
        self.assertIn("X-ALTA<", html)
        self.assertIn("X-ALTA-REALIZADA", html)
        self.assertNotIn("X-MEDIA", html)
        self.assertNotIn("X-BAJA", html)

    def test_filtrar_por_estado(self):
        self.cargar()
        html = self.html("/admin/solicitudes?estado=realizado")
        self.assertIn("X-ALTA-REALIZADA", html)
        self.assertNotIn("X-MEDIA", html)

    def test_filtrar_por_estado_y_prioridad_a_la_vez(self):
        self.cargar()
        html = self.html("/admin/solicitudes?estado=pendiente&prioridad=alta")
        self.assertIn("X-ALTA<", html)
        self.assertNotIn("X-ALTA-REALIZADA", html)
        self.assertNotIn("X-MEDIA", html)

    def test_un_filtro_invalido_se_ignora(self):
        self.cargar()
        html = self.html("/admin/solicitudes?estado=inventado&prioridad=urgente")
        for detalle in ("X-BAJA", "X-ALTA<", "X-MEDIA", "X-ALTA-REALIZADA"):
            self.assertIn(detalle, html)

    def test_un_filtro_sin_resultados_lo_explica(self):
        self.cargar()
        html = self.html("/admin/solicitudes?estado=anulada")
        self.assertIn("No hay solicitudes con esos filtros", html)
        self.assertNotIn("Todavía no hay solicitudes", html)

    def test_sin_solicitudes_se_informa(self):
        self.assertIn("Todavía no hay solicitudes", self.html("/admin/solicitudes"))

    def test_los_filtros_muestran_cuantas_hay_de_cada_estado(self):
        self.cargar()
        html = self.html("/admin/solicitudes")
        self.assertIn("Pendiente <small>3</small>", html)
        self.assertIn("Realizado <small>1</small>", html)
        self.assertIn("Todas <small>4</small>", html)

    def test_el_filtro_activo_queda_marcado(self):
        self.cargar()
        html = self.html("/admin/solicitudes?prioridad=alta")
        self.assertIn('class="chip activo"', html)

    def test_cada_solicitud_muestra_su_prioridad(self):
        self.cargar()
        html = self.html("/admin/solicitudes")
        self.assertIn("Prioridad alta", html)
        self.assertIn("Prioridad media", html)
        self.assertIn("Prioridad baja", html)

    def test_solo_las_pendientes_tienen_selector_de_prioridad(self):
        self.insertar(cliente_id=2, estado="realizado")
        self.assertNotIn('name="prioridad"', self.html("/admin/solicitudes"))
        self.insertar(cliente_id=2)
        self.assertIn('name="prioridad"', self.html("/admin/solicitudes"))

    def test_una_solicitud_sin_prioridad_guardada_se_muestra_como_media(self):
        sid = self.insertar(cliente_id=2)
        del self.store.solicitudes[sid]["prioridad"]
        self.assertIn("Prioridad media", self.html("/admin/solicitudes"))

    def test_las_solicitudes_urgentes_generan_una_alerta(self):
        self.insertar(cliente_id=2, prioridad="alta")
        self.assertIn("1 solicitud de prioridad alta pendiente", self.html("/admin/solicitudes"))
        self.insertar(cliente_id=2, prioridad="alta")
        self.assertIn("2 solicitudes de prioridad alta pendientes", self.html("/admin/solicitudes"))

    def test_las_solicitudes_urgentes_resueltas_no_generan_alerta(self):
        self.insertar(cliente_id=2, prioridad="alta", estado="realizado")
        self.assertNotIn("de prioridad alta pendiente", self.html("/admin/solicitudes"))

    def test_el_panel_exige_ser_administrador(self):
        self.client.post("/logout")
        self.assertEqual(self.client.get("/admin/solicitudes?prioridad=alta").status_code, 302)
        self.como_cliente()
        self.assertEqual(self.client.get("/admin/solicitudes?prioridad=alta").status_code, 403)
