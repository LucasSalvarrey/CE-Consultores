"""Pantallas de planes: catálogo (HU-08.1), alta (HU-11.1) y edición (HU-12.1)."""
from datetime import datetime

from flask import abort, current_app, flash, redirect, render_template, request, url_for

from auditoria import registrar
from auth import admin_requerido, usuario_requerido

from . import bp
from .formatos import pesos
from .validaciones import validar_plan, valores_de


def _store():
    return current_app.extensions["store"]


def _texto(campo, valor):
    """Un valor de un plan, legible para el registro de cambios."""
    if valor is None:
        return "sin definir"
    if campo == "costo_mensual":
        return f"$ {pesos(valor)}"
    if campo == "sla_horas":
        return f"{valor} h"
    return str(valor)


@bp.get("/planes")
@usuario_requerido
def catalogo():
    """HU-08.1: lista de planes con descripción, costo mensual y SLA."""
    planes = sorted(_store().planes.values(), key=lambda p: p["id"])
    return render_template("catalogo.html", planes=planes)


@bp.route("/planes/nuevo", methods=["GET", "POST"])
@admin_requerido
def plan_nuevo():
    """HU-11.1: el administrador crea un plan."""
    store = _store()
    textos = {"titulo": "Nuevo plan", "boton": "Crear plan"}

    if request.method == "GET":
        return render_template("plan_form.html", valores={}, errores={}, **textos)

    datos, errores = validar_plan(request.form, store)
    if errores:
        return render_template(
            "plan_form.html", valores=request.form, errores=errores, **textos
        ), 400

    plan_id = store.siguiente_id("planes")
    store.planes[plan_id] = {
        "id": plan_id,
        **datos,
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
    registrar(
        "Plan creado", "plan", ref=plan_id,
        detalle=f"{datos['nombre']} · $ {pesos(datos['costo_mensual'])} · SLA {datos['sla_horas']} h",
    )
    flash(f"Se creó el plan «{datos['nombre']}».")
    return redirect(url_for("planes.catalogo"))


@bp.route("/planes/<int:plan_id>/editar", methods=["GET", "POST"])
@admin_requerido
def plan_editar(plan_id):
    """HU-12.1: el administrador modifica un plan existente."""
    store = _store()
    plan = store.planes.get(plan_id)
    if plan is None:
        abort(404)
    textos = {"titulo": "Editar plan", "boton": "Guardar cambios"}

    if request.method == "GET":
        return render_template(
            "plan_form.html", valores=valores_de(plan), errores={}, **textos
        )

    datos, errores = validar_plan(request.form, store, excluir_id=plan_id)
    if errores:
        return render_template(
            "plan_form.html", valores=request.form, errores=errores, **textos
        ), 400

    if all(plan[campo] == valor for campo, valor in datos.items()):
        flash("No hiciste ningún cambio.")
    else:
        cambios = [
            f"{campo}: {_texto(campo, plan[campo])} → {_texto(campo, valor)}"
            for campo, valor in datos.items() if plan[campo] != valor
        ]
        # `plan` es el mismo diccionario que guarda el Store: se actualiza ahí.
        plan.update(datos)
        registrar("Plan modificado", "plan", ref=plan_id, detalle=" · ".join(cambios))
        plan["modificado"] = datetime.now().isoformat(timespec="seconds")
        flash(f"Se actualizó el plan «{datos['nombre']}».")
    return redirect(url_for("planes.catalogo"))