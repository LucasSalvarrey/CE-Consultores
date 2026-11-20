"""HU-24 a HU-31: reclamos de los clientes (ingreso, duplicado, respuesta, estado y avisos)."""
from ayudas_gestion import GestionBase


class IngresarReclamoTest(GestionBase):
    """HU-24: el cliente ingresa un reclamo."""

    def test_el_formulario_exige_sesion(self):
        r = self.client.get("/reclamos/nuevo")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/reclamos/nuevo", r.headers["Location"])

    def test_el_formulario_ofrece_los_canales(self):
        self.como_cliente()
        html = self.html("/reclamos/nuevo")
        for canal in ("Web", "WhatsApp", "Teléfono"):
            self.assertIn(canal, html)

    def test_ingresar_un_reclamo_lo_deja_pendiente(self):
        self.como_cliente()
        r = self.crear_reclamo()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/reclamos/1"))
        reclamo = self.store.reclamos[1]
        self.assertEqual(reclamo["estado"], "pendiente")
        self.assertEqual(reclamo["cliente_id"], 1)
        self.assertEqual(reclamo["asunto"], "Cobro duplicado")
        self.assertEqual(reclamo["canal"], "web")
        self.assertEqual(reclamo["reiteraciones"], 0)

    def test_el_detalle_es_el_primer_mensaje_de_la_conversacion(self):
        self.como_cliente()
        self.crear_reclamo(detalle="Me cobraron dos veces.")
        mensajes = self.store.reclamos[1]["mensajes"]
        self.assertEqual(len(mensajes), 1)
        self.assertEqual(mensajes[0]["autor"], "cliente")
        self.assertEqual(mensajes[0]["texto"], "Me cobraron dos veces.")

    def test_se_confirma_la_recepcion_con_el_plazo(self):
        self.como_cliente()
        self.crear_reclamo()
        html = self.html("/reclamos/1")
        self.assertIn("Recibimos tu reclamo #1", html)
        self.assertIn("dentro de las 48 h", html)

    def test_el_asunto_se_limpia_de_espacios(self):
        self.como_cliente()
        self.crear_reclamo(asunto="   Cobro    duplicado  ")
        self.assertEqual(self.store.reclamos[1]["asunto"], "Cobro duplicado")

    def test_el_asunto_es_obligatorio(self):
        self.como_cliente()
        r = self.crear_reclamo(asunto="   ")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ingresá el asunto del reclamo", r.get_data(as_text=True))
        self.assertEqual(len(self.store.reclamos), 0)

    def test_el_asunto_tiene_un_maximo(self):
        self.como_cliente()
        self.assertEqual(self.crear_reclamo(asunto="a" * 101).status_code, 400)
        self.assertEqual(self.crear_reclamo(asunto="a" * 100).status_code, 302)

    def test_el_detalle_es_obligatorio_y_tiene_un_maximo(self):
        self.como_cliente()
        self.assertEqual(self.crear_reclamo(detalle="").status_code, 400)
        self.assertEqual(self.crear_reclamo(detalle="x" * 1001).status_code, 400)
        self.assertEqual(len(self.store.reclamos), 0)

    def test_el_canal_es_obligatorio_y_tiene_que_existir(self):
        self.como_cliente()
        self.assertEqual(self.crear_reclamo(canal="").status_code, 400)
        r = self.crear_reclamo(canal="paloma")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Elegí por qué canal", r.get_data(as_text=True))

    def test_un_error_conserva_lo_escrito(self):
        self.como_cliente()
        r = self.crear_reclamo(asunto="", detalle="Mi detalle importante")
        self.assertIn("Mi detalle importante", r.get_data(as_text=True))

    def test_un_administrador_no_puede_ingresar_reclamos(self):
        self.como_admin()
        self.assertEqual(self.crear_reclamo().status_code, 302)
        self.assertEqual(len(self.store.reclamos), 0)

    def test_el_reclamo_usa_el_sla_del_plan_del_cliente(self):
        self.como_cliente()
        self.poner_costo(1, sla_horas=24)
        self.crear_reclamo()
        self.assertEqual(self.store.reclamos[1]["sla_horas"], 24)

    def test_sin_sla_en_el_plan_se_usan_48_horas(self):
        self.como_cliente()
        self.crear_reclamo()
        self.assertEqual(self.store.reclamos[1]["sla_horas"], 48)

    def test_un_cliente_sin_plan_tambien_puede_reclamar(self):
        self.como_cliente()
        self.store.clientes[1]["plan_id"] = None
        self.assertEqual(self.crear_reclamo().status_code, 302)
        self.assertEqual(self.store.reclamos[1]["sla_horas"], 48)

    def test_queda_en_el_registro_de_cambios(self):
        self.como_cliente()
        self.crear_reclamo()
        entrada = self.store.registro[-1]
        self.assertEqual((entrada["accion"], entrada["entidad"], entrada["ref"]), ("Reclamo ingresado", "reclamo", 1))
        self.assertIn("Cobro duplicado", entrada["detalle"])


