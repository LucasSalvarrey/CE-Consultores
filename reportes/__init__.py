"""Reportes de gestión (HU-32, HU-33 y HU-34).

El administrador define qué quiere ver (HU-32): solicitudes, reclamos o
facturación, un período y, si quiere, un estado. El sistema arma el reporte con
una tabla y un resumen (HU-33). Si no hay datos para lo que se definió, lo
informa en lugar de mostrar una tabla vacía (HU-34). Todo reporte con datos se
puede descargar en CSV para abrirlo en Excel.

El paquete se reparte así:
    validaciones.py   qué se acepta al definir un reporte
    armado.py         arma el reporte: filas y resumen (no sabe nada de Flask)
    rutas.py          las pantallas
"""
from flask import Blueprint

bp = Blueprint("reportes", __name__)

# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas  # noqa: E402,F401
