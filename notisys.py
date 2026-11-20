"""Simulador de NotiSys, el servicio externo de notificaciones.

No envía nada por la red: guarda los avisos en memoria para poder mostrarlos y
probarlos. Cuando exista el servicio real, alcanza con reemplazar esta clase
por otra que tenga los mismos métodos.
"""
from datetime import datetime


class NotiSysSimulado:
    def __init__(self):
        self.enviadas = []

    def enviar(self, cliente_id, evento, mensaje, enlace=None):
        """Registra un aviso para el cliente.

        `evento` dice qué lo originó (por ejemplo "realizado" o "reclamo_respondido")
        y `enlace` es la pantalla donde el cliente puede ver el detalle.
        """
        aviso = {
            "id": len(self.enviadas) + 1,
            "cliente_id": cliente_id,
            "evento": evento,
            "mensaje": mensaje,
            "enlace": enlace,
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "leido": False,
        }
        self.enviadas.append(aviso)
        return aviso

    def de_cliente(self, cliente_id):
        """Los avisos de un cliente, el más reciente primero."""
        propios = [a for a in self.enviadas if a["cliente_id"] == cliente_id]
        return list(reversed(propios))

    def sin_leer(self, cliente_id):
        """Cuántos avisos del cliente todavía no vio."""
        return sum(1 for a in self.enviadas if a["cliente_id"] == cliente_id and not a["leido"])

    def marcar_leidos(self, cliente_id):
        for aviso in self.enviadas:
            if aviso["cliente_id"] == cliente_id:
                aviso["leido"] = True
