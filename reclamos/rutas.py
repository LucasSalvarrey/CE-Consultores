"""Pantallas de reclamos: las del cliente (ingresar, ver, escribir, anular) y las
del administrador (responder, cambiar el estado, escalar y simular el tiempo)."""
from datetime import datetime

from flask import abort, current_app, flash, redirect, render_template, request, url_for

from auditoria import registrar
from auth import admin_actual, admin_requerido, cliente_actual, login_requerido

from . import bp
from .estados import ABIERTOS, ANULADO, CANALES, ESCALADO, ETIQUETAS, PENDIENTE, RESUELTO
from .sla import escalar, revisar, sla_horas_de, vencimiento
from .validaciones import normalizar_asunto, validar_mensaje, validar_reclamo

# Orden del panel del administrador: primero lo más urgente.
ORDEN = {ESCALADO: 0, PENDIENTE: 1, RESUELTO: 2, ANULADO: 3}


def _store():
    return current_app.extensions["store"]


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _mensaje(autor, nombre, texto):
    return {"autor": autor, "nombre": nombre, "texto": texto, "fecha": _ahora()}


def _avisar(reclamo, evento, mensaje):
    """Pide a NotiSys (simulado) que avise al cliente (HU-31)."""
    current_app.extensions["notisys"].enviar(
        reclamo["cliente_id"], evento, mensaje,
        enlace=url_for("reclamos.detalle", reclamo_id=reclamo["id"]),
    )


@bp.before_app_request
def vigilar_sla():
    """Antes de cada pedido se revisan los plazos, como si corriera un proceso aparte."""
    if request.endpoint != "static":
        revisar()


def _con_datos(reclamo, store):
    """El reclamo más los datos para mostrarlo: cliente y estado del SLA."""
    cliente = store.clientes.get(reclamo["cliente_id"])
    datos = {
        **reclamo,
        "cliente_nombre": cliente["nombre"] if cliente else "(cliente desconocido)",
        "sla_texto": None,
        "sla_vencido": False,
    }
    if reclamo["estado"] == PENDIENTE:
        restante = (
            datetime.fromisoformat(reclamo["vence"]) - current_app.extensions["reloj"].ahora()
        ).total_seconds() / 3600
        if restante <= 0:
            datos["sla_texto"], datos["sla_vencido"] = "SLA vencido", True
        else:
            datos["sla_texto"] = f"Vence en {max(1, round(restante))} h"
    return datos


def _reclamo_del_cliente(reclamo_id):
    """El reclamo, si es del cliente con sesión. Uno ajeno responde como inexistente."""
    reclamo = _store().reclamos.get(reclamo_id)
    if reclamo is None or reclamo["cliente_id"] != cliente_actual()["id"]:
        abort(404)
    return reclamo


# --- cliente ----------------------------------------------------------------

@bp.get("/reclamos")
@login_requerido
def mis_reclamos():
    """El cliente ve solo sus reclamos. Los nuevos primero."""
    store = _store()
    propios = [r for r in store.reclamos.values() if r["cliente_id"] == cliente_actual()["id"]]
    propios.sort(key=lambda r: r["id"], reverse=True)
    return render_template("mis_reclamos.html", reclamos=[_con_datos(r, store) for r in propios])


@bp.route("/reclamos/nuevo", methods=["GET", "POST"])
@login_requerido
def nuevo():
    """HU-24: el cliente ingresa un reclamo. Si ya tiene uno abierto sobre el mismo
    asunto, no se crea otro: se suma su mensaje al existente (HU-28)."""
    store = _store()
    cliente = cliente_actual()

    if request.method == "GET":
        return render_template("reclamo_form.html", canales=CANALES, valores={}, errores={})

    datos, errores = validar_reclamo(request.form)
    if errores:
        return render_template(
            "reclamo_form.html", canales=CANALES, valores=request.form, errores=errores
        ), 400

    clave = normalizar_asunto(datos["asunto"])
    duplicado = next(
        (
            r for r in sorted(store.reclamos.values(), key=lambda r: r["id"])
            if r["cliente_id"] == cliente["id"]
            and r["estado"] in ABIERTOS
            and normalizar_asunto(r["asunto"]) == clave
        ),
        None,
    )
    if duplicado is not None:
        duplicado["mensajes"].append(_mensaje("cliente", cliente["nombre"], datos["detalle"]))
        duplicado["reiteraciones"] += 1
        duplicado["modificado"] = _ahora()
        _avisar(
            duplicado, "reclamo_reiterado",
            f"Ya tenías abierto el reclamo #{duplicado['id']} sobre este asunto: sumamos tu mensaje a ese reclamo.",
        )
        registrar(
            "Reclamo reiterado", "reclamo", ref=duplicado["id"],
            detalle=f"El cliente volvió a escribir sobre «{duplicado['asunto']}» (reiteración {duplicado['reiteraciones']})",
        )
        flash(
            f"Ya tenés abierto el reclamo #{duplicado['id']} sobre este asunto. "
            "No creamos uno nuevo: sumamos tu mensaje a ese reclamo.",
            "alerta",
        )
        return redirect(url_for("reclamos.detalle", reclamo_id=duplicado["id"]))

    reloj = current_app.extensions["reloj"]
    sla_horas = sla_horas_de(store, cliente)
    reclamo_id = store.siguiente_id("reclamos")
    reclamo = {
        "id": reclamo_id,
        "cliente_id": cliente["id"],
        "asunto": datos["asunto"],
        "canal": datos["canal"],
        "estado": PENDIENTE,
        "mensajes": [_mensaje("cliente", cliente["nombre"], datos["detalle"])],
        "reiteraciones": 0,
        "sla_horas": sla_horas,
        "vence": vencimiento(reloj, sla_horas),
        "creado": _ahora(),
    }
    store.reclamos[reclamo_id] = reclamo
    _avisar(
        reclamo, "reclamo_recibido",
        f"Recibimos tu reclamo #{reclamo_id}. Te vamos a responder dentro de las {sla_horas} h.",
    )
    registrar(
        "Reclamo ingresado", "reclamo", ref=reclamo_id,
        detalle=f"«{datos['asunto']}» por {CANALES[datos['canal']]} · SLA de {sla_horas} h",
    )
    flash(f"Recibimos tu reclamo #{reclamo_id}. Te vamos a responder dentro de las {sla_horas} h.")
    return redirect(url_for("reclamos.detalle", reclamo_id=reclamo_id))


