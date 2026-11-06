from datetime import datetime

from werkzeug.security import generate_password_hash

CLIENTE_DEMO = {
    "nombre": "Lucas Salvarrey",
    "dni": "45786322",
    "email": "lucas@ejemplo.com",
    "telefono": "+54 11 5555-1234",
    "plan_id": 1,
}
PASSWORD_DEMO = "clave-segura-2"


def cargar_datos(store):
    """Agrega el cliente de ejemplo al Store, ya habilitado."""
    cliente_id = store.siguiente_id("clientes")
    store.clientes[cliente_id] = {
        "id": cliente_id,
        **CLIENTE_DEMO,
        "password_hash": generate_password_hash(PASSWORD_DEMO),
        "estado": "habilitada",
        "creado": datetime.now().isoformat(timespec="seconds"),
    }