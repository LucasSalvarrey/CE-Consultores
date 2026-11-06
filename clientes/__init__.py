"""Gestión de clientes (CU01).

Implementa el registro de personas (HU-01.1 y HU-01.2) con validación
automática de identidad en VeriCheck (HU-02.1). Si VeriCheck rechaza los
datos, no se crea la cuenta y se muestra el motivo (HU-03.1). Si los valida,
la cuenta queda habilitada y se muestra la bienvenida (HU-07.1).

Además, el cliente con sesión iniciada puede modificar su email y su teléfono
(HU-04.1). El nombre y el DNI no se editan porque los validó VeriCheck.

El paquete se reparte así:
    validaciones.py   qué se acepta en los formularios de registro y de perfil
    rutas.py          las pantallas: registro, mi cuenta y editar perfil
"""
from flask import Blueprint

bp = Blueprint("clientes", __name__)

# Se importa al final porque rutas.py necesita el `bp` que se creó arriba.
from . import rutas 