@bp.get("/reclamos/<int:reclamo_id>")
@login_requerido
def detalle(reclamo_id):
    """El cliente ve la conversación de su reclamo."""
    reclamo = _reclamo_del_cliente(reclamo_id)
    return render_template(
        "reclamo_detalle.html", reclamo=_con_datos(reclamo, _store()), es_admin=False, error=None
    )


@bp.post("/reclamos/<int:reclamo_id>/mensaje")
@login_requerido
def escribir(reclamo_id):
    """El cliente suma un mensaje a su reclamo, mientras siga abierto."""
    reclamo = _reclamo_del_cliente(reclamo_id)
    if reclamo["estado"] not in ABIERTOS:
        flash("Este reclamo ya está cerrado: no se pueden agregar mensajes.", "error")
        return redirect(url_for("reclamos.detalle", reclamo_id=reclamo_id))

    texto, error = validar_mensaje(request.form)
    if error:
        return render_template(
            "reclamo_detalle.html", reclamo=_con_datos(reclamo, _store()), es_admin=False, error=error
        ), 400

    reclamo["mensajes"].append(_mensaje("cliente", cliente_actual()["nombre"], texto))
    reclamo["modificado"] = _ahora()
    registrar("Mensaje del cliente", "reclamo", ref=reclamo_id, detalle="El cliente agregó un mensaje")
    flash("Tu mensaje se agregó al reclamo.")
    return redirect(url_for("reclamos.detalle", reclamo_id=reclamo_id))


@bp.post("/reclamos/<int:reclamo_id>/anular")
@login_requerido
def anular(reclamo_id):
    """El cliente anula un reclamo suyo, solo si sigue pendiente."""
    reclamo = _reclamo_del_cliente(reclamo_id)
    if reclamo["estado"] != PENDIENTE:
        flash("Solo se pueden anular reclamos pendientes.", "error")
    else:
        reclamo["estado"] = ANULADO
        reclamo["modificado"] = _ahora()
        registrar("Reclamo anulado", "reclamo", ref=reclamo_id, detalle="Lo anuló el cliente")
        flash("El reclamo se anuló.")
    return redirect(url_for("reclamos.detalle", reclamo_id=reclamo_id))


# --- administrador ----------------------------------------------------------

@bp.get("/admin/reclamos")
@admin_requerido
def panel():
    """Todos los reclamos, con filtro por estado. Primero los escalados."""
    store = _store()
    estado = request.args.get("estado", "")
    if estado not in ETIQUETAS:
        estado = ""

    todos = [_con_datos(r, store) for r in store.reclamos.values()]
    conteos = {e: sum(1 for r in todos if r["estado"] == e) for e in ETIQUETAS}
    elegidos = [r for r in todos if not estado or r["estado"] == estado]
    elegidos.sort(key=lambda r: (ORDEN[r["estado"]], r["id"]))
    return render_template(
        "panel_reclamos.html",
        reclamos=elegidos,
        total=len(todos),
        conteos=conteos,
        estado=estado,
        horas_simuladas=current_app.extensions["reloj"].horas_simuladas,
    )


def _reclamo(reclamo_id):
    reclamo = _store().reclamos.get(reclamo_id)
    if reclamo is None:
        abort(404)
    return reclamo


