"""Estados de una factura y cómo se muestran en pantalla."""
PENDIENTE = "pendiente"
PAGADA = "pagada"
FALLIDA = "fallida"
DEVUELTA = "devuelta"

ETIQUETAS = {
    PENDIENTE: "Pendiente",
    PAGADA: "Pagada",
    FALLIDA: "Falla en PagoNet",
    DEVUELTA: "Devuelta",
}


def etiqueta(estado):
    return ETIQUETAS.get(estado, estado)
