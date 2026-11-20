"""SLA de los reclamos y escalado automático (HU-29)."""
from datetime import datetime, timedelta

from flask import current_app, url_for

from auditoria import registrar

from .estados import ESCALADO, PENDIENTE

SLA_POR_DEFECTO_HORAS = 48


def sla_horas_de(store, cliente):
    """Las horas de SLA del cliente: las de su plan, o 48 h si no tiene."""
    plan = store.planes.get(cliente["plan_id"]) if cliente and cliente.get("plan_id") is not None else None
    if plan and plan.get("sla_horas"):
        return plan["sla_horas"]
    return SLA_POR_DEFECTO_HORAS


def vencimiento(reloj, horas):
    """Cuándo vence un SLA de `horas` que empieza ahora, según el reloj de la app."""
    return (reloj.ahora() + timedelta(hours=horas)).isoformat(timespec="seconds")


def escalar(reclamo, por):
    """Pasa el reclamo a «escalado» y avisa al cliente. `por` es 'sla' o 'admin'."""
    ahora = datetime.now().isoformat(timespec="seconds")
    if por == "sla":
        texto = f"Escalado automáticamente: se superó el SLA de {reclamo['sla_horas']} h sin respuesta."
        aviso = (
            f"Tu reclamo #{reclamo['id']} fue escalado porque se superó el tiempo de "
            f"respuesta (SLA de {reclamo['sla_horas']} h)."
        )
    else:
        texto = "Escalado por el administrador."
        aviso = f"Tu reclamo #{reclamo['id']} fue escalado para que lo revise un responsable."

    reclamo["estado"] = ESCALADO
    reclamo["escalado_por"] = por
    reclamo["modificado"] = ahora
    reclamo["mensajes"].append({"autor": "sistema", "nombre": "Sistema", "texto": texto, "fecha": ahora})
    current_app.extensions["notisys"].enviar(
        reclamo["cliente_id"], "reclamo_escalado", aviso,
        enlace=url_for("reclamos.detalle", reclamo_id=reclamo["id"]),
    )
    registrar(
        "Reclamo escalado", "reclamo", ref=reclamo["id"], detalle=texto,
        actor="Sistema" if por == "sla" else None,
    )


def revisar():
    """Escala los reclamos pendientes cuyo SLA ya venció. Devuelve los que escaló.

    Se ejecuta antes de cada pedido (ver `reclamos/rutas.py`), como si fuera un
    proceso que vigila los plazos.
    """
    app = current_app
    ahora = app.extensions["reloj"].ahora()
    escalados = []
    for reclamo in list(app.extensions["store"].reclamos.values()):
        if reclamo["estado"] == PENDIENTE and datetime.fromisoformat(reclamo["vence"]) <= ahora:
            escalar(reclamo, "sla")
            escalados.append(reclamo)
    return escalados
