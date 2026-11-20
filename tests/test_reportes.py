"""HU-32, HU-33 y HU-34: definir un reporte, armarlo y el caso del reporte vacío."""
import unittest
from datetime import date
from decimal import Decimal

from ayudas_gestion import GestionBase
from reportes.armado import armar
from reportes.validaciones import validar_definicion


def definicion(**cambios):
    datos = {"tipo": "solicitudes", "desde": None, "hasta": None, "estado": ""}
    datos.update(cambios)
    return datos


class ValidarDefinicionTest(unittest.TestCase):
    """HU-32: qué se acepta al definir un reporte."""

    def test_una_definicion_minima_es_valida(self):
        datos, errores = validar_definicion({"tipo": "reclamos"})
        self.assertEqual(errores, {})
        self.assertEqual(datos, {"tipo": "reclamos", "desde": None, "hasta": None, "estado": ""})

    def test_una_definicion_completa(self):
        datos, errores = validar_definicion(
            {"tipo": "solicitudes", "desde": "2026-01-01", "hasta": "2026-03-31", "estado": "pendiente"}
        )
        self.assertEqual(errores, {})
        self.assertEqual(datos["desde"], date(2026, 1, 1))
        self.assertEqual(datos["hasta"], date(2026, 3, 31))

    def test_el_tipo_es_obligatorio_y_tiene_que_existir(self):
        self.assertIn("tipo", validar_definicion({})[1])
        self.assertIn("tipo", validar_definicion({"tipo": ""})[1])
        self.assertIn("tipo", validar_definicion({"tipo": "ventas"})[1])

    def test_las_fechas_tienen_que_ser_validas(self):
        for texto in ("2026-13-45", "ayer", "01/02/2026", "2026-02-30"):
            self.assertIn("desde", validar_definicion({"tipo": "reclamos", "desde": texto})[1], texto)
            self.assertIn("hasta", validar_definicion({"tipo": "reclamos", "hasta": texto})[1], texto)

    def test_desde_no_puede_ser_posterior_a_hasta(self):
        _, errores = validar_definicion({"tipo": "reclamos", "desde": "2026-05-01", "hasta": "2026-04-01"})
        self.assertIn("no puede ser anterior", errores["hasta"])

    def test_desde_y_hasta_pueden_ser_el_mismo_dia(self):
        _, errores = validar_definicion({"tipo": "reclamos", "desde": "2026-05-01", "hasta": "2026-05-01"})
        self.assertEqual(errores, {})

    def test_el_estado_tiene_que_corresponder_al_tipo(self):
        self.assertEqual(validar_definicion({"tipo": "facturacion", "estado": "pagada"})[1], {})
        self.assertIn("estado", validar_definicion({"tipo": "reclamos", "estado": "pagada"})[1])
        self.assertIn("estado", validar_definicion({"tipo": "solicitudes", "estado": "escalado"})[1])


