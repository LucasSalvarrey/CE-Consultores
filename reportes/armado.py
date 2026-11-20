"""Arma un reporte a partir de lo que el administrador definió (HU-33 y HU-34).

No sabe nada de Flask: recibe el Store y la definición ya validada, y devuelve un
diccionario con el título, las columnas, las filas y el resumen.
"""
from datetime import datetime

from facturacion.estados import ETIQUETAS as ESTADOS_FACTURA
from planes.formatos import pesos
from reclamos.estados import CANALES, ETIQUETAS as ESTADOS_RECLAMO
from solicitudes.estados import (
    ETIQUETAS as ESTADOS_SOLICITUD, PRIORIDAD_ETIQUETAS, PRIORIDAD_POR_DEFECTO, TIPOS as TIPOS_SOLICITUD,
)

from .validaciones import ESTADOS_POR_TIPO, TIPOS


def _fecha(texto):
    return datetime.fromisoformat(texto).date()


def _dinero(valor):
    return f"$ {pesos(valor)}"


def _dia(texto):
    return _fecha(texto).strftime("%d/%m/%Y")


def _filtrar(registros, definicion):
    """Aplica el período y el estado que se definieron."""
    elegidos = []
    for r in registros:
        dia = _fecha(r["creado"])
        if definicion["desde"] and dia < definicion["desde"]:
            continue
        if definicion["hasta"] and dia > definicion["hasta"]:
            continue
        if definicion["estado"] and r["estado"] != definicion["estado"]:
            continue
        elegidos.append(r)
    return sorted(elegidos, key=lambda r: r["id"])


def _periodo(definicion):
    desde, hasta = definicion["desde"], definicion["hasta"]
    if desde and hasta:
        return f"del {desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}"
    if desde:
        return f"desde el {desde.strftime('%d/%m/%Y')}"
    if hasta:
        return f"hasta el {hasta.strftime('%d/%m/%Y')}"
    return "de todo el período"


def _por_estado(registros, etiquetas):
    return [
        (etiquetas[estado], sum(1 for r in registros if r["estado"] == estado))
        for estado in etiquetas
    ]


def _nombre_cliente(store, cliente_id):
    cliente = store.clientes.get(cliente_id)
    return cliente["nombre"] if cliente else "(cliente desconocido)"


def _nombre_plan(store, plan_id, por_defecto="—"):
    plan = store.planes.get(plan_id) if plan_id is not None else None
    return plan["nombre"] if plan else por_defecto


def _solicitudes(store, registros):
    columnas = ["N.º", "Cliente", "Tipo", "Plan pedido", "Prioridad", "Estado", "Fecha"]
    filas = [
        [
            f"#{s['id']}", _nombre_cliente(store, s["cliente_id"]),
            TIPOS_SOLICITUD.get(s.get("tipo", "cambio"), "Cambio de plan"),
            _nombre_plan(store, s["plan_id"], "Sin plan"),
            PRIORIDAD_ETIQUETAS.get(s.get("prioridad", PRIORIDAD_POR_DEFECTO), "Media"),
            ESTADOS_SOLICITUD[s["estado"]], _dia(s["creado"]),
        ]
        for s in registros
    ]
    resumen = [("Total de solicitudes", len(registros))]
    resumen += _por_estado(registros, ESTADOS_SOLICITUD)
    resumen += [
        (f"Prioridad {etiqueta.lower()}", sum(1 for s in registros if s.get("prioridad", PRIORIDAD_POR_DEFECTO) == clave))
        for clave, etiqueta in PRIORIDAD_ETIQUETAS.items()
    ]
    return columnas, filas, resumen


def _reclamos(store, registros):
    columnas = ["N.º", "Cliente", "Asunto", "Canal", "Estado", "Reiteraciones", "Fecha"]
    filas = [
        [
            f"#{r['id']}", _nombre_cliente(store, r["cliente_id"]), r["asunto"],
            CANALES.get(r["canal"], r["canal"]), ESTADOS_RECLAMO[r["estado"]],
            str(r["reiteraciones"]), _dia(r["creado"]),
        ]
        for r in registros
    ]
    resumen = [("Total de reclamos", len(registros))]
    resumen += _por_estado(registros, ESTADOS_RECLAMO)
    resumen += [
        ("Escalados por SLA", sum(1 for r in registros if r.get("escalado_por") == "sla")),
        ("Reiterados", sum(1 for r in registros if r["reiteraciones"] > 0)),
    ]
    return columnas, filas, resumen


def _facturacion(store, registros):
    columnas = ["N.º", "Solicitud", "Cliente", "Plan", "Monto", "Estado", "Intentos", "Fecha"]
    filas = [
        [
            f"#{f['id']}", f"#{f['solicitud_id']}", _nombre_cliente(store, f["cliente_id"]),
            _nombre_plan(store, f["plan_id"]), _dinero(f["monto"]), ESTADOS_FACTURA[f["estado"]],
            str(f.get("intentos", 0)), _dia(f["creado"]),
        ]
        for f in registros
    ]
    cobrado = sum((f["monto"] for f in registros if f["estado"] == "pagada"), 0)
    devuelto = sum((f["monto"] for f in registros if f["estado"] == "devuelta"), 0)
    resumen = [("Total de facturas", len(registros))]
    resumen += _por_estado(registros, ESTADOS_FACTURA)
    resumen += [("Total cobrado", _dinero(cobrado)), ("Total devuelto", _dinero(devuelto))]
    return columnas, filas, resumen


ARMADORES = {
    "solicitudes": (lambda s: s.solicitudes, _solicitudes),
    "reclamos": (lambda s: s.reclamos, _reclamos),
    "facturacion": (lambda s: s.facturas, _facturacion),
}


def armar(store, definicion):
    """Devuelve el reporte: {titulo, periodo, columnas, filas, resumen, vacio}."""
    tipo = definicion["tipo"]
    origen, construir = ARMADORES[tipo]
    registros = _filtrar(origen(store).values(), definicion)
    columnas, filas, resumen = construir(store, registros)

    titulo = f"Reporte de {TIPOS[tipo].lower()}"
    if definicion["estado"]:
        titulo += f" · {ESTADOS_POR_TIPO[tipo][definicion['estado']].lower()}s"
    return {
        "titulo": titulo,
        "periodo": _periodo(definicion),
        "columnas": columnas,
        "filas": filas,
        "resumen": resumen,
        "vacio": not filas,
    }
