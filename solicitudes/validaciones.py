"""Reglas del formulario de una solicitud de modificación de plan."""
from .documentos import validar_documento

MAX_DETALLE = 500

# Valor del formulario para pedir la baja: «no adquirir ningún plan».
SIN_PLAN = "ninguno"


def validar_solicitud(form, store, plan_actual_id, documento=None):
    """Valida el formulario. Devuelve (datos, errores).

    `plan_actual_id` es el plan que el cliente ya tiene (o None si no tiene
    ninguno): pedir el mismo plan no es una modificación. `documento` es una
    tupla (nombre, contenido) con el archivo adjunto, o None si no adjuntó nada.

    El tipo de solicitud se deduce de lo que se elige:
        sin plan                 -> baja
        un plan, sin tener plan  -> alta
        un plan, teniendo otro   -> cambio
    """
    errores = {}
    tipo = None
    plan_id = None

    texto_plan = (form.get("plan_id") or "").strip()
    if texto_plan == SIN_PLAN:
        if plan_actual_id is None:
            errores["plan_id"] = "Ya no tenés un plan contratado."
        else:
            tipo = "baja"
    else:
        if texto_plan.isascii() and texto_plan.isdigit():
            plan_id = int(texto_plan)
        if plan_id not in store.planes:
            plan_id = None
            errores["plan_id"] = "Elegí un plan de la lista."
        elif plan_id == plan_actual_id:
            errores["plan_id"] = "Ya tenés contratado ese plan. Elegí otro."
        else:
            tipo = "alta" if plan_actual_id is None else "cambio"

    detalle = (form.get("detalle") or "").strip()
    if not detalle:
        errores["detalle"] = "Contanos qué querés modificar."
    elif len(detalle) > MAX_DETALLE:
        errores["detalle"] = f"El detalle no puede superar los {MAX_DETALLE} caracteres."

    adjunto = None
    if documento is not None:
        adjunto, error = validar_documento(*documento)
        if error:
            errores["documento"] = error

    return {"tipo": tipo, "plan_id": plan_id, "detalle": detalle, "adjunto": adjunto}, errores
