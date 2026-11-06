import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

PASSWORD = "clave-segura-1"


class PerfilTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "CARGAR_DATOS": False})
        self.client = self.app.test_client()
        self.store = self.app.extensions["store"]
        # Lucas (id 1) y Galo (id 2) figuran en el padrón de prueba de VeriCheck.
        self.registrar("Lucas Salvarrey", "45786322", "lucas@ejemplo.com", "+54 11 5555-1234")
        self.registrar("Galo Roselli", "28999111", "galo@ejemplo.com", "+54 11 4444-0000")
        self.client.post("/logout")
        self.login("lucas@ejemplo.com")

    def registrar(self, nombre, dni, email, telefono):
        self.client.post("/registro", data={
            "nombre": nombre, "dni": dni, "email": email, "telefono": telefono,
            "plan_id": "1", "password": PASSWORD, "password2": PASSWORD,
        })

    def login(self, email):
        return self.client.post("/login", data={"email": email, "password": PASSWORD})

    def editar(self, **cambios):
        datos = {"email": "lucas@ejemplo.com", "telefono": "+54 11 5555-1234"}
        datos.update(cambios)
        return self.client.post("/mi-cuenta/editar", data=datos)

    # --- acceso -----------------------------------------------------------

    def test_requiere_sesion(self):
        self.client.post("/logout")
        r = self.client.get("/mi-cuenta/editar")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login?next=/mi-cuenta/editar", r.headers["Location"])

    def test_sin_sesion_no_se_puede_modificar(self):
        self.client.post("/logout")
        r = self.editar(email="hack@ejemplo.com")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.store.clientes[1]["email"], "lucas@ejemplo.com")

    def test_mi_cuenta_tiene_link_para_editar(self):
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertIn("/mi-cuenta/editar", html)

    # --- formulario -------------------------------------------------------

    def test_formulario_viene_con_los_datos_actuales(self):
        html = self.client.get("/mi-cuenta/editar").get_data(as_text=True)
        self.assertIn('value="lucas@ejemplo.com"', html)
        self.assertIn('value="+54 11 5555-1234"', html)

    def test_nombre_y_dni_se_muestran_pero_no_se_editan(self):
        html = self.client.get("/mi-cuenta/editar").get_data(as_text=True)
        self.assertIn("Lucas Salvarrey", html)
        self.assertIn("45786322", html)
        self.assertNotIn('name="nombre"', html)
        self.assertNotIn('name="dni"', html)

    def test_nombre_y_dni_enviados_a_mano_se_ignoran(self):
        self.editar(telefono="+54 11 7777-8888", nombre="Otro Nombre", dni="11111111")
        c = self.store.clientes[1]
        self.assertEqual(c["nombre"], "Lucas Salvarrey")
        self.assertEqual(c["dni"], "45786322")
        self.assertEqual(c["telefono"], "+54 11 7777-8888")

    # --- cambios válidos --------------------------------------------------

    def test_modifica_email_y_telefono(self):
        r = self.editar(email="lucas.nuevo@ejemplo.com", telefono="+54 351 444-5555")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))
        c = self.store.clientes[1]
        self.assertEqual(c["email"], "lucas.nuevo@ejemplo.com")
        self.assertEqual(c["telefono"], "+54 351 444-5555")
        self.assertIn("modificado", c)

    def test_muestra_confirmacion_y_los_datos_nuevos(self):
        r = self.client.post("/mi-cuenta/editar", follow_redirects=True, data={
            "email": "lucas.nuevo@ejemplo.com", "telefono": "+54 351 444-5555"})
        html = r.get_data(as_text=True)
        self.assertIn("Tus datos se actualizaron correctamente", html)
        self.assertIn("lucas.nuevo@ejemplo.com", html)

    def test_la_confirmacion_se_muestra_una_sola_vez(self):
        self.client.post("/mi-cuenta/editar", follow_redirects=True, data={
            "email": "lucas.nuevo@ejemplo.com", "telefono": "+54 351 444-5555"})
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertNotIn("se actualizaron", html)

    def test_email_se_guarda_limpio_y_en_minusculas(self):
        self.editar(email="  LUCAS.Nuevo@Ejemplo.COM ")
        self.assertEqual(self.store.clientes[1]["email"], "lucas.nuevo@ejemplo.com")

    def test_puede_conservar_su_propio_email(self):
        # Cambia solo el teléfono: su email no cuenta como repetido.
        r = self.editar(telefono="+54 11 7777-8888")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.store.clientes[1]["telefono"], "+54 11 7777-8888")

    def test_sin_cambios_lo_avisa_y_no_modifica(self):
        r = self.client.post("/mi-cuenta/editar", follow_redirects=True, data={
            "email": "lucas@ejemplo.com", "telefono": "+54 11 5555-1234"})
        self.assertIn("No hiciste ningún cambio", r.get_data(as_text=True))
        self.assertNotIn("modificado", self.store.clientes[1])

    def test_con_el_email_nuevo_se_puede_iniciar_sesion(self):
        self.editar(email="lucas.nuevo@ejemplo.com")
        self.client.post("/logout")
        self.assertEqual(self.login("lucas.nuevo@ejemplo.com").status_code, 302)
        self.client.post("/logout")
        self.assertEqual(self.login("lucas@ejemplo.com").status_code, 401)
        self.client.post("/logout")
    # --- cambios inválidos ------------------------------------------------

    def test_email_invalido(self):
        r = self.editar(email="no-es-un-email")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email válido", r.get_data(as_text=True))
        self.assertEqual(self.store.clientes[1]["email"], "lucas@ejemplo.com")

    def test_telefono_invalido(self):
        r = self.editar(telefono="abc")
        self.assertEqual(r.status_code, 400)
        self.assertIn("teléfono válido", r.get_data(as_text=True))
        self.assertEqual(self.store.clientes[1]["telefono"], "+54 11 5555-1234")

    def test_campos_vacios(self):
        r = self.client.post("/mi-cuenta/editar", data={})
        self.assertEqual(r.status_code, 400)
        html = r.get_data(as_text=True)
        self.assertIn("email válido", html)
        self.assertIn("teléfono válido", html)

    def test_email_de_otro_cliente(self):
        r = self.editar(email="galo@ejemplo.com")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya existe un cliente", r.get_data(as_text=True))
        self.assertEqual(self.store.clientes[1]["email"], "lucas@ejemplo.com")

    def test_si_hay_un_error_no_se_guarda_ningun_campo(self):
        # El teléfono es válido pero el email no: no se guarda ninguno de los dos.
        self.editar(email="malo", telefono="+54 11 7777-8888")
        self.assertEqual(self.store.clientes[1]["telefono"], "+54 11 5555-1234")

    def test_error_conserva_lo_escrito(self):
        html = self.editar(email="malo", telefono="+54 11 7777-8888").get_data(as_text=True)
        self.assertIn('value="malo"', html)
        self.assertIn('value="+54 11 7777-8888"', html)

    def test_no_afecta_a_otros_clientes(self):
        self.editar(email="lucas.nuevo@ejemplo.com", telefono="+54 351 444-5555")
        galo = self.store.clientes[2]
        self.assertEqual(galo["email"], "galo@ejemplo.com")
        self.assertEqual(galo["telefono"], "+54 11 4444-0000")


if __name__ == "__main__":
    unittest.main()