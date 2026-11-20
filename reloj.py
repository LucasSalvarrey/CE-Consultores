"""Reloj de la aplicación, con paso del tiempo simulado.

Sirve para probar el vencimiento del SLA de un reclamo sin esperar horas
reales: el administrador "avanza" el reloj y el sistema revisa los plazos.
"""
from datetime import datetime, timedelta


class Reloj:
    def __init__(self):
        self.horas_simuladas = 0

    def ahora(self):
        return datetime.now() + timedelta(hours=self.horas_simuladas)

    def avanzar(self, horas):
        self.horas_simuladas += horas
