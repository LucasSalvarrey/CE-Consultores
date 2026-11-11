"""Pantallas de solicitudes: crear (US3), ver las propias (US5), anular (US6)
y panel del administrador (US4)."""
from datetime import datetime

from flask import abort, current_app, flash, redirect, render_template, request, url_for

from auth import admin_actual, admin_requerido, cliente_actual, login_requerido

from . import bp
from .estados import ANULADA, PENDIENTE, RECHAZADA, REALIZADO
from .validaciones import validar_solicitud


def _store():
    return current_app.extensions["store"]


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _notificar(solicitud, evento, mensaje):
    """Pide a NotiSys (simulado) que avise al cliente."""
    current_app.extensions["notisys"].enviar(
        solicitud["cliente_id"], solicitud["id"], evento, mensaje
    )


def _con_nombres(solicitud, store):
    """La solicitud más el nombre del cliente y del plan, para mostrarla."""
    cliente = store.clientes.get(solicitud["cliente_id"])
    plan = store.planes.get(solicitud["plan_id"])
    return {
        **solicitud,
        "cliente_nombre": cliente["nombre"] if cliente else "(cliente desconocido)",
        "plan_nombre": plan["nombre"] if plan else "(plan desconocido)",
    }


@bp.route("/solicitudes/nueva", methods=["GET", "POST"])
@login_requerido
def nueva_solicitud():
    """US3: el cliente pide cambiar de plan. Nace en estado «pendiente»."""
    store = _store()
    cliente = cliente_actual()
    planes = sorted(store.planes.values(), key=lambda p: p["id"])
    plan_actual = store.planes[cliente["plan_id"]]

    if request.method == "GET":
        return render_template(
            "solicitud_form.html", planes=planes, plan_actual=plan_actual,
            valores={}, errores={},
        )

    datos, errores = validar_solicitud(request.form, store, cliente["plan_id"])
    if errores:
        return render_template(
            "solicitud_form.html", planes=planes, plan_actual=plan_actual,
            valores=request.form, errores=errores,
        ), 400

    solicitud_id = store.siguiente_id("solicitudes")
    solicitud = {
        "id": solicitud_id,
        "cliente_id": cliente["id"],
        **datos,
        "estado": PENDIENTE,
        "creado": _ahora(),
    }
    store.solicitudes[solicitud_id] = solicitud
    _notificar(solicitud, PENDIENTE, f"Tu solicitud #{solicitud_id} quedó pendiente.")
    flash("Tu solicitud se registró y quedó pendiente.")
    return redirect(url_for("solicitudes.mis_solicitudes"))


@bp.get("/solicitudes")
@login_requerido
def mis_solicitudes():
    """US5: el cliente ve solo sus solicitudes, con su estado, y los avisos que recibió."""
    store = _store()
    cliente = cliente_actual()
    propias = [s for s in store.solicitudes.values() if s["cliente_id"] == cliente["id"]]
    propias.sort(key=lambda s: s["id"], reverse=True)
    avisos = current_app.extensions["notisys"].de_cliente(cliente["id"])[:5]
    return render_template(
        "mis_solicitudes.html",
        solicitudes=[_con_nombres(s, store) for s in propias],
        avisos=avisos,
    )


@bp.post("/solicitudes/<int:solicitud_id>/anular")
@login_requerido
def anular(solicitud_id):
    """US6: el cliente anula una solicitud suya, solo si sigue pendiente."""
    solicitud = _store().solicitudes.get(solicitud_id)
    # Una solicitud ajena responde igual que una que no existe.
    if solicitud is None or solicitud["cliente_id"] != cliente_actual()["id"]:
        abort(404)

    if solicitud["estado"] != PENDIENTE:
        flash("Solo se pueden anular solicitudes pendientes.")
    else:
        solicitud["estado"] = ANULADA
        solicitud["modificado"] = _ahora()
        flash("La solicitud se anuló.")
    return redirect(url_for("solicitudes.mis_solicitudes"))


