"""Pantallas de solicitudes: las del cliente (crear, ver, anular) y el panel del
administrador (filtrar, priorizar, validar documentación, aprobar y rechazar)."""
from collections import Counter
from datetime import datetime
from io import BytesIO

from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for

from auditoria import registrar
from auth import (
    admin_actual, admin_requerido, cliente_actual, destino_seguro, login_requerido,
    usuario_requerido,
)

from . import bp
from .documentos import MAX_BYTES
from .estados import (
    ANULADA, DOC_RECIBIDA, DOC_VALIDADA, ETIQUETAS, PENDIENTE, PRIORIDAD_POR_DEFECTO,
    PRIORIDADES, RECHAZADA, REALIZADO, TIPOS,
)
from .validaciones import SIN_PLAN, validar_solicitud


def _store():
    return current_app.extensions["store"]


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _avisar(solicitud, evento, mensaje):
    """Pide a NotiSys (simulado) que avise al cliente."""
    current_app.extensions["notisys"].enviar(
        solicitud["cliente_id"], evento, mensaje, enlace=url_for("solicitudes.mis_solicitudes")
    )


def _volver(por_defecto):
    """A dónde volver después de una acción: el formulario puede indicarlo."""
    return redirect(destino_seguro(request.form.get("volver"), por_defecto))


def _con_nombres(solicitud, store):
    """La solicitud más los datos que hacen falta para mostrarla."""
    cliente = store.clientes.get(solicitud["cliente_id"])
    plan = store.planes.get(solicitud["plan_id"]) if solicitud["plan_id"] is not None else None
    tipo = solicitud.get("tipo", "cambio")
    return {
        **solicitud,
        "tipo": tipo,
        "prioridad": solicitud.get("prioridad", PRIORIDAD_POR_DEFECTO),
        "adjunto": solicitud.get("adjunto"),
        "cliente_nombre": cliente["nombre"] if cliente else "(cliente desconocido)",
        "plan_nombre": plan["nombre"] if plan else ("Sin plan" if tipo == "baja" else "(plan desconocido)"),
        "factura": store.facturas.get(solicitud.get("factura_id")),
    }


# --- cliente ----------------------------------------------------------------

@bp.route("/solicitudes/nueva", methods=["GET", "POST"])
@login_requerido
def nueva_solicitud():
    """El cliente pide un alta, un cambio o la baja de su plan. Nace «pendiente»."""
    store = _store()
    cliente = cliente_actual()
    planes = sorted(store.planes.values(), key=lambda p: p["id"])
    plan_actual = store.planes.get(cliente["plan_id"])
    contexto = {
        "planes": planes, "plan_actual": plan_actual,
        "sin_plan": SIN_PLAN, "max_mb": MAX_BYTES // (1024 * 1024),
    }

    if request.method == "GET":
        return render_template("solicitud_form.html", valores={}, errores={}, **contexto)

    archivo = request.files.get("documento")
    documento = None
    if archivo is not None and archivo.filename:
        documento = (archivo.filename, archivo.read(MAX_BYTES + 1))

    datos, errores = validar_solicitud(request.form, store, cliente["plan_id"], documento)
    if errores:
        return render_template(
            "solicitud_form.html", valores=request.form, errores=errores, **contexto
        ), 400

    ahora = _ahora()
    adjunto = datos["adjunto"]
    if adjunto is not None:
        adjunto["estado"] = DOC_RECIBIDA  # HU-17: la documentación queda recibida
        adjunto["recibido"] = ahora

    solicitud_id = store.siguiente_id("solicitudes")
    solicitud = {
        "id": solicitud_id,
        "cliente_id": cliente["id"],
        **datos,
        "estado": PENDIENTE,
        "prioridad": PRIORIDAD_POR_DEFECTO,
        "creado": ahora,
    }
    store.solicitudes[solicitud_id] = solicitud

    _avisar(solicitud, PENDIENTE, f"Tu solicitud #{solicitud_id} quedó pendiente.")
    detalle = TIPOS[datos["tipo"]]
    if adjunto is not None:
        _avisar(
            solicitud, "documentacion_recibida",
            f"Recibimos la documentación de tu solicitud #{solicitud_id}: {adjunto['nombre']}.",
        )
        detalle += f" · documentación adjunta: {adjunto['nombre']}"
    registrar("Solicitud creada", "solicitud", ref=solicitud_id, detalle=detalle)
    flash("Tu solicitud se registró y quedó pendiente.")
    return redirect(url_for("solicitudes.mis_solicitudes"))


@bp.get("/solicitudes")
@login_requerido
def mis_solicitudes():
    """El cliente ve solo sus solicitudes, con su estado. Las nuevas primero."""
    store = _store()
    cliente = cliente_actual()
    propias = [s for s in store.solicitudes.values() if s["cliente_id"] == cliente["id"]]
    propias.sort(key=lambda s: s["id"], reverse=True)
    return render_template(
        "mis_solicitudes.html",
        solicitudes=[_con_nombres(s, store) for s in propias],
    )


