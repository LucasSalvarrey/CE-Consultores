import os

from flask import Flask, redirect, url_for

from datos import cargar_datos
from store import Store
from vericheck import VeriCheckSimulado


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-solo-para-desarrollo")
    app.config["ADMIN_EMAIL"] = os.environ.get("ADMIN_EMAIL", "benicio@ceconsultores.com")
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "admin-desarrollo-1")
    app.config["CARGAR_DATOS"] = os.environ.get("CARGAR_DATOS", "1") != "0"
    if test_config:
        app.config.update(test_config)

    app.extensions["store"] = Store(app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"])
    app.extensions["vericheck"] = VeriCheckSimulado()
    if app.config["CARGAR_DATOS"]:
        cargar_datos(app.extensions["store"])
        
    from auth import bp as auth_bp
    from clientes import bp as clientes_bp
    from planes import bp as planes_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(planes_bp)

    @app.get("/")
    def inicio():
        return redirect(url_for("clientes.mi_cuenta"))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)