class ArmarReporteTest(GestionBase):
    """HU-33: el reporte tiene filas y un resumen."""

    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    def resumen(self, reporte):
        return dict(reporte["resumen"])

    def test_reporte_de_solicitudes(self):
        self.insertar(cliente_id=2, estado="pendiente", prioridad="alta")
        self.insertar(cliente_id=2, estado="realizado", plan_id=3)
        self.insertar(cliente_id=2, estado="anulada", tipo="baja", plan_id=None)
        reporte = armar(self.store, definicion())
        resumen = self.resumen(reporte)
        self.assertEqual(resumen["Total de solicitudes"], 3)
        self.assertEqual((resumen["Pendiente"], resumen["Realizado"], resumen["Anulada"], resumen["Rechazada"]), (1, 1, 1, 0))
        self.assertEqual((resumen["Prioridad alta"], resumen["Prioridad media"], resumen["Prioridad baja"]), (1, 2, 0))
        self.assertEqual(len(reporte["filas"]), 3)
        self.assertEqual(reporte["columnas"][0], "N.º")
        self.assertEqual(reporte["filas"][0][:2], ["#1", "Galo Roselli"])
        self.assertFalse(reporte["vacio"])

    def test_las_filas_de_una_baja_muestran_sin_plan(self):
        self.insertar(cliente_id=2, tipo="baja", plan_id=None)
        fila = armar(self.store, definicion())["filas"][0]
        self.assertIn("Baja de plan", fila)
        self.assertIn("Sin plan", fila)

    def test_reporte_de_reclamos(self):
        self.insertar_reclamo(cliente_id=2, asunto="a", estado="escalado", escalado_por="sla", reiteraciones=2)
        self.insertar_reclamo(cliente_id=2, asunto="b", estado="escalado", escalado_por="admin")
        self.insertar_reclamo(cliente_id=2, asunto="c", estado="resuelto")
        reporte = armar(self.store, definicion(tipo="reclamos"))
        resumen = self.resumen(reporte)
        self.assertEqual(resumen["Total de reclamos"], 3)
        self.assertEqual((resumen["Escalado"], resumen["Resuelto"], resumen["Pendiente"]), (2, 1, 0))
        self.assertEqual(resumen["Escalados por SLA"], 1)
        self.assertEqual(resumen["Reiterados"], 1)
        self.assertEqual(reporte["filas"][0][2], "a")

    def test_reporte_de_facturacion(self):
        self.insertar_factura(estado="pagada", monto="9000.00", cliente_id=2)
        self.insertar_factura(estado="pagada", monto="5000.00", cliente_id=2)
        self.insertar_factura(estado="devuelta", monto="3000.00", cliente_id=2)
        self.insertar_factura(estado="fallida", monto="1000.00", cliente_id=2)
        resumen = self.resumen(armar(self.store, definicion(tipo="facturacion")))
        self.assertEqual(resumen["Total de facturas"], 4)
        self.assertEqual(resumen["Total cobrado"], "$ 14.000,00")
        self.assertEqual(resumen["Total devuelto"], "$ 3.000,00")
        self.assertEqual(resumen["Pagadas"] if "Pagadas" in resumen else resumen["Pagada"], 2)

    def test_filtrar_por_estado(self):
        self.insertar(cliente_id=2, estado="pendiente")
        self.insertar(cliente_id=2, estado="realizado")
        reporte = armar(self.store, definicion(estado="realizado"))
        self.assertEqual(len(reporte["filas"]), 1)
        self.assertEqual(reporte["filas"][0][5], "Realizado")
        self.assertIn("realizado", reporte["titulo"])

    def test_filtrar_por_periodo(self):
        a = self.insertar(cliente_id=2)
        b = self.insertar(cliente_id=2)
        c = self.insertar(cliente_id=2)
        self.store.solicitudes[a]["creado"] = "2026-01-10T09:00:00"
        self.store.solicitudes[b]["creado"] = "2026-02-15T09:00:00"
        self.store.solicitudes[c]["creado"] = "2026-03-20T09:00:00"
        solo_febrero = armar(self.store, definicion(desde=date(2026, 2, 1), hasta=date(2026, 2, 28)))
        self.assertEqual([f[0] for f in solo_febrero["filas"]], [f"#{b}"])
        desde = armar(self.store, definicion(desde=date(2026, 2, 15)))
        self.assertEqual([f[0] for f in desde["filas"]], [f"#{b}", f"#{c}"])
        hasta = armar(self.store, definicion(hasta=date(2026, 2, 15)))
        self.assertEqual([f[0] for f in hasta["filas"]], [f"#{a}", f"#{b}"])

    def test_el_periodo_se_describe(self):
        self.assertEqual(armar(self.store, definicion())["periodo"], "de todo el período")
        self.assertEqual(
            armar(self.store, definicion(desde=date(2026, 2, 1), hasta=date(2026, 2, 28)))["periodo"],
            "del 01/02/2026 al 28/02/2026",
        )
        self.assertEqual(armar(self.store, definicion(desde=date(2026, 2, 1)))["periodo"], "desde el 01/02/2026")
        self.assertEqual(armar(self.store, definicion(hasta=date(2026, 2, 28)))["periodo"], "hasta el 28/02/2026")

    def test_las_filas_van_ordenadas_por_numero(self):
        for _ in range(3):
            self.insertar(cliente_id=2)
        self.assertEqual([f[0] for f in armar(self.store, definicion())["filas"]], ["#1", "#2", "#3"])


