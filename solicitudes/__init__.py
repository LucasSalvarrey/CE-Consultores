"""Solicitudes de modificación de plan (US3 a US6).

El cliente pide un cambio de plan (US3), ve cómo avanza su pedido (US5) y puede
anularlo mientras siga pendiente (US6). El administrador ve todas las
solicitudes y marca como realizadas las pendientes (US4).

Una solicitud pasa por estos estados:
    pendiente  ->  realizado    (el administrador la aprueba y PagoNet acepta la facturación)
    pendiente  ->  rechazada    (el administrador la rechaza, o PagoNet rechaza la facturación)
    pendiente  ->  anulada      (la anula el cliente)
Una solicitud realizada, rechazada o anulada ya no cambia.

Al aprobarla se factura el plan nuevo en PagoNet (simulado). Si el cobro se
acepta, el cliente pasa al plan pedido; si no, la solicitud queda rechazada y
su plan no cambia. NotiSys (simulado) avisa al cliente cuando la solicitud
queda pendiente, realizada o rechazada.

El paquete se reparte así:
    estados.py        los estados y sus textos
    validaciones.py   qué se acepta en el formulario de una solicitud
    rutas.py          las pantallas del cliente y el panel del administrador
"""
from flask import Blueprint

from .estados import etiqueta

bp = Blueprint("solicitudes", __name__)

# El filtro queda disponible en todos los templates: {{ estado|estado_solicitud }}
bp.add_app_template_filter(etiqueta, "estado_solicitud")

# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas
