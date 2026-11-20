"""Pantallas de facturación (solo administrador)."""
from datetime import datetime

from flask import abort, current_app, flash, redirect, render_template, request, url_for

from auditoria import registrar
from auth import admin_actual, admin_requerido, destino_seguro
from planes.formatos import pesos

from . import bp
from .estados import DEVUELTA, ETIQUETAS, FALLIDA, PAGADA, PENDIENTE

# Orden del listado: primero lo que necesita atención.
ORDEN = {FALLIDA: 0, PENDIENTE: 1, PAGADA: 2, DEVUELTA: 3}


def _store():
    return current_app.extensions["store"]


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _avisar(factura, evento, mensaje):
    current_app.extensions["notisys"].enviar(
        factura["cliente_id"], evento, mensaje, enlace=url_for("solicitudes.mis_solicitudes")
    )


def _volver():
    return redirect(destino_seguro(request.form.get("volver"), url_for("facturacion.listado")))


@bp.get("/admin/facturas")
@admin_requerido
def listado():
    """Todas las facturas, con filtro por estado. Primero las que necesitan atención."""
    store = _store()
    estado = request.args.get("estado", "")
    if estado not in ETIQUETAS:
        estado = ""

    filas = []
    for f in store.facturas.values():
        cliente = store.clientes.get(f["cliente_id"])
        plan = store.planes.get(f["plan_id"])
        filas.append({
            **f,
            "cliente_nombre": cliente["nombre"] if cliente else "(cliente desconocido)",
            "plan_nombre": plan["nombre"] if plan else "(plan desconocido)",
            "devolucion": store.devoluciones.get(f.get("devolucion_id")),
        })
    conteos = {e: sum(1 for f in filas if f["estado"] == e) for e in ETIQUETAS}
    elegidas = [f for f in filas if not estado or f["estado"] == estado]
    elegidas.sort(key=lambda f: (ORDEN[f["estado"]], -f["id"]))
    return render_template(
        "facturas.html", facturas=elegidas, total=len(filas), conteos=conteos, estado=estado,
    )


@bp.post("/admin/facturas/<int:factura_id>/facturar")
@admin_requerido
def facturar(factura_id):
    """HU-21: cobra la factura en PagoNet. También sirve para reintentar una fallida.

    Con la casilla «Simular falla» PagoNet responde con un error, para poder
    probar la gestión de fallas (HU-22).
    """
    factura = _store().facturas.get(factura_id)
    if factura is None:
        abort(404)

    if factura["estado"] not in (PENDIENTE, FALLIDA):
        flash("Solo se pueden facturar facturas pendientes o con falla.", "error")
        return _volver()

    simular_falla = request.form.get("simular_falla") == "1"
    datos_factura = {
        "cliente_id": factura["cliente_id"],
        "plan_id": factura["plan_id"],
        "monto": factura["monto"],
    }
    resultado = current_app.extensions["pagonet"].procesar_facturacion(
        datos_factura, simular_falla=simular_falla
    )
    reintento = factura["estado"] == FALLIDA
    factura["intentos"] = factura.get("intentos", 0) + 1
    factura["modificado"] = _ahora()

    if resultado.aprobado:
        factura["estado"] = PAGADA
        factura["motivo_falla"] = None
        _avisar(
            factura, "factura_pagada",
            f"Registramos el pago de tu factura #{factura_id} por $ {pesos(factura['monto'])}.",
        )
        registrar(
            "Factura cobrada", "factura", ref=factura_id,
            detalle=f"{'Reintento exitoso' if reintento else 'Cobro exitoso'} en PagoNet · $ {pesos(factura['monto'])}",
        )
        flash(f"La factura #{factura_id} se cobró correctamente en PagoNet.")
    else:
        factura["estado"] = FALLIDA
        factura["motivo_falla"] = resultado.motivo
        registrar(
            "Falla en PagoNet", "factura", ref=factura_id,
            detalle=f"Intento {factura['intentos']}: {resultado.motivo}",
        )
        flash(
            f"PagoNet informó una falla en la factura #{factura_id}. Reintentá el cobro "
            "o realizá la devolución al cliente.",
            "error",
        )
    return _volver()


@bp.post("/admin/facturas/<int:factura_id>/devolver")
@admin_requerido
def devolver(factura_id):
    """HU-22: ante una falla de PagoNet, el administrador devuelve el dinero al cliente."""
    store = _store()
    factura = store.facturas.get(factura_id)
    if factura is None:
        abort(404)

    if factura["estado"] != FALLIDA:
        flash("Solo se puede devolver el dinero de una factura con falla en PagoNet.", "error")
        return _volver()

    devolucion_id = store.siguiente_id("devoluciones")
    store.devoluciones[devolucion_id] = {
        "id": devolucion_id,
        "factura_id": factura_id,
        "cliente_id": factura["cliente_id"],
        "monto": factura["monto"],
        "fecha": _ahora(),
        "admin_id": admin_actual()["id"],
    }
    factura["estado"] = DEVUELTA
    factura["devolucion_id"] = devolucion_id
    factura["modificado"] = _ahora()

    _avisar(
        factura, "factura_devuelta",
        f"Realizamos la devolución de $ {pesos(factura['monto'])} por la factura #{factura_id}.",
    )
    registrar(
        "Devolución realizada", "factura", ref=factura_id,
        detalle=f"Devolución #{devolucion_id} al cliente por $ {pesos(factura['monto'])}",
    )
    flash(f"Se realizó la devolución de $ {pesos(factura['monto'])} al cliente por la factura #{factura_id}.")
    return _volver()
