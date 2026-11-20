"""HU-01.1 y HU-01.2: datos del registro y plan inicial."""
import unittest

from ayudas import RegistroBase


class RegistroTest(RegistroBase):
    """HU-01.1 y HU-01.2: datos del registro y plan inicial."""

    def test_formulario_se_muestra(self):
        r = self.client.get("/registro")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("Plan inicial", html)
        self.assertIn("DNI", html)

    def test_formulario_no_tiene_empresa_ni_cuit(self):
        html = self.client.get("/registro").get_data(as_text=True)
        self.assertNotIn("Empresa", html)
        self.assertNotIn("CUIT", html)

    def test_registro_valido_crea_cliente(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.store.clientes), 1)
        c = self.store.clientes[1]
        self.assertEqual(c["dni"], "45786322")  # sin puntos
        self.assertEqual(c["email"], "lucas@ejemplo.com")  # en minúsculas
        self.assertEqual(c["plan_id"], 1)
        self.assertNotIn("empresa", c)

    def test_contrasena_no_se_guarda_en_texto_plano(self):
        self.registrar()
        c = self.store.clientes[1]
        self.assertNotIn("password", c)
        self.assertNotEqual(c["password_hash"], "clave-segura-1")

    def test_campos_obligatorios_vacios(self):
        r = self.client.post("/registro", data={})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.store.clientes), 0)
        html = r.get_data(as_text=True)
        for mensaje in ("nombre completo", "DNI válido", "email válido",
                        "teléfono válido", "al menos 8", "plan de la lista"):
            self.assertIn(mensaje, html)

    def test_dni_invalido(self):
        # Un CUIT (11 dígitos) tampoco se acepta: el sistema es solo para personas.
        for malo in ("abc", "123", "20123456783"):
            self.assertEqual(self.registrar(dni=malo).status_code, 400, malo)
        self.assertEqual(len(self.store.clientes), 0)

    def test_email_invalido(self):
        self.assertEqual(self.registrar(email="no-es-un-email").status_code, 400)

    def test_contrasenas_distintas(self):
        r = self.registrar(password2="otra-clave-123")
        self.assertEqual(r.status_code, 400)
        self.assertIn("no coinciden", r.get_data(as_text=True))

    def test_contrasena_corta(self):
        self.assertEqual(self.registrar(password="corta", password2="corta").status_code, 400)

    def test_plan_inexistente(self):
        self.assertEqual(self.registrar(plan_id="99").status_code, 400)
        self.assertEqual(self.registrar(plan_id="abc").status_code, 400)

    def test_dni_duplicado(self):
        self.registrar()
        r = self.registrar(email="otro@ejemplo.com")
        self.assertEqual(r.status_code, 400)
        self.assertIn("ese DNI", r.get_data(as_text=True))
        self.assertEqual(len(self.store.clientes), 1)

    def test_email_duplicado(self):
        self.registrar()
        r = self.registrar(dni="28999111", nombre="Galo Roselli", email="galo@ejemplo.com")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.store.clientes), 1)

    def test_error_conserva_datos_pero_no_contrasenas(self):
        r = self.registrar(email="malo")
        html = r.get_data(as_text=True)
        self.assertIn("Lucas Salvarrey", html)
        self.assertNotIn("clave-segura-1", html)


if __name__ == "__main__":
    unittest.main()