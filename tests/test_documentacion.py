"""HU-15, HU-16 y HU-17: adjuntar, validar y recibir documentación en una solicitud."""
from ayudas_gestion import JPG, PDF, PNG, GestionBase

DOS_MB = 2 * 1024 * 1024


class AdjuntarDocumentacionTest(GestionBase):
    """HU-15 y HU-16: el cliente adjunta un archivo y el sistema valida que sea aceptable."""

    def setUp(self):
        super().setUp()
        self.como_cliente()

    def test_adjuntar_un_pdf_valido(self):
        r = self.crear_solicitud(documento=("constancia.pdf", PDF))
        self.assertEqual(r.status_code, 302)
        adjunto = self.store.solicitudes[1]["adjunto"]
        self.assertEqual(adjunto["nombre"], "constancia.pdf")
        self.assertEqual(adjunto["tipo"], "application/pdf")
        self.assertEqual(adjunto["tamano"], len(PDF))
        self.assertEqual(adjunto["contenido"], PDF)

    def test_adjuntar_un_png_y_un_jpg(self):
        self.assertEqual(self.crear_solicitud(documento=("dni.png", PNG)).status_code, 302)
        self.assertEqual(self.crear_solicitud(documento=("foto.jpg", JPG)).status_code, 302)
        self.assertEqual(self.crear_solicitud(documento=("foto2.JPEG", JPG)).status_code, 302)
        self.assertEqual(self.store.solicitudes[1]["adjunto"]["tipo"], "image/png")
        self.assertEqual(self.store.solicitudes[2]["adjunto"]["tipo"], "image/jpeg")

    def test_la_documentacion_es_opcional(self):
        self.assertEqual(self.crear_solicitud().status_code, 302)
        self.assertIsNone(self.store.solicitudes[1]["adjunto"])

    def test_no_se_acepta_otra_extension(self):
        for nombre in ("virus.exe", "notas.txt", "planilla.xlsx", "sin_extension"):
            r = self.crear_solicitud(documento=(nombre, PDF))
            self.assertEqual(r.status_code, 400, nombre)
            self.assertIn("PDF, PNG o JPG", r.get_data(as_text=True))
        self.assertEqual(len(self.store.solicitudes), 0)

    def test_no_se_acepta_un_archivo_vacio(self):
        r = self.crear_solicitud(documento=("vacio.pdf", b""))
        self.assertEqual(r.status_code, 400)
        self.assertIn("El archivo está vacío", r.get_data(as_text=True))

    def test_el_maximo_son_2_mb(self):
        justo = b"%PDF-" + b"x" * (DOS_MB - 5)
        self.assertEqual(self.crear_solicitud(documento=("justo.pdf", justo)).status_code, 302)
        r = self.crear_solicitud(documento=("grande.pdf", justo + b"x"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("supera el máximo de 2 MB", r.get_data(as_text=True))

    def test_el_contenido_tiene_que_coincidir_con_la_extension(self):
        r = self.crear_solicitud(documento=("falso.pdf", b"esto es texto, no un pdf"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("no parece ser un PDF válido", r.get_data(as_text=True))
        r = self.crear_solicitud(documento=("falso.png", PDF))
        self.assertEqual(r.status_code, 400)
        self.assertIn("PNG", r.get_data(as_text=True))

    def test_el_nombre_del_archivo_se_limpia(self):
        self.crear_solicitud(documento=("../../etc/passwd.pdf", PDF))
        self.assertEqual(self.store.solicitudes[1]["adjunto"]["nombre"], "etc_passwd.pdf")

    def test_un_documento_invalido_no_crea_la_solicitud_ni_avisos(self):
        self.crear_solicitud(documento=("virus.exe", PDF))
        self.assertEqual(len(self.store.solicitudes), 0)
        self.assertEqual(len(self.notisys.enviadas), 0)

    def test_un_error_del_documento_conserva_lo_escrito(self):
        r = self.crear_solicitud(detalle="Mi detalle importante", documento=("virus.exe", PDF))
        self.assertIn("Mi detalle importante", r.get_data(as_text=True))

    def test_se_pueden_ver_varios_errores_a_la_vez(self):
        r = self.crear_solicitud(plan_id="", detalle="", documento=("virus.exe", PDF))
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Elegí un plan de la lista", html)
        self.assertIn("Contanos qué querés modificar", html)
        self.assertIn("PDF, PNG o JPG", html)


class RecepcionTest(GestionBase):
    """HU-17: la documentación queda recibida y se avisa."""

    def setUp(self):
        super().setUp()
        self.como_cliente()

    def test_la_documentacion_queda_recibida(self):
        self.crear_solicitud(documento=("constancia.pdf", PDF))
        adjunto = self.store.solicitudes[1]["adjunto"]
        self.assertEqual(adjunto["estado"], "recibida")
        self.assertIn("recibido", adjunto)

    def test_se_avisa_al_cliente_que_se_recibio(self):
        self.crear_solicitud(documento=("constancia.pdf", PDF))
        eventos = [a["evento"] for a in self.notisys.enviadas]
        self.assertEqual(eventos, ["pendiente", "documentacion_recibida"])
        self.assertIn("constancia.pdf", self.notisys.enviadas[1]["mensaje"])

    def test_sin_documento_no_hay_aviso_de_recepcion(self):
        self.crear_solicitud()
        self.assertEqual([a["evento"] for a in self.notisys.enviadas], ["pendiente"])

    def test_el_cliente_ve_que_la_documentacion_fue_recibida(self):
        self.crear_solicitud(documento=("constancia.pdf", PDF))
        html = self.html("/solicitudes")
        self.assertIn("constancia.pdf", html)
        self.assertIn("Documentación recibida", html)
        self.assertIn("/solicitudes/1/documento", html)

    def test_el_administrador_ve_la_documentacion_y_el_boton_para_validarla(self):
        self.crear_solicitud(documento=("constancia.pdf", PDF))
        self.cambiar_a_admin()
        html = self.html("/admin/solicitudes")
        self.assertIn("constancia.pdf", html)
        self.assertIn("Documentación recibida", html)
        self.assertIn("Validar documentación", html)

    def test_queda_constancia_en_el_registro(self):
        self.crear_solicitud(documento=("constancia.pdf", PDF))
        self.assertIn("constancia.pdf", self.store.registro[-1]["detalle"])


class ValidarDocumentacionTest(GestionBase):
    """HU-16: el administrador revisa la documentación recibida y la valida."""

    def setUp(self):
        super().setUp()
        self.poner_costo(2)
        self.agregar_cliente_ajeno()

    def con_documento(self, estado="recibida", solicitud_estado="pendiente", cliente_id=2):
        sid = self.insertar(cliente_id=cliente_id, estado=solicitud_estado, adjunto=self.adjunto(estado))
        self.como_admin()
        return sid

    def validar(self, sid):
        return self.client.post(f"/admin/solicitudes/{sid}/documento/validar")

    def test_validar_la_documentacion(self):
        sid = self.con_documento()
        r = self.validar(sid)
        self.assertEqual(r.status_code, 302)
        adjunto = self.store.solicitudes[sid]["adjunto"]
        self.assertEqual(adjunto["estado"], "validada")
        self.assertIn("validado", adjunto)

    def test_se_avisa_al_cliente_que_se_valido(self):
        sid = self.con_documento(cliente_id=1)
        self.store.clientes[1] = {"id": 1, "nombre": "Lucas", "plan_id": 1}
        self.validar(sid)
        aviso = self.notisys.enviadas[-1]
        self.assertEqual(aviso["evento"], "documentacion_validada")
        self.assertEqual(aviso["cliente_id"], 1)

    def test_el_panel_confirma_y_quita_el_boton(self):
        sid = self.con_documento()
        self.validar(sid)
        html = self.html("/admin/solicitudes")
        self.assertIn("quedó validada", html)
        self.assertIn("Documentación validada", html)
        self.assertNotIn("Validar documentación", html)

    def test_validar_dos_veces_no_cambia_nada(self):
        sid = self.con_documento("validada")
        self.validar(sid)
        self.assertIn("ya estaba validada", self.html("/admin/solicitudes"))

    def test_solo_se_valida_la_documentacion_de_solicitudes_pendientes(self):
        sid = self.con_documento(solicitud_estado="anulada")
        self.validar(sid)
        self.assertEqual(self.store.solicitudes[sid]["adjunto"]["estado"], "recibida")

    def test_sin_documentacion_no_hay_nada_que_validar(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.assertEqual(self.validar(sid).status_code, 404)
        self.assertEqual(self.validar(99).status_code, 404)

    def test_un_cliente_no_puede_validar(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1, adjunto=self.adjunto())
        self.assertEqual(self.validar(sid).status_code, 403)
        self.assertEqual(self.store.solicitudes[sid]["adjunto"]["estado"], "recibida")

    def test_sin_sesion_no_se_puede_validar(self):
        sid = self.insertar(cliente_id=2, adjunto=self.adjunto())
        self.assertEqual(self.validar(sid).status_code, 302)
        self.assertEqual(self.store.solicitudes[sid]["adjunto"]["estado"], "recibida")

    def test_validar_no_funciona_con_get(self):
        sid = self.con_documento()
        self.assertEqual(self.client.get(f"/admin/solicitudes/{sid}/documento/validar").status_code, 405)

    # --- la documentación condiciona la aprobación ---------------------------------

    def test_no_se_puede_aprobar_con_documentacion_sin_validar(self):
        sid = self.con_documento()
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.assertEqual(self.store.solicitudes[sid]["estado"], "pendiente")
        self.assertEqual(len(self.store.facturas), 0)
        self.assertIn("todavía no fue validada", self.html("/admin/solicitudes"))

    def test_se_puede_aprobar_con_documentacion_validada(self):
        sid = self.con_documento()
        self.validar(sid)
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.assertEqual(self.store.solicitudes[sid]["estado"], "realizado")

    def test_sin_documentacion_se_aprueba_directamente(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2)
        self.client.post(f"/admin/solicitudes/{sid}/realizar")
        self.assertEqual(self.store.solicitudes[sid]["estado"], "realizado")

    def test_se_puede_rechazar_sin_validar_la_documentacion(self):
        sid = self.con_documento()
        self.client.post(f"/admin/solicitudes/{sid}/rechazar")
        self.assertEqual(self.store.solicitudes[sid]["estado"], "rechazada")


class DescargarDocumentacionTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    def test_el_cliente_descarga_su_documento(self):
        self.como_cliente()
        self.crear_solicitud(documento=("constancia.pdf", PDF))
        r = self.client.get("/solicitudes/1/documento")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, PDF)
        self.assertEqual(r.mimetype, "application/pdf")
        self.assertIn("attachment", r.headers["Content-Disposition"])
        self.assertIn("constancia.pdf", r.headers["Content-Disposition"])
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")

    def test_el_administrador_descarga_cualquier_documento(self):
        self.como_admin()
        sid = self.insertar(cliente_id=2, adjunto=self.adjunto(contenido=PDF))
        r = self.client.get(f"/solicitudes/{sid}/documento")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, PDF)

    def test_un_cliente_no_descarga_el_documento_de_otro(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=2, adjunto=self.adjunto())
        self.assertEqual(self.client.get(f"/solicitudes/{sid}/documento").status_code, 404)

    def test_sin_sesion_pide_iniciar_sesion(self):
        sid = self.insertar(cliente_id=2, adjunto=self.adjunto())
        r = self.client.get(f"/solicitudes/{sid}/documento")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_una_solicitud_sin_documento_no_se_descarga(self):
        self.como_cliente()
        sid = self.insertar(cliente_id=1)
        self.assertEqual(self.client.get(f"/solicitudes/{sid}/documento").status_code, 404)

    def test_una_solicitud_inexistente_no_se_descarga(self):
        self.como_cliente()
        self.assertEqual(self.client.get("/solicitudes/99/documento").status_code, 404)
