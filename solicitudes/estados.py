"""Estados, tipos y prioridades de una solicitud, y cómo se muestran en pantalla."""
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

# Tipos de solicitud (HU-13): se deducen de lo que el cliente elige en el formulario.
TIPOS = {
    "alta": "Alta de plan",
    "cambio": "Cambio de plan",
    "baja": "Baja de plan",
}

# Prioridades (HU-19). La menor posición se atiende primero.
PRIORIDADES = ("alta", "media", "baja")
PRIORIDAD_ETIQUETAS = {"alta": "Alta", "media": "Media", "baja": "Baja"}
PRIORIDAD_POR_DEFECTO = "media"

# Estados de la documentación adjunta (HU-15 a HU-17).
DOC_RECIBIDA = "recibida"
DOC_VALIDADA = "validada"
DOC_ETIQUETAS = {DOC_RECIBIDA: "Recibida", DOC_VALIDADA: "Validada"}


def etiqueta(estado):
    """Texto para mostrar: 'realizado' -> 'Realizado'."""
    return ETIQUETAS.get(estado, estado)


def tipo_etiqueta(tipo):
    return TIPOS.get(tipo, "Cambio de plan")


def prioridad_etiqueta(prioridad):
    return PRIORIDAD_ETIQUETAS.get(prioridad, "Media")


def doc_etiqueta(estado):
    return DOC_ETIQUETAS.get(estado, estado)
