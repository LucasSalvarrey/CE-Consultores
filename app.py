import os
from datetime import datetime

from flask import Flask, redirect, render_template, url_for

from datos import cargar_datos
from notisys import NotiSysSimulado
from pagonet import PagoNetSimulado
from reloj import Reloj
from store import Store
from vericheck import VeriCheckSimulado


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-solo-para-desarrollo")
    app.config["ADMIN_EMAIL"] = os.environ.get("ADMIN_EMAIL", "benicio@ceconsultores.com")
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "admin-desarrollo-1")
    app.config["CARGAR_DATOS"] = os.environ.get("CARGAR_DATOS", "1") != "0"
    # Tope del cuerpo de un pedido (los documentos adjuntos se validan aparte, en 2 MB).
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    if test_config:
        app.config.update(test_config)

    app.extensions["store"] = Store(app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"])
    app.extensions["vericheck"] = VeriCheckSimulado()
    app.extensions["pagonet"] = PagoNetSimulado()
    app.extensions["notisys"] = NotiSysSimulado()
    app.extensions["reloj"] = Reloj()
    if app.config["CARGAR_DATOS"]:
        cargar_datos(app.extensions["store"])
        
    from alertas import registrar_alertas
    from auditoria import bp as auditoria_bp
    from auth import admin_actual, bp as auth_bp
    from clientes import bp as clientes_bp
    from facturacion import bp as facturacion_bp
    from inicio import bp as inicio_bp
    from planes import bp as planes_bp
    from reclamos import bp as reclamos_bp
    from reportes import bp as reportes_bp
    from solicitudes import bp as solicitudes_bp
    for blueprint in (
        auth_bp, clientes_bp, planes_bp, solicitudes_bp, facturacion_bp,
        reclamos_bp, reportes_bp, auditoria_bp, inicio_bp,
    ):
        app.register_blueprint(blueprint)
    registrar_alertas(app)

    @app.template_filter("fecha")
    def fecha(texto):
        """'2026-11-20T14:05:00' -> '20/11/2026 14:05'"""
        return datetime.fromisoformat(texto).strftime("%d/%m/%Y %H:%M") if texto else "—"

    @app.get("/")
    def inicio():
        if admin_actual() is not None:
            return redirect(url_for("inicio.panel"))
        return redirect(url_for("clientes.mi_cuenta"))

    # Pantallas de error con el mismo estilo que el resto de la aplicación.
    mensajes = {
        403: ("Acceso restringido", "Esta pantalla es solo para administradores."),
        404: ("No encontramos lo que buscabas", "La página no existe o no tenés acceso a ella."),
        405: ("Acción no permitida", "Esa acción no se puede hacer desde acá."),
        413: ("El archivo es demasiado grande", "El pedido supera el tamaño máximo permitido."),
    }

    def pagina_de_error(error):
        titulo, texto = mensajes[error.code]
        return render_template("error.html", codigo=error.code, titulo=titulo, texto=texto), error.code

    for codigo in mensajes:
        app.register_error_handler(codigo, pagina_de_error)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)