class ReporteVacioTest(GestionBase):
    """HU-34: si no hay datos, el reporte lo dice."""

    def test_sin_datos_el_reporte_esta_vacio(self):
        reporte = armar(self.store, definicion())
        self.assertTrue(reporte["vacio"])
        self.assertEqual(reporte["filas"], [])

    def test_los_filtros_pueden_dejar_el_reporte_vacio(self):
        self.agregar_cliente_ajeno()
        self.insertar(cliente_id=2, estado="pendiente")
        self.assertTrue(armar(self.store, definicion(estado="realizado"))["vacio"])
        self.assertTrue(armar(self.store, definicion(desde=date(2030, 1, 1)))["vacio"])

    def test_el_resumen_de_un_reporte_vacio_esta_en_cero(self):
        resumen = dict(armar(self.store, definicion(tipo="facturacion"))["resumen"])
        self.assertEqual(resumen["Total de facturas"], 0)
        self.assertEqual(resumen["Total cobrado"], "$ 0,00")

    def test_la_pantalla_avisa_que_el_reporte_esta_vacio(self):
        self.como_admin()
        html = self.html("/admin/reportes?tipo=reclamos")
        self.assertIn("Reporte vacío", html)
        self.assertIn("No hay datos para lo que definiste", html)
        self.assertNotIn("Descargar CSV", html)

    def test_un_periodo_sin_datos_tambien(self):
        self.como_admin()
        self.agregar_cliente_ajeno()
        self.insertar(cliente_id=2)
        html = self.html("/admin/reportes?tipo=solicitudes&desde=2030-01-01")
        self.assertIn("Reporte vacío", html)


