"""Reglas del formulario de un plan (alta y edición)."""
import re
from decimal import Decimal

# Costo: dígitos y, opcionalmente, coma o punto con 1 o 2 decimales.
# No se acepta separador de miles: "12.500" sería ambiguo (¿12,50 o 12500?).
COSTO_RE = re.compile(r"^\d{1,9}([.,]\d{1,2})?$", re.ASCII)


def validar_plan(form, store, excluir_id=None):
    """Valida el formulario de un plan. Devuelve (datos, errores).

    `excluir_id` es el plan que se está editando: su propio nombre actual no
    cuenta como repetido.
    """
    errores = {}

    # " ".join(split()) colapsa espacios repetidos: "Plan   Oro " -> "Plan Oro"
    nombre = " ".join((form.get("nombre") or "").split())
    if not nombre:
        errores["nombre"] = "Ingresá el nombre del plan."
    elif len(nombre) > 60:
        errores["nombre"] = "El nombre no puede superar los 60 caracteres."
    elif any(
        p["nombre"].lower() == nombre.lower() and p["id"] != excluir_id
        for p in store.planes.values()
    ):
        errores["nombre"] = "Ya existe un plan con ese nombre."

    descripcion = (form.get("descripcion") or "").strip()
    if not descripcion:
        errores["descripcion"] = "Ingresá una descripción."
    elif len(descripcion) > 300:
        errores["descripcion"] = "La descripción no puede superar los 300 caracteres."

    costo = None
    texto_costo = (form.get("costo_mensual") or "").strip()
    if COSTO_RE.match(texto_costo):
        costo = Decimal(texto_costo.replace(",", ".")).quantize(Decimal("0.01"))
    if costo is None or costo <= 0:
        errores["costo_mensual"] = (
            "Ingresá un costo mayor a cero, sin separador de miles (ej.: 12500 o 12500,50)."
        )

    sla = None
    texto_sla = (form.get("sla_horas") or "").strip()
    if texto_sla.isascii() and texto_sla.isdigit() and 1 <= int(texto_sla) <= 9999:
        sla = int(texto_sla)
    else:
        errores["sla_horas"] = "Ingresá el SLA como un número entero de horas (1 o más)."

    datos = {
        "nombre": nombre,
        "descripcion": descripcion,
        "costo_mensual": costo,
        "sla_horas": sla,
    }
    return datos, errores


def valores_de(plan):
    """Los datos de un plan como texto, para precargar el formulario de edición."""
    costo = plan["costo_mensual"]
    return {
        "nombre": plan["nombre"],
        "descripcion": plan["descripcion"] or "",
        "costo_mensual": f"{costo:.2f}".replace(".", ",") if costo is not None else "",
        "sla_horas": plan["sla_horas"] if plan["sla_horas"] is not None else "",
    }