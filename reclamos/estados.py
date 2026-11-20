"""Estados y canales de un reclamo, y cómo se muestran en pantalla."""
PENDIENTE = "pendiente"
ESCALADO = "escalado"
RESUELTO = "resuelto"
ANULADO = "anulado"

ETIQUETAS = {
    PENDIENTE: "Pendiente",
    ESCALADO: "Escalado",
    RESUELTO: "Resuelto",
    ANULADO: "Anulado",
}

# Un reclamo está «abierto» mientras alguien tiene que ocuparse de él.
ABIERTOS = (PENDIENTE, ESCALADO)

CANALES = {"web": "Web", "whatsapp": "WhatsApp", "telefono": "Teléfono"}


def etiqueta(estado):
    return ETIQUETAS.get(estado, estado)


def canal_etiqueta(canal):
    return CANALES.get(canal, canal)
