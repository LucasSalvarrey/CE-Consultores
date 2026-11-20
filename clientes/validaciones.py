"""Reglas de los formularios de registro y de edición de perfil."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TELEFONO_RE = re.compile(r"^\+?[\d\s\-()]{6,20}$")


def _limpiar_dni(valor):
    """Saca puntos, guiones y espacios: '30.123.456' -> '30123456'."""
    return re.sub(r"[.\-\s]", "", valor or "")


def _validar_email(valor, store, excluir_id=None):
    """Devuelve (email_limpio, mensaje_de_error). El error es None si está bien.

    `excluir_id` es el cliente que está editando su propio perfil: su email
    actual no cuenta como repetido.
    """
    email = (valor or "").strip().lower()
    if not EMAIL_RE.match(email):
        return email, "Ingresá un email válido."
    en_uso_por_cliente = any(
        c["email"] == email and c["id"] != excluir_id for c in store.clientes.values()
    )
    en_uso_por_admin = any(a["email"] == email for a in store.administradores.values())
    if en_uso_por_cliente or en_uso_por_admin:
        return email, "Ya existe un cliente registrado con ese email."
    return email, None


def _validar_telefono(valor):
    """Devuelve (telefono_limpio, mensaje_de_error)."""
    telefono = (valor or "").strip()
    if not TELEFONO_RE.match(telefono):
        return telefono, "Ingresá un teléfono válido."
    return telefono, None


def validar_registro(form, store):
    """Valida el formulario de registro.

    Devuelve (datos, errores). Si errores está vacío, datos tiene los valores
    ya limpios y listos para guardar.
    """
    errores = {}

    nombre = (form.get("nombre") or "").strip()
    if not nombre:
        errores["nombre"] = "Ingresá tu nombre completo."

    dni = _limpiar_dni(form.get("dni"))
    if not dni.isdigit() or len(dni) not in (7, 8):
        errores["dni"] = "Ingresá un DNI válido (7 u 8 dígitos)."
    elif any(c["dni"] == dni for c in store.clientes.values()):
        errores["dni"] = "Ya existe un cliente registrado con ese DNI."

    email, error = _validar_email(form.get("email"), store)
    if error:
        errores["email"] = error

    telefono, error = _validar_telefono(form.get("telefono"))
    if error:
        errores["telefono"] = error

    password = form.get("password") or ""
    if len(password) < 8:
        errores["password"] = "La contraseña debe tener al menos 8 caracteres."
    elif password != (form.get("password2") or ""):
        errores["password2"] = "Las contraseñas no coinciden."

    plan_id = None
    try:
        plan_id = int(form.get("plan_id") or "")
    except ValueError:
        pass
    if plan_id not in store.planes:
        errores["plan_id"] = "Elegí un plan de la lista."

    datos = {
        "nombre": nombre,
        "dni": dni,
        "email": email,
        "telefono": telefono,
        "password": password,
        "plan_id": plan_id,
    }
    return datos, errores


def validar_perfil(form, store, cliente_id):
    """Valida el formulario de edición. Devuelve (datos, errores)."""
    errores = {}

    email, error = _validar_email(form.get("email"), store, excluir_id=cliente_id)
    if error:
        errores["email"] = error

    telefono, error = _validar_telefono(form.get("telefono"))
    if error:
        errores["telefono"] = error

    return {"email": email, "telefono": telefono}, errores