class PantallaDeReportesTest(GestionBase):
    def setUp(self):
        super().setUp()
        self.agregar_cliente_ajeno()

    # --- acceso --------------------------------------------------------------------

    def test_exige_sesion(self):
        for ruta in ("/admin/reportes", "/admin/reportes?tipo=reclamos", "/admin/reportes/descargar?tipo=reclamos"):
            r = self.client.get(ruta)
            self.assertEqual(r.status_code, 302, ruta)
            self.assertIn("/login", r.headers["Location"])

    def test_un_cliente_no_entra(self):
        self.como_cliente()
        for ruta in ("/admin/reportes", "/admin/reportes?tipo=reclamos", "/admin/reportes/descargar?tipo=reclamos"):
            self.assertEqual(self.client.get(ruta).status_code, 403, ruta)

    # --- definir y armar --------------------------------------------------------------

    def test_sin_parametros_solo_se_muestra_el_formulario(self):
        self.como_admin()
        r = self.client.get("/admin/reportes")
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Definir reporte", html)
        self.assertNotIn("Reporte vacío", html)
        self.assertNotIn("Datos de todo el período", html)

    def test_el_formulario_ofrece_los_tipos_y_los_estados(self):
        self.como_admin()
        html = self.html("/admin/reportes")
        for texto in ("Solicitudes", "Reclamos", "Facturación", "Pendiente", "Escalado", "Falla en PagoNet"):
            self.assertIn(texto, html)

    def test_se_arma_el_reporte_de_solicitudes(self):
        self.como_admin()
        self.insertar(cliente_id=2, detalle="x", plan_id=3, prioridad="alta")
        html = self.html("/admin/reportes?tipo=solicitudes")
        self.assertIn("Reporte de solicitudes", html)
        self.assertIn("Total de solicitudes", html)
        self.assertIn("Galo Roselli", html)
        self.assertIn("Plan Premium", html)
        self.assertIn("Descargar CSV", html)

    def test_se_arma_el_reporte_de_facturacion(self):
        self.como_admin()
        self.insertar_factura(estado="pagada", cliente_id=2, monto="9000.00")
        html = self.html("/admin/reportes?tipo=facturacion")
        self.assertIn("Reporte de facturación", html)
        self.assertIn("Total cobrado", html)
        self.assertIn("$ 9.000,00", html)

    def test_se_arma_el_reporte_de_reclamos(self):
        self.como_admin()
        self.insertar_reclamo(cliente_id=2, asunto="ASUNTO-DEL-RECLAMO")
        html = self.html("/admin/reportes?tipo=reclamos")
        self.assertIn("Reporte de reclamos", html)
        self.assertIn("ASUNTO-DEL-RECLAMO", html)

    def test_el_formulario_recuerda_lo_definido(self):
        self.como_admin()
        html = self.html("/admin/reportes?tipo=reclamos&desde=2026-01-01&hasta=2026-12-31&estado=resuelto")
        self.assertIn('value="2026-01-01"', html)
        self.assertIn('value="2026-12-31"', html)
        self.assertIn('<option value="reclamos" selected>', html)

    def test_una_definicion_invalida_muestra_los_errores(self):
        self.como_admin()
        casos = {
            "/admin/reportes?tipo=": "Elegí qué querés reportar",
            "/admin/reportes?tipo=reclamos&desde=2026-13-45": "Ingresá una fecha válida",
            "/admin/reportes?tipo=reclamos&desde=2026-05-01&hasta=2026-04-01": "no puede ser anterior",
            "/admin/reportes?tipo=reclamos&estado=pagada": "Ese estado no existe",
        }
        for ruta, texto in casos.items():
            r = self.client.get(ruta)
            self.assertEqual(r.status_code, 400, ruta)
            self.assertIn(texto, r.get_data(as_text=True))

    def test_armar_un_reporte_queda_en_el_registro(self):
        self.como_admin()
        self.insertar(cliente_id=2)
        self.client.get("/admin/reportes?tipo=solicitudes")
        entrada = self.store.registro[-1]
        self.assertEqual(entrada["accion"], "Reporte armado")
        self.assertIn("Reporte de solicitudes", entrada["detalle"])
        self.assertIn("1 fila", entrada["detalle"])

    # --- descarga ------------------------------------------------------------------------

    def test_se_descarga_el_reporte_en_csv(self):
        self.como_admin()
        self.insertar(cliente_id=2, plan_id=3)
        r = self.client.get("/admin/reportes/descargar?tipo=solicitudes")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "text/csv")
        self.assertIn("attachment", r.headers["Content-Disposition"])
        self.assertIn("reporte-solicitudes-", r.headers["Content-Disposition"])
        self.assertTrue(r.headers["Content-Disposition"].rstrip('"').endswith(".csv"))

    def test_el_csv_se_abre_bien_en_excel(self):
        self.como_admin()
        self.insertar(cliente_id=2, plan_id=3)
        texto = self.client.get("/admin/reportes/descargar?tipo=solicitudes").data.decode("utf-8")
        self.assertTrue(texto.startswith("\ufeff"))  # BOM para los acentos
        lineas = texto.splitlines()
        self.assertIn("Reporte de solicitudes", lineas[0])
        self.assertEqual(lineas[1], "N.º;Cliente;Tipo;Plan pedido;Prioridad;Estado;Fecha")
        self.assertTrue(lineas[2].startswith("#1;Galo Roselli;Cambio de plan;Plan Premium;Media;Pendiente;"))
        self.assertIn("Total de solicitudes;1", lineas)

    def test_el_csv_respeta_los_filtros(self):
        self.como_admin()
        self.insertar(cliente_id=2, estado="pendiente", detalle="a")
        self.insertar(cliente_id=2, estado="realizado", detalle="b")
        texto = self.client.get("/admin/reportes/descargar?tipo=solicitudes&estado=realizado").data.decode("utf-8")
        self.assertIn("#2;", texto)
        self.assertNotIn("#1;", texto)

    def test_no_se_descarga_un_reporte_vacio(self):
        self.como_admin()
        r = self.client.get("/admin/reportes/descargar?tipo=reclamos")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/reportes", r.headers["Location"])
        self.assertIn("No hay datos para descargar", self.html("/admin/reportes"))

    def test_no_se_descarga_con_una_definicion_invalida(self):
        self.como_admin()
        r = self.client.get("/admin/reportes/descargar?tipo=ventas")
        self.assertEqual(r.status_code, 302)
        self.assertIn("Revisá la definición del reporte", self.html("/admin/reportes"))

    def test_el_boton_de_descarga_conserva_la_definicion(self):
        self.como_admin()
        self.insertar(cliente_id=2)
        html = self.html("/admin/reportes?tipo=solicitudes&estado=pendiente")
        self.assertIn("/admin/reportes/descargar?tipo=solicitudes", html)
        self.assertIn("estado=pendiente", html)
