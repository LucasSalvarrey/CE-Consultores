"""Reglas del formulario de una solicitud de modificación de plan."""

MAX_DETALLE = 500


def validar_solicitud(form, store, plan_actual_id):
    """Valida el formulario. Devuelve (datos, errores).

    `plan_actual_id` es el plan que el cliente ya tiene: pedir el mismo plan no
    es una modificación.
    """
    errores = {}

    plan_id = None
    texto_plan = (form.get("plan_id") or "").strip()
    if texto_plan.isascii() and texto_plan.isdigit():
        plan_id = int(texto_plan)
    if plan_id not in store.planes:
        errores["plan_id"] = "Elegí un plan de la lista."
    elif plan_id == plan_actual_id:
        errores["plan_id"] = "Ya tenés contratado ese plan. Elegí otro."

    detalle = (form.get("detalle") or "").strip()
    if not detalle:
        errores["detalle"] = "Contanos qué querés modificar."
    elif len(detalle) > MAX_DETALLE:
        errores["detalle"] = f"El detalle no puede superar los {MAX_DETALLE} caracteres."

    return {"plan_id": plan_id, "detalle": detalle}, errores
