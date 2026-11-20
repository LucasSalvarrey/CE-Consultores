"""Simulador de PagoNet, el servicio externo de facturación y cobros.

No hace ninguna llamada de red: aplica reglas simples de prueba. Cuando exista
el servicio real, alcanza con reemplazar esta clase por otra que tenga el
mismo método `procesar_facturacion`.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoPago:
    aprobado: bool
    motivo: Optional[str] = None


class PagoNetSimulado:
    def procesar_facturacion(self, datos_factura, simular_falla=False):
        """Recibe los datos de la factura (`cliente_id`, `plan_id` y `monto`).

        Con `simular_falla=True` responde como si PagoNet estuviera caído, para
        poder probar la gestión de una falla. Además rechaza un monto que no
        sea mayor a cero.
        """
        if simular_falla:
            return ResultadoPago(False, "Falla de comunicación con PagoNet (simulada): no se pudo confirmar el cobro.")
        monto = datos_factura.get("monto")
        if monto is None:
            return ResultadoPago(False, "El plan no tiene un costo mensual definido.")
        if monto <= 0:
            return ResultadoPago(False, "El monto a facturar debe ser mayor a cero.")
        return ResultadoPago(True)
