"""Panel de inicio del administrador: un resumen de lo que necesita atención."""
from flask import Blueprint, current_app, render_template

from auth import admin_requerido

bp = Blueprint("inicio", __name__)


@bp.get("/admin")
@admin_requerido
def panel():
    store = current_app.extensions["store"]
    solicitudes = list(store.solicitudes.values())
    reclamos = list(store.reclamos.values())
    facturas = list(store.facturas.values())
    resumen = {
        "solicitudes_pendientes": sum(1 for s in solicitudes if s["estado"] == "pendiente"),
        "solicitudes_urgentes": sum(
            1 for s in solicitudes if s["estado"] == "pendiente" and s.get("prioridad") == "alta"
        ),
        "reclamos_abiertos": sum(1 for r in reclamos if r["estado"] in ("pendiente", "escalado")),
        "reclamos_escalados": sum(1 for r in reclamos if r["estado"] == "escalado"),
        "facturas_por_gestionar": sum(1 for f in facturas if f["estado"] in ("pendiente", "fallida")),
        "facturas_fallidas": sum(1 for f in facturas if f["estado"] == "fallida"),
        "clientes": len(store.clientes),
    }
    ultimos = list(reversed(store.registro))[:6]
    return render_template("inicio_admin.html", resumen=resumen, ultimos=ultimos)
