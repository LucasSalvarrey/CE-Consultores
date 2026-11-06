"""Pantallas de clientes: registro (HU-01.1 a HU-07.1) y perfil (HU-04.1)."""
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from auth import cliente_actual, login_requerido

from . import bp
from .validaciones import validar_perfil, validar_registro


def _store():
    return current_app.extensions["store"]


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    store = _store()
    planes = list(store.planes.values())

    if request.method == "GET":
        return render_template("registro.html", planes=planes, valores={}, errores={})

    datos, errores = validar_registro(request.form, store)
    if errores:
        # Se devuelven los valores cargados, salvo las contraseñas.
        return render_template(
            "registro.html", planes=planes, valores=request.form, errores=errores
        ), 400

    # HU-02.1: validación automática de identidad.
    vericheck = current_app.extensions["vericheck"]
    resultado = vericheck.validar(datos["dni"], datos["nombre"])
    if not resultado.valido:
        # HU-03.1: se informa el motivo y no se crea la cuenta.
        return render_template(
            "registro.html",
            planes=planes,
            valores=request.form,
            errores={},
            rechazo=resultado.motivo,
        ), 422

    cliente_id = store.siguiente_id("clientes")
    store.clientes[cliente_id] = {
        "id": cliente_id,
        "nombre": datos["nombre"],
        "dni": datos["dni"],
        "email": datos["email"],
        "telefono": datos["telefono"],
        "password_hash": generate_password_hash(datos["password"]),
        "plan_id": datos["plan_id"],
        "estado": "habilitada",
        "creado": datetime.now().isoformat(timespec="seconds"),
    }

    # HU-07.1: la identidad ya está validada, así que se le inicia la sesión y
    # va directo a Mi cuenta, donde ve el mensaje de bienvenida.
    session.clear()  # descarta cualquier sesión anterior
    session["cliente_id"] = cliente_id
    flash(
        f"¡Bienvenido/a, {datos['nombre']}! "
        "Tu identidad fue validada y tu cuenta ya está habilitada."
    )
    return redirect(url_for("clientes.mi_cuenta"))


@bp.get("/mi-cuenta")
@login_requerido
def mi_cuenta():
    """Datos del cliente con sesión iniciada. Base para HU-04.1 (modificar perfil)."""
    cliente = cliente_actual()
    plan = _store().planes[cliente["plan_id"]]
    return render_template("mi_cuenta.html", cliente=cliente, plan=plan)


@bp.route("/mi-cuenta/editar", methods=["GET", "POST"])
@login_requerido
def editar_perfil():
    """HU-04.1: el cliente modifica su email y su teléfono."""
    store = _store()
    cliente = cliente_actual()

    if request.method == "GET":
        return render_template(
            "editar_perfil.html", cliente=cliente, valores=cliente, errores={}
        )

    datos, errores = validar_perfil(request.form, store, cliente["id"])
    if errores:
        return render_template(
            "editar_perfil.html", cliente=cliente, valores=request.form, errores=errores
        ), 400

    if datos["email"] == cliente["email"] and datos["telefono"] == cliente["telefono"]:
        flash("No hiciste ningún cambio.")
    else:
        # `cliente` es el mismo diccionario que guarda el Store: se actualiza ahí.
        cliente.update(datos)
        cliente["modificado"] = datetime.now().isoformat(timespec="seconds")
        flash("Tus datos se actualizaron correctamente.")
    return redirect(url_for("clientes.mi_cuenta"))