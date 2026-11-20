"""Ayudas compartidas por los tests: bases de planes y de registro."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin-clave-test-1"
CLIENTE_PASSWORD = "clave-segura-1"


class PlanesBase(unittest.TestCase):
    """Base de los tests de planes: app limpia y atajos para entrar como admin o cliente."""

    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "CARGAR_DATOS": False,
            "ADMIN_EMAIL": ADMIN_EMAIL,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
        })
        self.client = self.app.test_client()
        self.store = self.app.extensions["store"]

    # --- ayudas -----------------------------------------------------------

    def login(self, email, password):
        return self.client.post("/login", data={"email": email, "password": password})

    def como_admin(self):
        return self.login(ADMIN_EMAIL, ADMIN_PASSWORD)

    def como_cliente(self):
        # Lucas Salvarrey figura en el padrón de prueba de VeriCheck.
        self.client.post("/registro", data={
            "nombre": "Lucas Salvarrey", "dni": "45786322", "email": "lucas@ejemplo.com",
            "telefono": "+54 11 5555-1234", "plan_id": "1",
            "password": CLIENTE_PASSWORD, "password2": CLIENTE_PASSWORD,
        })
        # El registro ya deja a Lucas con la sesión iniciada.
        with self.client.session_transaction() as s:
            self.assertEqual(s.get("cliente_id"), 1)

    def crear_plan(self, **cambios):
        datos = {
            "nombre": "Plan Empresarial",
            "descripcion": "Atención prioritaria",
            "costo_mensual": "12500",
            "sla_horas": "24",
        }
        datos.update(cambios)
        return self.client.post("/planes/nuevo", data=datos)

    def editar_plan(self, plan_id=1, **cambios):
        datos = {
            "nombre": "Plan Básico",
            "descripcion": "Descripción nueva",
            "costo_mensual": "9000",
            "sla_horas": "48",
        }
        datos.update(cambios)
        return self.client.post(f"/planes/{plan_id}/editar", data=datos)


def datos_validos(**cambios):
    """Lucas Salvarrey, DNI 45786322, figura en el padrón de prueba de VeriCheck."""
    datos = {
        "nombre": "Lucas Salvarrey",
        "dni": "45.786.322",
        "email": "lucas@ejemplo.com",
        "telefono": "+54 11 5555-1234",
        "plan_id": "1",
        "password": "clave-segura-1",
        "password2": "clave-segura-1",
    }
    datos.update(cambios)
    return datos


class RegistroBase(unittest.TestCase):
    """Base de los tests de registro: app sin datos de ejemplo y el atajo `registrar`."""

    def setUp(self):
        # Sin datos de ejemplo: cada test arranca con la memoria vacía y
        # registra por su cuenta a Lucas Salvarrey (que en la app real ya existe).
        self.app = create_app({"TESTING": True, "CARGAR_DATOS": False})
        self.client = self.app.test_client()
        self.store = self.app.extensions["store"]

    def registrar(self, **cambios):
        return self.client.post("/registro", data=datos_validos(**cambios))