@bp.get("/admin/reclamos/<int:reclamo_id>")
@admin_requerido
def detalle_admin(reclamo_id):
    """El administrador ve la conversación y puede responder."""
    reclamo = _reclamo(reclamo_id)
    return render_template(
        "reclamo_detalle.html", reclamo=_con_datos(reclamo, _store()), es_admin=True, error=None
    )


@bp.post("/admin/reclamos/<int:reclamo_id>/responder")
@admin_requerido
def responder(reclamo_id):
    """HU-27: el administrador responde. Con «Responder y resolver» (HU-30) además
    cierra el reclamo. Al cliente le llega un aviso (HU-31)."""
    reclamo = _reclamo(reclamo_id)
    if reclamo["estado"] not in ABIERTOS:
        flash("Este reclamo ya está cerrado. Reabrilo si hace falta responder.", "error")
        return redirect(url_for("reclamos.detalle_admin", reclamo_id=reclamo_id))

    texto, error = validar_mensaje(request.form)
    if error:
        return render_template(
            "reclamo_detalle.html", reclamo=_con_datos(reclamo, _store()), es_admin=True, error=error
        ), 400

    admin = admin_actual()
    resolver = request.form.get("accion") == "resolver"
    reclamo["mensajes"].append(_mensaje("admin", admin["nombre"], texto))
    reclamo["modificado"] = _ahora()
    if resolver:
        reclamo["estado"] = RESUELTO
        _avisar(reclamo, "reclamo_resuelto", f"Tu reclamo #{reclamo_id} fue respondido y quedó resuelto.")
        registrar("Reclamo resuelto", "reclamo", ref=reclamo_id, detalle="Respuesta del administrador y cierre del reclamo")
        flash(f"Respondiste el reclamo #{reclamo_id} y quedó resuelto.")
    else:
        _avisar(reclamo, "reclamo_respondido", f"Respondimos tu reclamo #{reclamo_id}.")
        registrar("Reclamo respondido", "reclamo", ref=reclamo_id, detalle="Respuesta del administrador")
        flash(f"Tu respuesta al reclamo #{reclamo_id} se envió al cliente.")
    return redirect(url_for("reclamos.detalle_admin", reclamo_id=reclamo_id))


@bp.post("/admin/reclamos/<int:reclamo_id>/escalar")
@admin_requerido
def escalar_manual(reclamo_id):
    """HU-30: el administrador escala un reclamo pendiente."""
    reclamo = _reclamo(reclamo_id)
    if reclamo["estado"] != PENDIENTE:
        flash("Solo se pueden escalar reclamos pendientes.", "error")
    else:
        escalar(reclamo, "admin")
        flash(f"El reclamo #{reclamo_id} quedó escalado.")
    return redirect(url_for("reclamos.detalle_admin", reclamo_id=reclamo_id))


@bp.post("/admin/reclamos/<int:reclamo_id>/reabrir")
@admin_requerido
def reabrir(reclamo_id):
    """HU-30: el administrador reabre un reclamo resuelto. Vuelve a empezar su SLA."""
    reclamo = _reclamo(reclamo_id)
    if reclamo["estado"] != RESUELTO:
        flash("Solo se pueden reabrir reclamos resueltos.", "error")
    else:
        reclamo["estado"] = PENDIENTE
        reclamo["escalado_por"] = None
        reclamo["vence"] = vencimiento(current_app.extensions["reloj"], reclamo["sla_horas"])
        reclamo["modificado"] = _ahora()
        reclamo["mensajes"].append(_mensaje("sistema", "Sistema", "Reabierto por el administrador."))
        _avisar(reclamo, "reclamo_reabierto", f"Reabrimos tu reclamo #{reclamo_id}.")
        registrar("Reclamo reabierto", "reclamo", ref=reclamo_id, detalle="Volvió a pendiente")
        flash(f"El reclamo #{reclamo_id} se reabrió.")
    return redirect(url_for("reclamos.detalle_admin", reclamo_id=reclamo_id))


@bp.post("/admin/reclamos/simular-tiempo")
@admin_requerido
def simular_tiempo():
    """HU-29: avanza el reloj para ver cómo se escalan los reclamos que vencen."""
    texto = (request.form.get("horas") or "24").strip()
    if not (texto.isascii() and texto.isdigit() and 1 <= int(texto) <= 720):
        flash("Ingresá una cantidad de horas entre 1 y 720.", "error")
        return redirect(url_for("reclamos.panel"))

    horas = int(texto)
    current_app.extensions["reloj"].avanzar(horas)
    escalados = revisar()
    registrar(
        "Tiempo simulado", "sistema",
        detalle=f"Se avanzó el reloj {horas} h · {len(escalados)} reclamo(s) escalado(s) por SLA",
    )
    if escalados:
        numeros = ", ".join(f"#{r['id']}" for r in escalados)
        flash(f"Pasaron {horas} h. Se escalaron por SLA vencido los reclamos {numeros}.", "alerta")
    else:
        flash(f"Pasaron {horas} h. Ningún reclamo superó su SLA.")
    return redirect(url_for("reclamos.panel"))
