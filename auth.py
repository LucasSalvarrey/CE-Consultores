from functools import wraps

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint("auth", __name__)

HASH_FALSO = generate_password_hash("contraseña-que-nadie-tiene")


def _store():
    return current_app.extensions["store"]


def cliente_actual():
    cliente_id = session.get("cliente_id")
    if cliente_id is None:
        return None
    return _store().clientes.get(cliente_id)


def admin_actual():
    admin_id = session.get("admin_id")
    if admin_id is None:
        return None
    return _store().administradores.get(admin_id)


def login_requerido(vista):
    """Solo clientes."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if cliente_actual() is None:
            return redirect(url_for("auth.login", next=request.path))
        return vista(*args, **kwargs)
    return envoltura


def usuario_requerido(vista):
    """Cualquier persona con sesión, sea cliente o administrador."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if cliente_actual() is None and admin_actual() is None:
            return redirect(url_for("auth.login", next=request.path))
        return vista(*args, **kwargs)
    return envoltura


def admin_requerido(vista):
    """Solo administradores. Un cliente con sesión recibe 403 (prohibido)."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if admin_actual() is None:
            if cliente_actual() is not None:
                abort(403)
            return redirect(url_for("auth.login", next=request.path))
        return vista(*args, **kwargs)
    return envoltura


def destino_seguro(destino, por_defecto):
    if destino and destino.startswith("/") and not destino.startswith("//") and "\\" not in destino:
        return destino
    return por_defecto


_destino_seguro = destino_seguro


def _buscar_usuario(email):
    store = _store()
    for admin in store.administradores.values():
        if admin["email"] == email:
            return "administrador", admin
    for cliente in store.clientes.values():
        if cliente["email"] == email:
            return "cliente", cliente
    return None, None


@bp.app_context_processor
def inyectar_usuario():
    return {"cliente_actual": cliente_actual(), "admin_actual": admin_actual()}


@bp.route("/login", methods=["GET", "POST"])
def login():
    if cliente_actual() is not None:
        return redirect(url_for("clientes.mi_cuenta"))
    if admin_actual() is not None:
        return redirect(url_for("inicio.panel"))
    siguiente = request.values.get("next", "")

    if request.method == "GET":
        return render_template("login.html", siguiente=siguiente, email="", error=None)

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    rol, usuario = _buscar_usuario(email)
    hash_guardado = usuario["password_hash"] if usuario else HASH_FALSO

    if check_password_hash(hash_guardado, password) and usuario is not None:
        session.clear()
        if rol == "administrador":
            session["admin_id"] = usuario["id"]
            inicio = url_for("inicio.panel")
        else:
            session["cliente_id"] = usuario["id"]
            inicio = url_for("clientes.mi_cuenta")
        return redirect(_destino_seguro(siguiente, inicio))

    return render_template(
        "login.html", siguiente=siguiente, email=email,
        error="Email o contraseña incorrectos.",
    ), 401


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))