class ReclamoDuplicadoTest(GestionBase):
    """HU-28: si ya hay un reclamo abierto sobre el mismo asunto, no se crea otro."""

    def setUp(self):
        super().setUp()
        self.como_cliente()
        self.agregar_cliente_ajeno()

    def test_el_mismo_asunto_no_crea_otro_reclamo(self):
        self.crear_reclamo()
        r = self.crear_reclamo(detalle="Sigo esperando una respuesta.")
        self.assertEqual(len(self.store.reclamos), 1)
        self.assertTrue(r.headers["Location"].endswith("/reclamos/1"))

    def test_se_suma_el_mensaje_al_reclamo_existente(self):
        self.crear_reclamo()
        self.crear_reclamo(detalle="Sigo esperando una respuesta.")
        mensajes = self.store.reclamos[1]["mensajes"]
        self.assertEqual(len(mensajes), 2)
        self.assertEqual(mensajes[1]["texto"], "Sigo esperando una respuesta.")

    def test_se_cuenta_la_reiteracion(self):
        self.crear_reclamo()
        self.crear_reclamo()
        self.crear_reclamo()
        self.assertEqual(self.store.reclamos[1]["reiteraciones"], 2)

    def test_se_alerta_al_cliente(self):
        self.crear_reclamo()
        self.crear_reclamo()
        html = self.html("/reclamos/1")
        self.assertIn("Ya tenés abierto el reclamo #1", html)
        self.assertIn("No creamos uno nuevo", html)
        self.assertIn('class="aviso aviso-alerta"', html)

    def test_se_avisa_por_notisys(self):
        self.crear_reclamo()
        self.crear_reclamo()
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "reclamo_reiterado")
        self.assertEqual(aviso["enlace"], "/reclamos/1")

    def test_mayusculas_tildes_y_espacios_no_importan(self):
        self.crear_reclamo(asunto="Cobro duplicado")
        self.crear_reclamo(asunto="  COBRO    duplicádo ")
        self.assertEqual(len(self.store.reclamos), 1)

    def test_un_asunto_distinto_crea_otro_reclamo(self):
        self.crear_reclamo()
        self.crear_reclamo(asunto="No puedo ingresar")
        self.assertEqual(len(self.store.reclamos), 2)

    def test_un_reclamo_escalado_sigue_contando_como_abierto(self):
        self.insertar_reclamo(estado="escalado")
        self.crear_reclamo()
        self.assertEqual(len(self.store.reclamos), 1)
        self.assertEqual(self.store.reclamos[1]["reiteraciones"], 1)

    def test_un_reclamo_resuelto_no_cuenta_como_duplicado(self):
        self.insertar_reclamo(estado="resuelto")
        self.crear_reclamo()
        self.assertEqual(len(self.store.reclamos), 2)

    def test_un_reclamo_anulado_no_cuenta_como_duplicado(self):
        self.insertar_reclamo(estado="anulado")
        self.crear_reclamo()
        self.assertEqual(len(self.store.reclamos), 2)

    def test_el_reclamo_de_otro_cliente_no_cuenta(self):
        self.insertar_reclamo(cliente_id=2)
        self.crear_reclamo()
        self.assertEqual(len(self.store.reclamos), 2)
        self.assertEqual(self.store.reclamos[1]["reiteraciones"], 0)

    def test_la_reiteracion_queda_en_el_registro(self):
        self.crear_reclamo()
        self.crear_reclamo()
        entrada = self.store.registro[-1]
        self.assertEqual(entrada["accion"], "Reclamo reiterado")
        self.assertIn("reiteración 1", entrada["detalle"])

    def test_el_administrador_ve_que_el_reclamo_es_reiterado(self):
        self.crear_reclamo()
        self.crear_reclamo()
        self.cambiar_a_admin()
        self.assertIn("Reiterado ×2", self.html("/admin/reclamos"))
        self.assertIn("1 reclamo reiterado", self.html("/admin"))

    def test_un_reclamo_sin_reiteraciones_no_muestra_la_marca(self):
        self.crear_reclamo()
        self.assertNotIn("Reiterado", self.html("/reclamos"))


class ReclamosDelClienteTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.como_cliente()
        self.agregar_cliente_ajeno()

    def test_la_lista_exige_sesion(self):
        self.client.post("/logout")
        r = self.client.get("/reclamos")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/reclamos", r.headers["Location"])

    def test_sin_reclamos_se_informa(self):
        self.assertIn("No tenés reclamos", self.html("/reclamos"))

    def test_se_ven_solo_los_propios(self):
        self.insertar_reclamo(cliente_id=1, asunto="RECLAMO-PROPIO")
        self.insertar_reclamo(cliente_id=2, asunto="RECLAMO-AJENO")
        html = self.html("/reclamos")
        self.assertIn("RECLAMO-PROPIO", html)
        self.assertNotIn("RECLAMO-AJENO", html)

    def test_los_mas_nuevos_van_primero(self):
        self.insertar_reclamo(asunto="PRIMERO-VIEJO")
        self.insertar_reclamo(asunto="SEGUNDO-NUEVO")
        html = self.html("/reclamos")
        self.assertLess(html.index("SEGUNDO-NUEVO"), html.index("PRIMERO-VIEJO"))

    def test_el_detalle_muestra_la_conversacion(self):
        self.insertar_reclamo(asunto="Cobro duplicado")
        html = self.html("/reclamos/1")
        self.assertIn("Cobro duplicado", html)
        self.assertIn("Mensaje inicial de Cobro duplicado", html)

    def test_un_reclamo_ajeno_responde_como_inexistente(self):
        self.insertar_reclamo(cliente_id=2)
        self.assertEqual(self.client.get("/reclamos/1").status_code, 404)
        self.assertEqual(self.client.get("/reclamos/99").status_code, 404)

    def test_la_fecha_se_muestra_en_formato_legible(self):
        self.insertar_reclamo(creado="2026-01-01T10:00:00")
        self.assertIn("01/01/2026 10:00", self.html("/reclamos/1"))

    def test_el_texto_del_reclamo_no_inyecta_html(self):
        self.insertar_reclamo(asunto="<script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", self.html("/reclamos"))

    # --- escribir un mensaje ---------------------------------------------------

    def test_el_cliente_agrega_un_mensaje(self):
        self.insertar_reclamo()
        r = self.client.post("/reclamos/1/mensaje", data={"texto": "Les adjunto más datos."})
        self.assertEqual(r.status_code, 302)
        mensajes = self.store.reclamos[1]["mensajes"]
        self.assertEqual(mensajes[-1]["autor"], "cliente")
        self.assertEqual(mensajes[-1]["texto"], "Les adjunto más datos.")

    def test_tambien_puede_escribir_en_un_reclamo_escalado(self):
        self.insertar_reclamo(estado="escalado")
        self.client.post("/reclamos/1/mensaje", data={"texto": "Sigo esperando."})
        self.assertEqual(len(self.store.reclamos[1]["mensajes"]), 2)

    def test_un_mensaje_vacio_o_muy_largo_se_rechaza(self):
        self.insertar_reclamo()
        self.assertEqual(self.client.post("/reclamos/1/mensaje", data={"texto": "  "}).status_code, 400)
        self.assertEqual(self.client.post("/reclamos/1/mensaje", data={"texto": "x" * 1001}).status_code, 400)
        self.assertEqual(len(self.store.reclamos[1]["mensajes"]), 1)

    def test_no_se_escribe_en_un_reclamo_cerrado(self):
        for estado in ("resuelto", "anulado"):
            rid = self.insertar_reclamo(estado=estado, asunto=f"cerrado {estado}")
            self.client.post(f"/reclamos/{rid}/mensaje", data={"texto": "Hola"})
            self.assertEqual(len(self.store.reclamos[rid]["mensajes"]), 1)
        self.assertIn("ya está cerrado", self.html("/reclamos/2"))

    def test_no_se_escribe_en_el_reclamo_de_otro(self):
        self.insertar_reclamo(cliente_id=2)
        self.assertEqual(self.client.post("/reclamos/1/mensaje", data={"texto": "Hola"}).status_code, 404)

    # --- anular --------------------------------------------------------------------

    def test_el_cliente_anula_un_reclamo_pendiente(self):
        self.insertar_reclamo()
        self.client.post("/reclamos/1/anular")
        self.assertEqual(self.store.reclamos[1]["estado"], "anulado")

    def test_no_se_anula_un_reclamo_escalado_ni_resuelto(self):
        for estado in ("escalado", "resuelto"):
            rid = self.insertar_reclamo(estado=estado, asunto=f"r {estado}")
            self.client.post(f"/reclamos/{rid}/anular")
            self.assertEqual(self.store.reclamos[rid]["estado"], estado)
        self.assertIn("Solo se pueden anular reclamos pendientes", self.html("/reclamos/2"))

    def test_no_se_anula_el_reclamo_de_otro(self):
        self.insertar_reclamo(cliente_id=2)
        self.assertEqual(self.client.post("/reclamos/1/anular").status_code, 404)
        self.assertEqual(self.store.reclamos[1]["estado"], "pendiente")

    def test_anular_no_funciona_con_get(self):
        self.insertar_reclamo()
        self.assertEqual(self.client.get("/reclamos/1/anular").status_code, 405)

    def test_solo_un_reclamo_pendiente_ofrece_anular(self):
        self.insertar_reclamo(estado="resuelto")
        self.assertNotIn("Anular reclamo", self.html("/reclamos/1"))
        self.insertar_reclamo(asunto="otro")
        self.assertIn("Anular reclamo", self.html("/reclamos/2"))