@bp.get("/admin/solicitudes")
@admin_requerido
def panel():
    """US4: el administrador ve todas las solicitudes. Las pendientes van primero."""
    store = _store()
    todas = sorted(
        store.solicitudes.values(),
        key=lambda s: (s["estado"] != PENDIENTE, s["id"]),
    )
    return render_template(
        "panel_solicitudes.html",
        solicitudes=[_con_nombres(s, store) for s in todas],
    )


@bp.post("/admin/solicitudes/<int:solicitud_id>/realizar")
@admin_requerido
def realizar(solicitud_id):
    """US4: el administrador aprueba una solicitud pendiente.

    Se factura el plan pedido en PagoNet. Si el cobro se acepta, la solicitud
    pasa a «realizado» y el cliente cambia de plan. Si PagoNet lo rechaza, la
    solicitud queda «rechazada» y el plan del cliente no cambia.
    """
    store = _store()
    solicitud = store.solicitudes.get(solicitud_id)
    if solicitud is None:
        abort(404)

    if solicitud["estado"] != PENDIENTE:
        flash("Solo se pueden realizar solicitudes pendientes.")
        return redirect(url_for("solicitudes.panel"))

    cliente = store.clientes.get(solicitud["cliente_id"])
    plan = store.planes.get(solicitud["plan_id"])
    if cliente is None or plan is None:
        abort(404)

    datos_factura = {
        "cliente_id": cliente["id"],
        "plan_id": plan["id"],
        "monto": plan["costo_mensual"],
    }
    pago = current_app.extensions["pagonet"].procesar_facturacion(datos_factura)

    factura_id = store.siguiente_id("facturas")
    store.facturas[factura_id] = {
        "id": factura_id,
        "solicitud_id": solicitud["id"],
        **datos_factura,
        "estado": "aprobado" if pago.aprobado else "rechazado",
        "creado": _ahora(),
    }
    solicitud["factura_id"] = factura_id
    solicitud["modificado"] = _ahora()
    solicitud["resuelto_por"] = admin_actual()["id"]

    if pago.aprobado:
        cliente["plan_id"] = plan["id"]
        solicitud["estado"] = REALIZADO
        _notificar(
            solicitud, REALIZADO,
            f"Tu solicitud #{solicitud['id']} fue realizada: ahora tenés el {plan['nombre']}.",
        )
        flash("La solicitud quedó como realizada y el plan del cliente se actualizó.")
    else:
        solicitud["estado"] = RECHAZADA
        solicitud["motivo"] = f"PagoNet rechazó la facturación: {pago.motivo}"
        _notificar(
            solicitud, RECHAZADA,
            f"Tu solicitud #{solicitud['id']} fue rechazada. {solicitud['motivo']}",
        )
        flash(
            "PagoNet rechazó la facturación: la solicitud quedó rechazada "
            "y el plan del cliente no cambió."
        )
    return redirect(url_for("solicitudes.panel"))


@bp.post("/admin/solicitudes/<int:solicitud_id>/rechazar")
@admin_requerido
def rechazar(solicitud_id):
    """El administrador rechaza una solicitud pendiente, sin facturar."""
    solicitud = _store().solicitudes.get(solicitud_id)
    if solicitud is None:
        abort(404)

    if solicitud["estado"] != PENDIENTE:
        flash("Solo se pueden rechazar solicitudes pendientes.")
    else:
        solicitud["estado"] = RECHAZADA
        solicitud["motivo"] = "El administrador rechazó la solicitud."
        solicitud["modificado"] = _ahora()
        solicitud["resuelto_por"] = admin_actual()["id"]
        _notificar(
            solicitud, RECHAZADA,
            f"Tu solicitud #{solicitud['id']} fue rechazada. {solicitud['motivo']}",
        )
        flash("La solicitud quedó como rechazada.")
    return redirect(url_for("solicitudes.panel"))