@bp.post("/solicitudes/<int:solicitud_id>/anular")
@login_requerido
def anular(solicitud_id):
    """El cliente anula una solicitud suya, solo si sigue pendiente."""
    solicitud = _store().solicitudes.get(solicitud_id)
    # Una solicitud ajena responde igual que una que no existe.
    if solicitud is None or solicitud["cliente_id"] != cliente_actual()["id"]:
        abort(404)

    if solicitud["estado"] != PENDIENTE:
        flash("Solo se pueden anular solicitudes pendientes.", "error")
    else:
        solicitud["estado"] = ANULADA
        solicitud["modificado"] = _ahora()
        registrar("Solicitud anulada", "solicitud", ref=solicitud_id, detalle="La anuló el cliente")
        flash("La solicitud se anuló.")
    return redirect(url_for("solicitudes.mis_solicitudes"))


@bp.get("/solicitudes/<int:solicitud_id>/documento")
@usuario_requerido
def documento(solicitud_id):
    """Descarga la documentación adjunta. La ve su dueño y el administrador."""
    solicitud = _store().solicitudes.get(solicitud_id)
    cliente = cliente_actual()
    if (
        solicitud is None
        or not solicitud.get("adjunto")
        or (cliente is not None and solicitud["cliente_id"] != cliente["id"])
    ):
        abort(404)
    adjunto = solicitud["adjunto"]
    respuesta = send_file(
        BytesIO(adjunto["contenido"]), mimetype=adjunto["tipo"],
        as_attachment=True, download_name=adjunto["nombre"],
    )
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    return respuesta


# --- administrador ----------------------------------------------------------

@bp.get("/admin/solicitudes")
@admin_requerido
def panel():
    """Todas las solicitudes, con filtro por estado y prioridad (HU-19).

    Van primero las pendientes, y entre ellas las de prioridad más alta.
    """
    store = _store()
    estado = request.args.get("estado", "")
    prioridad = request.args.get("prioridad", "")
    if estado not in ETIQUETAS:
        estado = ""
    if prioridad not in PRIORIDADES:
        prioridad = ""

    todas = [_con_nombres(s, store) for s in store.solicitudes.values()]
    conteos = Counter(s["estado"] for s in todas)
    elegidas = [
        s for s in todas
        if (not estado or s["estado"] == estado) and (not prioridad or s["prioridad"] == prioridad)
    ]
    elegidas.sort(key=lambda s: (s["estado"] != PENDIENTE, PRIORIDADES.index(s["prioridad"]), s["id"]))
    return render_template(
        "panel_solicitudes.html",
        solicitudes=elegidas,
        total=len(todas),
        conteos=conteos,
        estado=estado,
        prioridad=prioridad,
    )


@bp.post("/admin/solicitudes/<int:solicitud_id>/prioridad")
@admin_requerido
def asignar_prioridad(solicitud_id):
    """HU-19: el administrador asigna la prioridad de una solicitud pendiente."""
    solicitud = _store().solicitudes.get(solicitud_id)
    if solicitud is None:
        abort(404)

    prioridad = request.form.get("prioridad")
    anterior = solicitud.get("prioridad", PRIORIDAD_POR_DEFECTO)
    if prioridad not in PRIORIDADES:
        flash("Elegí una prioridad válida.", "error")
    elif solicitud["estado"] != PENDIENTE:
        flash("Solo se puede cambiar la prioridad de solicitudes pendientes.", "error")
    elif prioridad == anterior:
        flash("La solicitud ya tenía esa prioridad.")
    else:
        solicitud["prioridad"] = prioridad
        solicitud["modificado"] = _ahora()
        registrar(
            "Prioridad asignada", "solicitud", ref=solicitud_id,
            detalle=f"Prioridad: {anterior} → {prioridad}",
        )
        flash(f"La solicitud #{solicitud_id} quedó con prioridad {prioridad}.")
    return _volver(url_for("solicitudes.panel"))


@bp.post("/admin/solicitudes/<int:solicitud_id>/documento/validar")
@admin_requerido
def validar_documentacion(solicitud_id):
    """HU-16: el administrador revisa la documentación recibida y la da por válida."""
    solicitud = _store().solicitudes.get(solicitud_id)
    if solicitud is None or not solicitud.get("adjunto"):
        abort(404)

    adjunto = solicitud["adjunto"]
    if solicitud["estado"] != PENDIENTE:
        flash("Solo se puede validar la documentación de solicitudes pendientes.", "error")
    elif adjunto["estado"] == DOC_VALIDADA:
        flash("La documentación ya estaba validada.")
    else:
        adjunto["estado"] = DOC_VALIDADA
        adjunto["validado"] = _ahora()
        _avisar(
            solicitud, "documentacion_validada",
            f"Validamos la documentación de tu solicitud #{solicitud_id}.",
        )
        registrar(
            "Documentación validada", "solicitud", ref=solicitud_id,
            detalle=f"Archivo: {adjunto['nombre']}",
        )
        flash(f"La documentación de la solicitud #{solicitud_id} quedó validada.")
    return _volver(url_for("solicitudes.panel"))