class ResponderReclamoTest(GestionBase):
    """HU-27, HU-30 y HU-31: el administrador responde, actualiza el estado y el cliente recibe avisos."""

    def setUp(self):
        super().setUp()
        self.como_cliente()
        self.agregar_cliente_ajeno()
        self.rid = self.insertar_reclamo(cliente_id=1)
        self.cambiar_a_admin()

    def responder(self, texto="Estamos revisando tu caso.", accion="responder", rid=None):
        return self.client.post(
            f"/admin/reclamos/{rid or self.rid}/responder", data={"texto": texto, "accion": accion}
        )

    # --- responder ---------------------------------------------------------------

    def test_el_administrador_responde(self):
        r = self.responder()
        self.assertEqual(r.status_code, 302)
        mensaje = self.store.reclamos[self.rid]["mensajes"][-1]
        self.assertEqual(mensaje["autor"], "admin")
        self.assertEqual(mensaje["texto"], "Estamos revisando tu caso.")
        self.assertTrue(mensaje["nombre"])

    def test_responder_no_cierra_el_reclamo(self):
        self.responder()
        self.assertEqual(self.store.reclamos[self.rid]["estado"], "pendiente")

    def test_responder_avisa_al_cliente(self):
        self.responder()
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "reclamo_respondido")
        self.assertEqual(aviso["cliente_id"], 1)
        self.assertEqual(aviso["enlace"], f"/reclamos/{self.rid}")
        self.assertIn("Respondimos tu reclamo", aviso["mensaje"])

    def test_el_cliente_ve_la_respuesta_y_el_aviso(self):
        self.responder("Ya lo estamos resolviendo.")
        self.cambiar_a_cliente()
        self.assertIn("Ya lo estamos resolviendo.", self.html(f"/reclamos/{self.rid}"))
        self.assertIn("Respondimos tu reclamo", self.html("/avisos"))

    def test_responder_y_resolver_cierra_el_reclamo(self):
        self.responder(accion="resolver")
        self.assertEqual(self.store.reclamos[self.rid]["estado"], "resuelto")
        self.assertEqual(self.notisys.enviadas[-1]["evento"], "reclamo_resuelto")
        self.assertIn("quedó resuelto", self.notisys.enviadas[-1]["mensaje"])

    def test_tambien_se_puede_resolver_un_reclamo_escalado(self):
        self.store.reclamos[self.rid]["estado"] = "escalado"
        self.responder(accion="resolver")
        self.assertEqual(self.store.reclamos[self.rid]["estado"], "resuelto")

    def test_una_respuesta_vacia_se_rechaza(self):
        r = self.responder(texto="   ")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Escribí un mensaje", r.get_data(as_text=True))
        self.assertEqual(len(self.store.reclamos[self.rid]["mensajes"]), 1)

    def test_una_respuesta_muy_larga_se_rechaza(self):
        self.assertEqual(self.responder(texto="x" * 1001).status_code, 400)

    def test_no_se_responde_un_reclamo_cerrado(self):
        for estado in ("resuelto", "anulado"):
            rid = self.insertar_reclamo(cliente_id=1, estado=estado, asunto=f"c {estado}")
            self.responder(rid=rid)
            self.assertEqual(len(self.store.reclamos[rid]["mensajes"]), 1)
        self.assertIn("ya está cerrado", self.html("/admin/reclamos/2"))

    def test_las_respuestas_quedan_en_el_registro(self):
        self.responder()
        self.assertEqual(self.store.registro[-1]["accion"], "Reclamo respondido")
        self.responder(accion="resolver")
        self.assertEqual(self.store.registro[-1]["accion"], "Reclamo resuelto")

    # --- escalar ---------------------------------------------------------------------

    def test_el_administrador_escala_un_reclamo_pendiente(self):
        self.client.post(f"/admin/reclamos/{self.rid}/escalar")
        reclamo = self.store.reclamos[self.rid]
        self.assertEqual(reclamo["estado"], "escalado")
        self.assertEqual(reclamo["escalado_por"], "admin")
        self.assertEqual(reclamo["mensajes"][-1]["autor"], "sistema")
        self.assertEqual(self.notisys.enviadas[-1]["evento"], "reclamo_escalado")

    def test_solo_se_escala_un_reclamo_pendiente(self):
        for estado in ("escalado", "resuelto", "anulado"):
            rid = self.insertar_reclamo(cliente_id=1, estado=estado, asunto=f"e {estado}")
            self.client.post(f"/admin/reclamos/{rid}/escalar")
            self.assertEqual(self.store.reclamos[rid]["estado"], estado)
            self.assertEqual(len(self.store.reclamos[rid]["mensajes"]), 1)

    # --- reabrir ------------------------------------------------------------------------

    def test_el_administrador_reabre_un_reclamo_resuelto(self):
        self.responder(accion="resolver")
        self.client.post(f"/admin/reclamos/{self.rid}/reabrir")
        reclamo = self.store.reclamos[self.rid]
        self.assertEqual(reclamo["estado"], "pendiente")
        self.assertIn("Reabierto", reclamo["mensajes"][-1]["texto"])
        self.assertEqual(self.notisys.enviadas[-1]["evento"], "reclamo_reabierto")

    def test_reabrir_renueva_el_sla(self):
        self.store.reclamos[self.rid]["estado"] = "resuelto"
        self.store.reclamos[self.rid]["vence"] = "2020-01-01T00:00:00"
        self.client.post(f"/admin/reclamos/{self.rid}/reabrir")
        self.assertGreater(self.store.reclamos[self.rid]["vence"], "2025-01-01T00:00:00")
        self.assertEqual(self.store.reclamos[self.rid]["estado"], "pendiente")  # no se vuelve a escalar enseguida

    def test_solo_se_reabre_un_reclamo_resuelto(self):
        self.client.post(f"/admin/reclamos/{self.rid}/reabrir")
        self.assertEqual(len(self.store.reclamos[self.rid]["mensajes"]), 1)
        self.assertIn("Solo se pueden reabrir reclamos resueltos", self.html(f"/admin/reclamos/{self.rid}"))

    # --- acceso ---------------------------------------------------------------------------

    def test_las_acciones_del_administrador_dan_404_si_el_reclamo_no_existe(self):
        for accion in ("responder", "escalar", "reabrir"):
            self.assertEqual(self.client.post(f"/admin/reclamos/99/{accion}", data={"texto": "x"}).status_code, 404)
        self.assertEqual(self.client.get("/admin/reclamos/99").status_code, 404)

    def test_las_acciones_no_funcionan_con_get(self):
        for accion in ("responder", "escalar", "reabrir"):
            self.assertEqual(self.client.get(f"/admin/reclamos/{self.rid}/{accion}").status_code, 405)

    def test_un_cliente_no_puede_usar_las_acciones_del_administrador(self):
        self.cambiar_a_cliente()
        self.assertEqual(self.responder().status_code, 403)
        self.assertEqual(self.client.post(f"/admin/reclamos/{self.rid}/escalar").status_code, 403)
        self.assertEqual(self.client.get(f"/admin/reclamos/{self.rid}").status_code, 403)
        self.assertEqual(self.store.reclamos[self.rid]["estado"], "pendiente")

    def test_sin_sesion_no_se_puede_responder(self):
        self.client.post("/logout")
        self.assertEqual(self.responder().status_code, 302)
        self.assertEqual(len(self.store.reclamos[self.rid]["mensajes"]), 1)

    def test_el_detalle_del_administrador_ofrece_las_acciones_segun_el_estado(self):
        html = self.html(f"/admin/reclamos/{self.rid}")
        self.assertIn("Responder y resolver", html)
        self.assertIn("Escalar reclamo", html)
        self.assertNotIn("Reabrir reclamo", html)
        self.store.reclamos[self.rid]["estado"] = "resuelto"
        html = self.html(f"/admin/reclamos/{self.rid}")
        self.assertIn("Reabrir reclamo", html)
        self.assertNotIn("Responder y resolver", html)


class PanelDeReclamosTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()
        self.como_admin()

    def test_el_panel_exige_ser_administrador(self):
        self.client.post("/logout")
        self.assertEqual(self.client.get("/admin/reclamos").status_code, 302)
        self.como_cliente()
        self.assertEqual(self.client.get("/admin/reclamos").status_code, 403)

    def test_sin_reclamos_se_informa(self):
        self.assertIn("Todavía no hay reclamos", self.html("/admin/reclamos"))

    def test_se_ven_los_reclamos_de_todos_los_clientes(self):
        self.insertar_reclamo(cliente_id=2, asunto="DE-GALO")
        html = self.html("/admin/reclamos")
        self.assertIn("DE-GALO", html)
        self.assertIn("Galo Roselli", html)

    def test_primero_los_escalados_despues_los_pendientes(self):
        self.insertar_reclamo(cliente_id=2, estado="resuelto", asunto="R-RESUELTO")
        self.insertar_reclamo(cliente_id=2, estado="pendiente", asunto="R-PENDIENTE")
        self.insertar_reclamo(cliente_id=2, estado="escalado", asunto="R-ESCALADO")
        html = self.html("/admin/reclamos")
        self.assertLess(html.index("R-ESCALADO"), html.index("R-PENDIENTE"))
        self.assertLess(html.index("R-PENDIENTE"), html.index("R-RESUELTO"))

    def test_filtrar_por_estado(self):
        self.insertar_reclamo(cliente_id=2, estado="resuelto", asunto="R-RESUELTO")
        self.insertar_reclamo(cliente_id=2, estado="pendiente", asunto="R-PENDIENTE")
        html = self.html("/admin/reclamos?estado=pendiente")
        self.assertIn("R-PENDIENTE", html)
        self.assertNotIn("R-RESUELTO", html)

    def test_un_estado_invalido_se_ignora(self):
        self.insertar_reclamo(cliente_id=2, asunto="R-UNO")
        self.assertIn("R-UNO", self.html("/admin/reclamos?estado=inventado"))

    def test_un_filtro_sin_resultados_lo_explica(self):
        self.insertar_reclamo(cliente_id=2)
        self.assertIn("No hay reclamos con ese estado", self.html("/admin/reclamos?estado=anulado"))

    def test_los_filtros_muestran_las_cantidades(self):
        self.insertar_reclamo(cliente_id=2, estado="resuelto", asunto="a")
        self.insertar_reclamo(cliente_id=2, estado="resuelto", asunto="b")
        self.insertar_reclamo(cliente_id=2, estado="escalado", asunto="c")
        html = self.html("/admin/reclamos")
        self.assertIn("Resueltos <small>2</small>", html)
        self.assertIn("Escalados <small>1</small>", html)
        self.assertIn("Todos <small>3</small>", html)

    def test_los_reclamos_escalados_generan_una_alerta(self):
        self.insertar_reclamo(cliente_id=2, estado="escalado")
        html = self.html("/admin/reclamos")
        self.assertIn("1 reclamo escalado", html)
        self.assertIn('href="/admin/reclamos?estado=escalado"', html)


