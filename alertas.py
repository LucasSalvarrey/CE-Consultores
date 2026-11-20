"""Alertas del administrador y avisos sin leer del cliente.

Se calculan en cada pantalla y se muestran en el encabezado: el administrador
ve en un vistazo qué necesita atención (fallas de PagoNet, reclamos escalados o
reiterados, solicitudes urgentes) y el cliente ve cuántos avisos no leyó.
"""
from flask import url_for

from auth import admin_actual, cliente_actual


def calcular_alertas(store):
    """Lista de alertas para el administrador: {nivel, texto, enlace, accion}."""
    alertas = []

    fallidas = [f for f in store.facturas.values() if f["estado"] == "fallida"]
    if fallidas:
        n = len(fallidas)
        alertas.append({
            "nivel": "error",
            "texto": f"{n} factura{'s' if n != 1 else ''} con falla en PagoNet: reintentá el cobro o realizá la devolución al cliente.",
            "enlace": url_for("facturacion.listado", estado="fallida"),
            "accion": "Gestionar",
        })

    escalados = [r for r in store.reclamos.values() if r["estado"] == "escalado"]
    if escalados:
        n = len(escalados)
        alertas.append({
            "nivel": "alerta",
            "texto": f"{n} reclamo{'s' if n != 1 else ''} escalado{'s' if n != 1 else ''} que necesita{'n' if n != 1 else ''} respuesta.",
            "enlace": url_for("reclamos.panel", estado="escalado"),
            "accion": "Ver reclamos",
        })

    reiterados = [r for r in store.reclamos.values() if r["estado"] == "pendiente" and r["reiteraciones"] > 0]
    if reiterados:
        n = len(reiterados)
        alertas.append({
            "nivel": "alerta",
            "texto": f"{n} reclamo{'s' if n != 1 else ''} reiterado{'s' if n != 1 else ''}: el cliente volvió a escribir sobre el mismo asunto.",
            "enlace": url_for("reclamos.panel", estado="pendiente"),
            "accion": "Ver reclamos",
        })

    urgentes = [
        s for s in store.solicitudes.values()
        if s["estado"] == "pendiente" and s.get("prioridad") == "alta"
    ]
    if urgentes:
        n = len(urgentes)
        alertas.append({
            "nivel": "info",
            "texto": f"{n} solicitud{'es' if n != 1 else ''} de prioridad alta pendiente{'s' if n != 1 else ''}.",
            "enlace": url_for("solicitudes.panel", estado="pendiente", prioridad="alta"),
            "accion": "Ver solicitudes",
        })
    return alertas


def registrar_alertas(app):
    """Deja disponibles `alertas_admin` y `avisos_sin_leer` en todos los templates."""

    @app.context_processor
    def inyectar_alertas():
        store = app.extensions["store"]
        datos = {"alertas_admin": [], "avisos_sin_leer": 0}
        if admin_actual() is not None:
            datos["alertas_admin"] = calcular_alertas(store)
        cliente = cliente_actual()
        if cliente is not None:
            datos["avisos_sin_leer"] = app.extensions["notisys"].sin_leer(cliente["id"])
        return datos
