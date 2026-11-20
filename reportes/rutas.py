"""Pantallas de reportes (solo administrador)."""
import csv
from datetime import date
from io import StringIO

from flask import Response, current_app, flash, redirect, render_template, request, url_for

from auditoria import registrar
from auth import admin_requerido

from . import bp
from .armado import armar
from .validaciones import ESTADOS_POR_TIPO, TIPOS, validar_definicion


def _estados_para_formulario():
    """Los estados de cada tipo de reporte, para que el formulario los ofrezca."""
    return {tipo: dict(estados) for tipo, estados in ESTADOS_POR_TIPO.items()}


@bp.get("/admin/reportes")
@admin_requerido
def reportes():
    """HU-32 y HU-33: el administrador define el reporte y el sistema lo arma.

    Sin parámetros solo se muestra el formulario. Con parámetros se arma el
    reporte; si no hay datos para lo definido, se informa (HU-34).
    """
    contexto = {"tipos": TIPOS, "estados": _estados_para_formulario()}
    if "tipo" not in request.args:
        return render_template("reportes.html", valores={}, errores={}, reporte=None, **contexto)

    definicion, errores = validar_definicion(request.args)
    if errores:
        return render_template(
            "reportes.html", valores=request.args, errores=errores, reporte=None, **contexto
        ), 400

    reporte = armar(current_app.extensions["store"], definicion)
    registrar(
        "Reporte armado", "sistema",
        detalle=f"{reporte['titulo']} {reporte['periodo']} · {len(reporte['filas'])} fila(s)",
    )
    return render_template(
        "reportes.html", valores=request.args, errores={}, reporte=reporte, **contexto
    )


@bp.get("/admin/reportes/descargar")
@admin_requerido
def descargar():
    """Descarga el reporte en CSV (con ; y UTF-8, para que Excel lo abra bien)."""
    definicion, errores = validar_definicion(request.args)
    if errores:
        flash("Revisá la definición del reporte antes de descargarlo.", "error")
        return redirect(url_for("reportes.reportes"))

    reporte = armar(current_app.extensions["store"], definicion)
    if reporte["vacio"]:
        flash("No hay datos para descargar con lo que definiste.", "alerta")
        return redirect(url_for("reportes.reportes", **request.args))

    salida = StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow([f"{reporte['titulo']} {reporte['periodo']}"])
    escritor.writerow(reporte["columnas"])
    escritor.writerows(reporte["filas"])
    escritor.writerow([])
    for etiqueta, valor in reporte["resumen"]:
        escritor.writerow([etiqueta, valor])

    nombre = f"reporte-{definicion['tipo']}-{date.today().isoformat()}.csv"
    return Response(
        "\ufeff" + salida.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