@bp.post("/admin/solicitudes/<int:solicitud_id>/realizar")
@admin_requerido
def realizar(solicitud_id):
    """El administrador aprueba una solicitud pendiente.

    Si es un alta o un cambio, el cliente pasa al plan pedido y se genera una
    factura pendiente (se cobra en «Facturación»). Si es una baja, el cliente
    queda sin plan. No se puede aprobar si la documentación adjunta todavía no
    fue validada, ni si el plan pedido no tiene costo definido.
    """
    store = _store()
    solicitud = store.solicitudes.get(solicitud_id)
    if solicitud is None:
        abort(404)

    if solicitud["estado"] != PENDIENTE:
        flash("Solo se pueden realizar solicitudes pendientes.", "error")
        return _volver(url_for("solicitudes.panel"))

    cliente = store.clientes.get(solicitud["cliente_id"])
    tipo = solicitud.get("tipo", "cambio")
    plan = store.planes.get(solicitud["plan_id"]) if solicitud["plan_id"] is not None else None
    if cliente is None or (tipo != "baja" and plan is None):
        abort(404)

    adjunto = solicitud.get("adjunto")
    if adjunto and adjunto["estado"] != DOC_VALIDADA:
        flash("No se puede aprobar: la documentación adjunta todavía no fue validada.", "error")
        return _volver(url_for("solicitudes.panel"))
    if tipo != "baja" and plan["costo_mensual"] is None:
        flash(
            f"No se puede aprobar: el plan «{plan['nombre']}» no tiene costo mensual definido. "
            "Completalo en Planes → Editar.",
            "error",
        )
        return _volver(url_for("solicitudes.panel"))

    ahora = _ahora()
    if tipo == "baja":
        cliente["plan_id"] = None
        aviso = f"Tu solicitud #{solicitud_id} fue realizada: tu plan fue dado de baja."
        detalle = "El cliente quedó sin plan"
        flash("La solicitud quedó como realizada: el cliente ya no tiene un plan contratado.")
    else:
        cliente["plan_id"] = plan["id"]
        factura_id = store.siguiente_id("facturas")
        store.facturas[factura_id] = {
            "id": factura_id,
            "solicitud_id": solicitud_id,
            "cliente_id": cliente["id"],
            "plan_id": plan["id"],
            "monto": plan["costo_mensual"],
            "estado": "pendiente",
            "intentos": 0,
            "creado": ahora,
        }
        solicitud["factura_id"] = factura_id
        aviso = f"Tu solicitud #{solicitud_id} fue realizada: ahora tenés el {plan['nombre']}."
        detalle = f"El cliente pasó al {plan['nombre']} · factura #{factura_id} pendiente"
        registrar("Factura generada", "factura", ref=factura_id, detalle=f"Por la solicitud #{solicitud_id}")
        flash(
            "La solicitud quedó como realizada y el plan del cliente se actualizó. "
            f"Se generó la factura #{factura_id}, pendiente de facturar en PagoNet."
        )

    solicitud["estado"] = REALIZADO
    solicitud["modificado"] = ahora
    solicitud["resuelto_por"] = admin_actual()["id"]
    _avisar(solicitud, REALIZADO, aviso)
    registrar("Solicitud aprobada", "solicitud", ref=solicitud_id, detalle=detalle)
    return _volver(url_for("solicitudes.panel"))


@bp.post("/admin/solicitudes/<int:solicitud_id>/rechazar")
@admin_requerido
def rechazar(solicitud_id):
    """El administrador rechaza una solicitud pendiente, sin facturar."""
    solicitud = _store().solicitudes.get(solicitud_id)
    if solicitud is None:
        abort(404)

    if solicitud["estado"] != PENDIENTE:
        flash("Solo se pueden rechazar solicitudes pendientes.", "error")
    else:
        solicitud["estado"] = RECHAZADA
        solicitud["motivo"] = "El administrador rechazó la solicitud."
        solicitud["modificado"] = _ahora()
        solicitud["resuelto_por"] = admin_actual()["id"]
        _avisar(
            solicitud, RECHAZADA,
            f"Tu solicitud #{solicitud_id} fue rechazada. {solicitud['motivo']}",
        )
        registrar("Solicitud rechazada", "solicitud", ref=solicitud_id, detalle=solicitud["motivo"])
        flash("La solicitud quedó como rechazada.")
    return _volver(url_for("solicitudes.panel"))
