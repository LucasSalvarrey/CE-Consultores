"""Qué se acepta al definir un reporte (HU-32)."""
from datetime import datetime

from facturacion.estados import ETIQUETAS as ESTADOS_FACTURA
from reclamos.estados import ETIQUETAS as ESTADOS_RECLAMO
from solicitudes.estados import ETIQUETAS as ESTADOS_SOLICITUD

TIPOS = {
    "solicitudes": "Solicitudes",
    "reclamos": "Reclamos",
    "facturacion": "Facturación",
}

ESTADOS_POR_TIPO = {
    "solicitudes": ESTADOS_SOLICITUD,
    "reclamos": ESTADOS_RECLAMO,
    "facturacion": ESTADOS_FACTURA,
}


def _fecha(texto):
    """Devuelve (fecha, es_valida). Un texto vacío es válido y significa «sin límite»."""
    texto = (texto or "").strip()
    if not texto:
        return None, True
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date(), True
    except ValueError:
        return None, False


def validar_definicion(args):
    """Valida lo que el administrador definió. Devuelve (definicion, errores)."""
    errores = {}

    tipo = args.get("tipo", "")
    if tipo not in TIPOS:
        errores["tipo"] = "Elegí qué querés reportar."

    desde, desde_ok = _fecha(args.get("desde"))
    if not desde_ok:
        errores["desde"] = "Ingresá una fecha válida."
    hasta, hasta_ok = _fecha(args.get("hasta"))
    if not hasta_ok:
        errores["hasta"] = "Ingresá una fecha válida."
    if desde and hasta and desde > hasta:
        errores["hasta"] = "La fecha «hasta» no puede ser anterior a «desde»."

    estado = args.get("estado", "")
    if estado and tipo in TIPOS and estado not in ESTADOS_POR_TIPO[tipo]:
        errores["estado"] = "Ese estado no existe para el tipo de reporte elegido."

    return {"tipo": tipo, "desde": desde, "hasta": hasta, "estado": estado}, errores
