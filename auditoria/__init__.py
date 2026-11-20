"""Registro de cambios (HU-39).

Cada vez que alguien o algo modifica datos del sistema (un cliente, un plan,
una solicitud, una factura, un reclamo) queda una entrada con la fecha, quién
fue, qué hizo y sobre qué. El administrador las consulta en «Registro».

Para dejar constancia desde cualquier pantalla:

    from auditoria import registrar
    registrar("Solicitud aprobada", "solicitud", ref=3, detalle="Pasó a realizado")

Si no se indica `actor`, se toma de la sesión: el administrador, el cliente o,
sin sesión (por ejemplo el control de SLA), «Sistema».
"""
from datetime import datetime

from flask import Blueprint, current_app

from auth import admin_actual, cliente_actual

bp = Blueprint("auditoria", __name__)

# Tipos de entidad que se registran y cómo se muestran.
ENTIDADES = {
    "cliente": "Cliente",
    "plan": "Plan",
    "solicitud": "Solicitud",
    "factura": "Factura",
    "reclamo": "Reclamo",
    "sistema": "Sistema",
}


def _actor_actual():
    admin = admin_actual()
    if admin is not None:
        return f"Administrador ({admin['nombre']})"
    cliente = cliente_actual()
    if cliente is not None:
        return f"Cliente ({cliente['nombre']})"
    return "Sistema"


def registrar(accion, entidad, ref=None, detalle="", actor=None):
    """Agrega una entrada al registro de cambios y la devuelve."""
    store = current_app.extensions["store"]
    entrada = {
        "id": store.siguiente_id("registro"),
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "actor": actor if actor is not None else _actor_actual(),
        "accion": accion,
        "entidad": entidad,
        "ref": ref,
        "detalle": detalle,
    }
    store.registro.append(entrada)
    return entrada


# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas  # noqa: E402,F401