class SlaYEscaladoTest(GestionBase):
    """HU-29: el reclamo que supera su SLA se escala solo (el tiempo es simulado)."""

    def setUp(self):
        super().setUp()
        self.como_cliente()

    def navegar(self):
        """Cualquier pedido dispara la revisión de plazos."""
        self.client.get("/reclamos")

    def simular(self, horas="24"):
        return self.client.post("/admin/reclamos/simular-tiempo", data={"horas": horas})

    # --- escalado automático ---------------------------------------------------------

    def test_un_reclamo_con_el_sla_vencido_se_escala_solo(self):
        rid = self.insertar_reclamo(horas_para_vencer=-1)
        self.navegar()
        reclamo = self.store.reclamos[rid]
        self.assertEqual(reclamo["estado"], "escalado")
        self.assertEqual(reclamo["escalado_por"], "sla")

    def test_el_escalado_deja_un_mensaje_del_sistema(self):
        rid = self.insertar_reclamo(sla_horas=72, horas_para_vencer=-1)
        self.navegar()
        mensaje = self.store.reclamos[rid]["mensajes"][-1]
        self.assertEqual(mensaje["autor"], "sistema")
        self.assertIn("se superó el SLA de 72 h", mensaje["texto"])

    def test_se_avisa_al_cliente_que_se_escalo(self):
        self.insertar_reclamo(horas_para_vencer=-1)
        self.navegar()
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "reclamo_escalado")
        self.assertIn("SLA de 48 h", aviso["mensaje"])
        self.assertEqual(aviso["enlace"], "/reclamos/1")

    def test_el_escalado_automatico_lo_registra_el_sistema(self):
        self.insertar_reclamo(horas_para_vencer=-1)
        self.navegar()
        entrada = self.store.registro[-1]
        self.assertEqual(entrada["accion"], "Reclamo escalado")
        self.assertEqual(entrada["actor"], "Sistema")

    def test_un_reclamo_dentro_del_plazo_no_se_escala(self):
        rid = self.insertar_reclamo(horas_para_vencer=10)
        self.navegar()
        self.assertEqual(self.store.reclamos[rid]["estado"], "pendiente")

    def test_solo_se_escalan_los_reclamos_pendientes(self):
        resuelto = self.insertar_reclamo(estado="resuelto", horas_para_vencer=-5, asunto="a")
        anulado = self.insertar_reclamo(estado="anulado", horas_para_vencer=-5, asunto="b")
        self.navegar()
        self.assertEqual(self.store.reclamos[resuelto]["estado"], "resuelto")
        self.assertEqual(self.store.reclamos[anulado]["estado"], "anulado")

    def test_un_reclamo_escalado_no_se_escala_dos_veces(self):
        rid = self.insertar_reclamo(horas_para_vencer=-1)
        self.navegar()
        self.navegar()
        sistema = [m for m in self.store.reclamos[rid]["mensajes"] if m["autor"] == "sistema"]
        self.assertEqual(len(sistema), 1)
        self.assertEqual(len(self.notisys.enviadas), 1)

    def test_se_escalan_varios_reclamos_a_la_vez(self):
        self.insertar_reclamo(horas_para_vencer=-1, asunto="a")
        self.insertar_reclamo(horas_para_vencer=-9, asunto="b")
        self.insertar_reclamo(horas_para_vencer=30, asunto="c")
        self.navegar()
        estados = [self.store.reclamos[i]["estado"] for i in (1, 2, 3)]
        self.assertEqual(estados, ["escalado", "escalado", "pendiente"])

    def test_el_cliente_ve_el_reclamo_escalado(self):
        self.insertar_reclamo(horas_para_vencer=-1)
        self.assertIn("Escalado", self.html("/reclamos"))

    def test_el_administrador_ve_la_alerta_y_el_motivo(self):
        self.insertar_reclamo(horas_para_vencer=-1)
        self.navegar()
        self.cambiar_a_admin()
        html = self.html("/admin/reclamos")
        self.assertIn("1 reclamo escalado", html)
        self.assertIn("Por SLA", html)

    def test_se_muestra_cuanto_falta_para_que_venza(self):
        self.insertar_reclamo(horas_para_vencer=36)
        self.assertIn("Vence en 36 h", self.html("/reclamos"))

    def test_un_reclamo_cerrado_no_muestra_el_plazo(self):
        self.insertar_reclamo(estado="resuelto", horas_para_vencer=36)
        self.assertNotIn("Vence en", self.html("/reclamos"))

    # --- simulación del tiempo ----------------------------------------------------------

    def test_avanzar_el_reloj_escala_los_reclamos_que_vencen(self):
        rid = self.insertar_reclamo(horas_para_vencer=30)
        self.cambiar_a_admin()
        self.simular("24")
        self.assertEqual(self.store.reclamos[rid]["estado"], "pendiente")
        self.simular("24")
        self.assertEqual(self.store.reclamos[rid]["estado"], "escalado")
        self.assertEqual(self.reloj.horas_simuladas, 48)

    def test_el_resultado_de_la_simulacion_se_informa(self):
        self.insertar_reclamo(horas_para_vencer=10)
        self.cambiar_a_admin()
        self.simular("24")
        html = self.html("/admin/reclamos")
        self.assertIn("Pasaron 24 h", html)
        self.assertIn("reclamos #1", html)

    def test_si_nada_vence_tambien_se_informa(self):
        self.insertar_reclamo(horas_para_vencer=100)
        self.cambiar_a_admin()
        self.simular("24")
        self.assertIn("Ningún reclamo superó su SLA", self.html("/admin/reclamos"))

    def test_las_horas_deben_ser_validas(self):
        self.cambiar_a_admin()
        for horas in ("0", "abc", "721", "-5", "", "2.5"):
            self.simular(horas if horas else "x")
        self.assertEqual(self.reloj.horas_simuladas, 0)

    def test_los_extremos_son_validos(self):
        self.cambiar_a_admin()
        self.simular("1")
        self.simular("720")
        self.assertEqual(self.reloj.horas_simuladas, 721)

    def test_sin_horas_se_avanza_un_dia(self):
        self.cambiar_a_admin()
        self.client.post("/admin/reclamos/simular-tiempo", data={})
        self.assertEqual(self.reloj.horas_simuladas, 24)

    def test_el_panel_muestra_el_tiempo_simulado(self):
        self.cambiar_a_admin()
        self.simular("24")
        self.assertIn("Tiempo simulado hasta ahora: +24 h", self.html("/admin/reclamos"))

    def test_la_simulacion_queda_en_el_registro(self):
        self.insertar_reclamo(horas_para_vencer=10)
        self.cambiar_a_admin()
        self.simular("24")
        acciones = [e["accion"] for e in self.store.registro]
        self.assertIn("Tiempo simulado", acciones)

    def test_un_reclamo_nuevo_vence_segun_el_reloj_simulado(self):
        self.reloj.avanzar(100)
        self.crear_reclamo()
        # Con el reloj adelantado, el reclamo no nace ya vencido.
        self.assertEqual(self.store.reclamos[1]["estado"], "pendiente")
        self.navegar()
        self.assertEqual(self.store.reclamos[1]["estado"], "pendiente")

    def test_un_cliente_no_puede_simular_el_tiempo(self):
        self.assertEqual(self.simular().status_code, 403)
        self.assertEqual(self.reloj.horas_simuladas, 0)

    def test_sin_sesion_no_se_puede_simular_el_tiempo(self):
        self.client.post("/logout")
        self.assertEqual(self.simular().status_code, 302)
        self.assertEqual(self.reloj.horas_simuladas, 0)

    def test_simular_no_funciona_con_get(self):
        self.cambiar_a_admin()
        self.assertEqual(self.client.get("/admin/reclamos/simular-tiempo").status_code, 405)


