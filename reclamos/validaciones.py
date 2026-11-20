"""Reglas de los formularios de reclamos."""
import unicodedata

from .estados import CANALES

MAX_ASUNTO = 100
MAX_TEXTO = 1000


def normalizar_asunto(texto):
    """Para comparar asuntos: sin tildes, en minúsculas y sin espacios de más.

    'Cobro  Duplicado' y 'cobro duplicádo' se consideran el mismo asunto.
    """
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def validar_reclamo(form):
    """Valida el formulario de un reclamo nuevo. Devuelve (datos, errores)."""
    errores = {}

    asunto = " ".join((form.get("asunto") or "").split())
    if not asunto:
        errores["asunto"] = "Ingresá el asunto del reclamo."
    elif len(asunto) > MAX_ASUNTO:
        errores["asunto"] = f"El asunto no puede superar los {MAX_ASUNTO} caracteres."

    detalle = (form.get("detalle") or "").strip()
    if not detalle:
        errores["detalle"] = "Contanos qué pasó."
    elif len(detalle) > MAX_TEXTO:
        errores["detalle"] = f"El detalle no puede superar los {MAX_TEXTO} caracteres."

    canal = form.get("canal") or ""
    if canal not in CANALES:
        errores["canal"] = "Elegí por qué canal nos escribís."

    return {"asunto": asunto, "detalle": detalle, "canal": canal}, errores


def validar_mensaje(form):
    """Valida un mensaje dentro de un reclamo. Devuelve (texto, error)."""
    texto = (form.get("texto") or "").strip()
    if not texto:
        return texto, "Escribí un mensaje."
    if len(texto) > MAX_TEXTO:
        return texto, f"El mensaje no puede superar los {MAX_TEXTO} caracteres."
    return texto, None
