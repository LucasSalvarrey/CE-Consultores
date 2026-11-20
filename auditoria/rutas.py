"""Pantalla del registro de cambios (solo administrador)."""
from flask import current_app, render_template, request

from auth import admin_requerido

from . import ENTIDADES, bp

MAXIMO = 300


@bp.get("/admin/registro")
@admin_requerido
def registro_de_cambios():
    """Lista los cambios, el más reciente primero, con filtro por entidad y búsqueda."""
    store = current_app.extensions["store"]
    entidad = request.args.get("entidad", "")
    if entidad not in ENTIDADES:
        entidad = ""
    texto = (request.args.get("q") or "").strip()

    entradas = list(reversed(store.registro))
    if entidad:
        entradas = [e for e in entradas if e["entidad"] == entidad]
    if texto:
        buscado = texto.lower()
        entradas = [
            e for e in entradas
            if buscado in f"{e['actor']} {e['accion']} {e['detalle']}".lower()
        ]
    total = len(entradas)
    return render_template(
        "registro_cambios.html",
        entradas=entradas[:MAXIMO],
        total=total,
        maximo=MAXIMO,
        entidades=ENTIDADES,
        entidad=entidad,
        q=texto,
    )
