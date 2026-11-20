"""Solicitudes de modificación de plan.

El cliente pide un alta, un cambio o la baja de su plan (HU-13), puede adjuntar
documentación (HU-15), ve cómo avanza su pedido y puede anularlo mientras siga
pendiente. El administrador valida la documentación (HU-16 y HU-17), asigna
prioridad y filtra (HU-19), y aprueba o rechaza.

Una solicitud pasa por estos estados:
    pendiente  ->  realizado    (la aprueba el administrador)
    pendiente  ->  rechazada    (la rechaza el administrador)
    pendiente  ->  anulada      (la anula el cliente)
Una solicitud realizada, rechazada o anulada ya no cambia.

Al aprobar un alta o un cambio de plan el cliente pasa al plan pedido y se
genera una factura pendiente, que el administrador cobra en «Facturación»
(HU-21). Al aprobar una baja el cliente queda sin plan y no se factura nada.
Si la solicitud tiene documentación, el administrador debe validarla antes de
poder aprobarla.

El paquete se reparte así:
    estados.py        estados, tipos y prioridades, con sus textos
    documentos.py     qué archivos se aceptan como documentación
    validaciones.py   qué se acepta en el formulario de una solicitud
    rutas.py          las pantallas del cliente y el panel del administrador
"""
from flask import Blueprint

from .estados import doc_etiqueta, etiqueta, prioridad_etiqueta, tipo_etiqueta

bp = Blueprint("solicitudes", __name__)

# Los filtros quedan disponibles en todos los templates: {{ estado|estado_solicitud }}
bp.add_app_template_filter(etiqueta, "estado_solicitud")
bp.add_app_template_filter(tipo_etiqueta, "tipo_solicitud")
bp.add_app_template_filter(prioridad_etiqueta, "prioridad_solicitud")
bp.add_app_template_filter(doc_etiqueta, "doc_estado")

# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas
