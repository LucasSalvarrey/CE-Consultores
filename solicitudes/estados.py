"""Estados posibles de una solicitud y cómo se muestran en pantalla."""
PENDIENTE = "pendiente"
REALIZADO = "realizado"
ANULADA = "anulada"
RECHAZADA = "rechazada"

ETIQUETAS = {
    PENDIENTE: "Pendiente",
    REALIZADO: "Realizado",
    ANULADA: "Anulada",
    RECHAZADA: "Rechazada",
}


def etiqueta(estado):
    """Texto para mostrar: 'realizado' -> 'Realizado'."""
    return ETIQUETAS.get(estado, estado)
