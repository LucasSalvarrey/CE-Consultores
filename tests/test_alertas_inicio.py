"""Panel de inicio del administrador, alertas y pantallas de error."""
import io

from ayudas_gestion import GestionBase


class InicioDelAdministradorTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    def test_exige_sesion_de_administrador(self):
        r = self.client.get("/admin")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/admin", r.headers["Location"])
        self.como_cliente()
        self.assertEqual(self.client.get("/admin").status_code, 403)

    def test_la_raiz_lleva_a_cada_uno_a_su_pantalla(self):
        self.assertTrue(self.client.get("/").headers["Location"].endswith("/mi-cuenta"))
        self.como_admin()
        self.assertTrue(self.client.get("/").headers["Location"].endswith("/admin"))

    def test_sin_datos_muestra_ceros(self):
        self.como_admin()
        html = self.html("/admin")
        self.assertIn("Panel de administración", html)
        self.assertIn("0 de prioridad alta", html)
        self.assertIn("0 escalados", html)
        self.assertIn("Todavía no hay cambios registrados", html)

    def test_cuenta_lo_que_necesita_atencion(self):
        self.insertar(cliente_id=2, prioridad="alta")
        self.insertar(cliente_id=2)
        self.insertar(cliente_id=2, estado="realizado")
        self.insertar_reclamo(cliente_id=2, asunto="a", estado="escalado")
        self.insertar_reclamo(cliente_id=2, asunto="b")
        self.insertar_reclamo(cliente_id=2, asunto="c", estado="resuelto")
        self.insertar_factura(estado="fallida", cliente_id=2)
        self.insertar_factura(estado="pendiente", cliente_id=2)
        self.insertar_factura(estado="pagada", cliente_id=2)
        self.como_admin()
        html = self.html("/admin")
        self.assertIn('<div class="stat__valor">2</div>\n    <div class="stat__nota">1 de prioridad alta', html)
        self.assertIn("1 de prioridad alta", html)
        self.assertIn("1 escalados", html)
        self.assertIn("1 con falla en PagoNet", html)

    def test_muestra_los_ultimos_cambios(self):
        self.como_cliente()
        self.crear_reclamo()
        self.cambiar_a_admin()
        html = self.html("/admin")
        self.assertIn("Reclamo ingresado", html)
        self.assertIn("Cliente registrado", html)

    def test_el_menu_del_administrador_tiene_todas_las_secciones(self):
        self.como_admin()
        html = self.html("/admin")
        for href in ("/admin", "/admin/solicitudes", "/admin/reclamos", "/admin/facturas",
                     "/admin/reportes", "/admin/registro", "/planes"):
            self.assertIn(f'href="{href}"', html)
        self.assertNotIn("Mi cuenta", html)

    def test_el_menu_del_cliente_tiene_sus_secciones(self):
        self.como_cliente()
        html = self.html("/mi-cuenta")
        for href in ("/planes", "/solicitudes", "/reclamos", "/avisos", "/mi-cuenta"):
            self.assertIn(f'href="{href}"', html)
        self.assertNotIn("/admin", html)

    def test_la_seccion_actual_queda_marcada(self):
        self.como_admin()
        self.assertIn('href="/admin/facturas" class="activo"', self.html("/admin/facturas"))
        self.assertNotIn('href="/admin/reclamos" class="activo"', self.html("/admin/facturas"))


class AlertasTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()
        self.como_admin()

    def alertas(self):
        return self.html("/admin")

    def test_sin_novedades_no_hay_alertas(self):
        self.assertNotIn('role="alert"', self.alertas())

    def test_alerta_por_facturas_con_falla(self):
        self.insertar_factura(estado="fallida", cliente_id=2)
        html = self.alertas()
        self.assertIn('aviso aviso-error', html)
        self.assertIn("1 factura con falla en PagoNet", html)
        self.assertIn("Gestionar", html)

    def test_alerta_por_reclamos_escalados(self):
        self.insertar_reclamo(cliente_id=2, estado="escalado")
        html = self.alertas()
        self.assertIn("1 reclamo escalado", html)
        self.insertar_reclamo(cliente_id=2, estado="escalado", asunto="otro")
        self.assertIn("2 reclamos escalados", self.alertas())

    def test_alerta_por_reclamos_reiterados(self):
        self.insertar_reclamo(cliente_id=2, reiteraciones=1)
        self.assertIn("1 reclamo reiterado", self.alertas())

    def test_un_reclamo_reiterado_ya_resuelto_no_alerta(self):
        self.insertar_reclamo(cliente_id=2, reiteraciones=3, estado="resuelto")
        self.assertNotIn("reiterado", self.alertas())

    def test_alerta_por_solicitudes_urgentes(self):
        self.insertar(cliente_id=2, prioridad="alta")
        html = self.alertas()
        self.assertIn("aviso-info", html)
        self.assertIn("1 solicitud de prioridad alta pendiente", html)

    def test_las_alertas_se_acumulan(self):
        self.insertar_factura(estado="fallida", cliente_id=2)
        self.insertar_reclamo(cliente_id=2, estado="escalado")
        self.insertar(cliente_id=2, prioridad="alta")
        self.assertEqual(self.alertas().count('role="alert"'), 3)

    def test_las_alertas_se_ven_en_todas_las_pantallas_del_administrador(self):
        self.insertar_factura(estado="fallida", cliente_id=2)
        for ruta in ("/admin", "/admin/solicitudes", "/admin/reclamos", "/admin/facturas",
                     "/admin/reportes", "/admin/registro", "/planes"):
            self.assertIn("con falla en PagoNet: reintentá", self.html(ruta), ruta)

    def test_el_cliente_no_ve_las_alertas_del_administrador(self):
        self.insertar_factura(estado="fallida", cliente_id=1)
        self.insertar_reclamo(cliente_id=1, estado="escalado")
        self.client.post("/logout")
        self.como_cliente()
        for ruta in ("/mi-cuenta", "/planes", "/solicitudes"):
            self.assertNotIn('role="alert"', self.html(ruta), ruta)

    def test_el_visitante_no_ve_alertas(self):
        self.insertar_factura(estado="fallida", cliente_id=2)
        self.client.post("/logout")
        self.assertNotIn('role="alert"', self.html("/login"))


class MensajesFlashTest(GestionBase):
    def test_un_mensaje_de_error_se_muestra_como_error(self):
        self.como_cliente()
        self.crear_reclamo()
        self.client.post("/reclamos/1/mensaje", data={"texto": "x"})
        self.client.post("/reclamos/1/anular")
        self.client.post("/reclamos/1/anular")
        self.assertIn('class="aviso aviso-error"', self.html("/reclamos/1"))

    def test_un_mensaje_comun_se_muestra_como_ok(self):
        self.como_cliente()
        self.crear_reclamo()
        self.assertIn('class="aviso aviso-ok"', self.html("/reclamos/1"))

    def test_un_mensaje_se_muestra_una_sola_vez(self):
        self.como_cliente()
        self.crear_reclamo()
        self.html("/reclamos/1")
        self.assertNotIn("Recibimos tu reclamo #1. Te vamos", self.html("/reclamos/1"))


class PaginasDeErrorTest(GestionBase):
    def test_pagina_inexistente(self):
        r = self.client.get("/esto-no-existe")
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 404)
        self.assertIn("No encontramos lo que buscabas", html)
        self.assertIn("CE Consultores", html)
        self.assertIn("Volver al inicio", html)

    def test_acceso_restringido(self):
        self.como_cliente()
        r = self.client.get("/admin/solicitudes")
        self.assertEqual(r.status_code, 403)
        self.assertIn("Acceso restringido", r.get_data(as_text=True))

    def test_accion_no_permitida(self):
        self.como_cliente()
        r = self.client.get("/solicitudes/1/anular")
        self.assertEqual(r.status_code, 405)
        self.assertIn("Acción no permitida", r.get_data(as_text=True))

    def test_un_archivo_demasiado_grande(self):
        self.como_cliente()
        enorme = b"%PDF-" + b"x" * (6 * 1024 * 1024)
        r = self.client.post(
            "/solicitudes/nueva",
            data={"plan_id": "2", "detalle": "x", "documento": (io.BytesIO(enorme), "enorme.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(r.status_code, 413)
        self.assertIn("demasiado grande", r.get_data(as_text=True))
        self.assertEqual(len(self.store.solicitudes), 0)
