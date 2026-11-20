from datetime import datetime
from decimal import Decimal

from werkzeug.security import generate_password_hash

CLIENTE_DEMO = {
    "nombre": "Lucas Salvarrey",
    "dni": "45786322",
    "email": "lucas@ejemplo.com",
    "telefono": "+54 11 5555-1234",
    "plan_id": 1,
}
PASSWORD_DEMO = "clave-segura-2"

# Valores de ejemplo para los 3 planes iniciales, así la demo funciona de entrada.
# Los SLA son cortos a propósito: sirven para probar el escalado de reclamos.
PLANES_DEMO = {
    1: {"descripcion": "Soporte por correo en horario laboral.",
        "costo_mensual": Decimal("5000.00"), "sla_horas": 72},
    2: {"descripcion": "Soporte por correo y chat con atención prioritaria.",
        "costo_mensual": Decimal("9000.00"), "sla_horas": 48},
    3: {"descripcion": "Soporte 24/7 con un gestor de cuenta asignado.",
        "costo_mensual": Decimal("15000.00"), "sla_horas": 24},
}

SOLICITUD_DEMO = {
    "plan_id": 2,
    "detalle": "Quiero pasar al Plan Estándar para tener atención prioritaria.",
}


def cargar_datos(store):
    """Completa los planes y agrega el cliente de ejemplo (habilitado) con una solicitud pendiente."""
    for plan_id, valores in PLANES_DEMO.items():
        store.planes[plan_id].update(valores)

    cliente_id = store.siguiente_id("clientes")
    store.clientes[cliente_id] = {
        "id": cliente_id,
        **CLIENTE_DEMO,
        "password_hash": generate_password_hash(PASSWORD_DEMO),
        "estado": "habilitada",
        "creado": datetime.now().isoformat(timespec="seconds"),
    }

    solicitud_id = store.siguiente_id("solicitudes")
    store.solicitudes[solicitud_id] = {
        "id": solicitud_id,
        "cliente_id": cliente_id,
        **SOLICITUD_DEMO,
        "estado": "pendiente",
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
