"""Facturación con PagoNet (HU-21 y HU-22).

Al aprobar el alta o el cambio de un plan se genera una factura pendiente. El
administrador la cobra con un botón (PagoNet es un simulador). Si PagoNet falla,
la factura queda en estado «fallida», aparece una alerta y el administrador la
gestiona: puede reintentar el cobro o realizar una devolución al cliente.

Una factura pasa por estos estados:
    pendiente  ->  pagada       (PagoNet confirma el cobro)
    pendiente  ->  fallida      (PagoNet falla)
    fallida    ->  pagada       (el reintento funciona)
    fallida    ->  devuelta     (el administrador devuelve el dinero al cliente)

El paquete se reparte así:
    estados.py   los estados y sus textos
    rutas.py     el listado, el cobro y la devolución
"""
from flask import Blueprint

from .estados import etiqueta

bp = Blueprint("facturacion", __name__)

bp.add_app_template_filter(etiqueta, "estado_factura")

# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas  # noqa: E402,F401