class NotificacionesDeReclamosTest(GestionBase):
    """HU-31: el cliente recibe un aviso de cada novedad de su reclamo."""

    def test_ingresar_un_reclamo_avisa_que_se_recibio(self):
        self.como_cliente()
        self.crear_reclamo()
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "reclamo_recibido")
        self.assertEqual(aviso["enlace"], "/reclamos/1")
        self.assertIn("Recibimos tu reclamo #1", aviso["mensaje"])

    def test_los_avisos_llevan_al_reclamo(self):
        self.como_cliente()
        self.crear_reclamo()
        self.assertIn('href="/reclamos/1"', self.html("/avisos"))

    def test_cada_novedad_genera_un_aviso(self):
        self.como_cliente()
        self.crear_reclamo()
        self.cambiar_a_admin()
        self.client.post("/admin/reclamos/1/responder", data={"texto": "Hola", "accion": "responder"})
        self.client.post("/admin/reclamos/1/escalar")
        self.client.post("/admin/reclamos/1/responder", data={"texto": "Listo", "accion": "resolver"})
        self.client.post("/admin/reclamos/1/reabrir")
        eventos = [a["evento"] for a in self.notisys.enviadas]
        self.assertEqual(
            eventos,
            ["reclamo_recibido", "reclamo_respondido", "reclamo_escalado", "reclamo_resuelto", "reclamo_reabierto"],
        )

    def test_anular_un_reclamo_no_genera_aviso(self):
        self.como_cliente()
        self.crear_reclamo()
        self.client.post("/reclamos/1/anular")
        self.assertEqual(len(self.notisys.enviadas), 1)  # solo el de recepción
