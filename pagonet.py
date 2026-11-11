"""Simulador de PagoNet, el servicio externo de facturación y cobros.

No hace ninguna llamada de red: aplica una regla simple de prueba. Cuando
exista el servicio real, alcanza con reemplazar esta clase por otra que tenga
el mismo método `procesar_facturacion`.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoPago:
    aprobado: bool
    motivo: Optional[str] = None


class PagoNetSimulado:
    def procesar_facturacion(self, datos_factura):
        """Recibe los datos de la factura (`cliente_id`, `plan_id` y `monto`).

        Rechaza el cobro si el plan no tiene un costo mensual mayor a cero:
        no hay nada que facturar.
        """
        monto = datos_factura.get("monto")
        if monto is None:
            return ResultadoPago(False, "el plan no tiene un costo mensual definido.")
        if monto <= 0:
            return ResultadoPago(False, "el monto a facturar debe ser mayor a cero.")
        return ResultadoPago(True)
