"""Simulador de NotiSys, el servicio externo de notificaciones.

No envía nada por la red: guarda los avisos en memoria para poder mostrarlos y
probarlos. Cuando exista el servicio real, alcanza con reemplazar esta clase
por otra que tenga los mismos métodos `enviar` y `de_cliente`.
"""
from datetime import datetime


class NotiSysSimulado:
    def __init__(self):
        self.enviadas = []

    def enviar(self, cliente_id, solicitud_id, evento, mensaje):
        """Registra un aviso para el cliente. `evento` es el estado que lo origina."""
        aviso = {
            "cliente_id": cliente_id,
            "solicitud_id": solicitud_id,
            "evento": evento,
            "mensaje": mensaje,
            "fecha": datetime.now().isoformat(timespec="seconds"),
        }
        self.enviadas.append(aviso)
        return aviso

    def de_cliente(self, cliente_id):
        """Los avisos de un cliente, el más reciente primero."""
        propios = [a for a in self.enviadas if a["cliente_id"] == cliente_id]
        return list(reversed(propios))
