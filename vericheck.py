"""Simulador de VeriCheck, el servicio externo de validación de identidad.

No hace ninguna llamada de red: consulta un padrón de prueba en memoria. Los
nombres y DNI de abajo son inventados, solo sirven para probar el sistema.
Cuando exista el servicio real, alcanza con reemplazar esta clase por otra que
tenga el mismo método `validar`.
"""
import unicodedata
from dataclasses import dataclass
from typing import Optional

PADRON_DEMO = {
    "45786322": "Lucas Salvarrey",
    "28999111": "Galo Roselli",
}


@dataclass
class Resultado:
    valido: bool
    motivo: Optional[str] = None


def _tokens(nombre):
    """Normaliza un nombre: sin tildes, en minúsculas y sin importar el orden."""
    sin_tildes = unicodedata.normalize("NFKD", nombre or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sorted(sin_tildes.lower().split())


class VeriCheckSimulado:
    def __init__(self, padron=None):
        self.padron = dict(PADRON_DEMO if padron is None else padron)

    def validar(self, dni, nombre):
        nombre_registrado = self.padron.get(dni)
        if nombre_registrado is None:
            return Resultado(False, "El DNI ingresado no figura en el registro de identidades.")
        if _tokens(nombre) != _tokens(nombre_registrado):
            return Resultado(False, "El nombre ingresado no coincide con el DNI.")
        return Resultado(True)
