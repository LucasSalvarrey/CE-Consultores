"""HU-02.1, HU-03.1 y HU-07.1: validación de identidad con VeriCheck."""
import unittest

from ayudas import RegistroBase, datos_validos
from vericheck import VeriCheckSimulado


class ValidacionIdentidadTest(RegistroBase):
    """HU-02.1, HU-03.1 y HU-07.1: validación con VeriCheck."""

    def test_identidad_valida_habilita_la_cuenta(self):
        self.registrar()
        self.assertEqual(self.store.clientes[1]["estado"], "habilitada")

    def cliente_en_sesion(self):
        with self.client.session_transaction() as s:
            return s.get("cliente_id")

    def test_al_registrarse_va_directo_a_mi_cuenta(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/mi-cuenta"))

    def test_al_registrarse_queda_con_la_sesion_iniciada(self):
        self.registrar()
        self.assertEqual(self.cliente_en_sesion(), 1)

    def test_mi_cuenta_muestra_la_bienvenida(self):
        r = self.client.post("/registro", follow_redirects=True, data=datos_validos())
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("Bienvenido/a, Lucas Salvarrey", html)
        self.assertIn("cuenta ya está habilitada", html)
        self.assertIn("30123456", html)  # es la página Mi cuenta, con sus datos

    def test_la_bienvenida_se_muestra_una_sola_vez(self):
        self.client.post("/registro", follow_redirects=True, data=datos_validos())
        html = self.client.get("/mi-cuenta").get_data(as_text=True)
        self.assertNotIn("Bienvenido/a", html)

    def test_ya_no_existe_la_pantalla_de_confirmacion(self):
        self.registrar()
        self.assertEqual(self.client.get("/registro/1/ok").status_code, 404)

    def test_si_se_rechaza_la_identidad_no_se_inicia_sesion(self):
        self.registrar(dni="12345678")
        self.assertIsNone(self.cliente_en_sesion())

    def test_con_errores_de_formato_no_se_inicia_sesion(self):
        self.registrar(email="malo")
        self.assertIsNone(self.cliente_en_sesion())

    def test_el_registro_reemplaza_la_sesion_anterior(self):
        # Un administrador con sesión que registra a un cliente pasa a ser ese cliente.
        self.client.post("/login", data={
            "email": self.app.config["ADMIN_EMAIL"],
            "password": self.app.config["ADMIN_PASSWORD"]})
        self.registrar()
        with self.client.session_transaction() as s:
            self.assertEqual(s.get("cliente_id"), 1)
            self.assertNotIn("admin_id", s)

    def test_dni_que_no_figura_es_rechazado_y_no_crea_cuenta(self):
        r = self.registrar(dni="12345678")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(len(self.store.clientes), 0)
        html = r.get_data(as_text=True)
        self.assertIn("No pudimos validar tu identidad", html)
        self.assertIn("no figura en el registro", html)
        self.assertIn("Tu cuenta no fue creada", html)

    def test_nombre_que_no_coincide_es_rechazado(self):
        r = self.registrar(nombre="Pedro Suárez")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(len(self.store.clientes), 0)
        self.assertIn("no coincide con el DNI", r.get_data(as_text=True))

    def test_rechazo_conserva_datos_para_corregir(self):
        r = self.registrar(nombre="Pedro Suárez")
        html = r.get_data(as_text=True)
        self.assertIn("Pedro Suárez", html)
        self.assertNotIn("clave-segura-1", html)

    def test_se_puede_corregir_y_reintentar(self):
        self.assertEqual(self.registrar(nombre="Pedro Suárez").status_code, 422)
        self.assertEqual(self.registrar().status_code, 302)
        self.assertEqual(len(self.store.clientes), 1)

    def test_el_rechazo_no_consume_id_de_cliente(self):
        self.registrar(dni="12345678")
        self.registrar()
        self.assertEqual(list(self.store.clientes), [1])

    def test_nombre_tolera_tildes_mayusculas_y_orden(self):
        r = self.registrar(nombre="  Salvarrey   Lucas ")
        self.assertEqual(r.status_code, 302)

    def test_validacion_de_formato_ocurre_antes_que_vericheck(self):
        # Con el formulario incompleto ni siquiera se consulta a VeriCheck.
        class Falla(VeriCheckSimulado):
            def validar(self, dni, nombre):
                raise AssertionError("no debería consultarse")

        self.app.extensions["vericheck"] = Falla()
        self.assertEqual(self.registrar(email="malo").status_code, 400)


class VeriCheckSimuladoTest(unittest.TestCase):
    def test_valido(self):
        r = VeriCheckSimulado({"111": "Juan Díaz"}).validar("111", "juan diaz")
        self.assertTrue(r.valido)
        self.assertIsNone(r.motivo)

    def test_dni_desconocido(self):
        r = VeriCheckSimulado({}).validar("111", "Juan Díaz")
        self.assertFalse(r.valido)
        self.assertIn("no figura", r.motivo)

    def test_nombre_distinto(self):
        r = VeriCheckSimulado({"111": "Juan Díaz"}).validar("111", "Juan Gómez")
        self.assertFalse(r.valido)
        self.assertIn("no coincide", r.motivo)


if __name__ == "__main__":
    unittest.main()