"""Reclamos de los clientes (HU-24 a HU-31).

El cliente ingresa un reclamo (HU-24). Si ya tiene uno abierto sobre el mismo
asunto no se crea otro: se suma su mensaje al existente y se lo avisa (HU-28,
reclamo duplicado). El administrador responde (HU-27), actualiza el estado
(HU-30) y el cliente recibe un aviso de cada novedad (HU-31).

Cada reclamo tiene un SLA: las horas que tiene el sistema para atenderlo, según
el plan del cliente (48 h si no tiene plan o su plan no define SLA). Si pasa ese
tiempo sin respuesta, el reclamo se escala solo (HU-29). El paso del tiempo es
simulado: el administrador puede avanzar el reloj para verlo funcionar.

Un reclamo pasa por estos estados:
    pendiente  ->  resuelto     (el administrador lo resuelve)
    pendiente  ->  escalado     (lo escala el administrador, o el SLA vence)
    escalado   ->  resuelto
    resuelto   ->  pendiente    (el administrador lo reabre)
    pendiente  ->  anulado      (lo anula el cliente)

El paquete se reparte así:
    estados.py        estados y canales, con sus textos
    validaciones.py   qué se acepta en los formularios
    sla.py            el vencimiento del SLA y el escalado
    rutas.py          las pantallas del cliente y del administrador
"""
from flask import Blueprint

from .estados import canal_etiqueta, etiqueta

bp = Blueprint("reclamos", __name__)

bp.add_app_template_filter(etiqueta, "estado_reclamo")
bp.add_app_template_filter(canal_etiqueta, "canal_reclamo")

# Se importan al final porque necesitan el `bp` que se creó arriba.
from . import rutas  # noqa: E402,F401
