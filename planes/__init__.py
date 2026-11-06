from flask import Blueprint

from .formatos import pesos

bp = Blueprint("planes", __name__)

# El filtro queda disponible en todos los templates: {{ valor|pesos }}
bp.add_app_template_filter(pesos, "pesos")

# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas