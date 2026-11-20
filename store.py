from itertools import count

from werkzeug.security import generate_password_hash


class Store:
    def __init__(self, admin_email, admin_password):
        self._ids = {}
        self.clientes = {}
        self.solicitudes = {}
        self.facturas = {}
        self.devoluciones = {}
        self.reclamos = {}
        self.registro = []

        self.administradores = {
            1: {
                "id": 1,
                "nombre": "Benicio",
                "email": admin_email.strip().lower(),
                "password_hash": generate_password_hash(admin_password),
            }
        }

        self.planes = {
            1: {"id": 1, "nombre": "Plan Básico", "descripcion": None,
                "costo_mensual": None, "sla_horas": None},
            2: {"id": 2, "nombre": "Plan Estándar", "descripcion": None,
                "costo_mensual": None, "sla_horas": None},
            3: {"id": 3, "nombre": "Plan Premium", "descripcion": None,
                "costo_mensual": None, "sla_horas": None},
        }
        self._ids["planes"] = count(max(self.planes) + 1)

    def siguiente_id(self, coleccion):
        if coleccion not in self._ids:
            self._ids[coleccion] = count(1)
        return next(self._ids[coleccion])