"""Atajos compartidos por los tests de solicitudes, facturación, reclamos, reportes y registro."""
import io
from datetime import datetime, timedelta
from decimal import Decimal

from ayudas import PlanesBase

# Contenidos mínimos que pasan la validación de cada tipo de archivo.
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


class GestionBase(PlanesBase):
    """Base con helpers para crear solicitudes, facturas y reclamos directo en el Store."""

    # --- sesiones y datos básicos -------------------------------------------

    def cambiar_a_admin(self):
        self.client.post("/logout")
        self.como_admin()

    def cambiar_a_cliente(self):
        self.client.post("/logout")
        self.login("lucas@ejemplo.com", "clave-segura-1")

    def poner_costo(self, plan_id, costo="9000.00", sla_horas=None):
        """Le define costo (y opcionalmente SLA) al plan: sin costo no se puede aprobar un pedido."""
        self.store.planes[plan_id]["costo_mensual"] = Decimal(costo)
        if sla_horas is not None:
            self.store.planes[plan_id]["sla_horas"] = sla_horas

    def agregar_cliente_ajeno(self):
        """Un segundo cliente, completo, para que el registro de Lucas no se rompa."""
        self.store.clientes[2] = {
            "id": 2, "nombre": "Galo Roselli", "dni": "28999111", "email": "galo@ejemplo.com",
            "telefono": "+54 11 4444-0000", "plan_id": 1,
        }

    @property
    def notisys(self):
        return self.app.extensions["notisys"]

    @property
    def reloj(self):
        return self.app.extensions["reloj"]

    def html(self, ruta):
        return self.client.get(ruta).get_data(as_text=True)

    # --- solicitudes ----------------------------------------------------------

    def crear_solicitud(self, documento=None, **cambios):
        datos = {"plan_id": "2", "detalle": "Quiero más atención prioritaria"}
        datos.update(cambios)
        if documento is not None:
            nombre, contenido = documento
            datos["documento"] = (io.BytesIO(contenido), nombre)
        return self.client.post("/solicitudes/nueva", data=datos, content_type="multipart/form-data")

    def insertar(self, cliente_id=1, estado="pendiente", plan_id=2, detalle="Detalle de prueba",
                 tipo="cambio", prioridad="media", adjunto=None):
        """Carga una solicitud directo en el Store, sin pasar por el formulario."""
        solicitud_id = self.store.siguiente_id("solicitudes")
        self.store.solicitudes[solicitud_id] = {
            "id": solicitud_id, "cliente_id": cliente_id, "plan_id": plan_id, "tipo": tipo,
            "detalle": detalle, "estado": estado, "prioridad": prioridad, "adjunto": adjunto,
            "creado": "2026-01-01T10:00:00",
        }
        return solicitud_id

    def adjunto(self, estado="recibida", nombre="constancia.pdf", contenido=PDF):
        return {"nombre": nombre, "tipo": "application/pdf", "tamano": len(contenido),
                "contenido": contenido, "estado": estado, "recibido": "2026-01-01T10:00:00"}

    # --- facturas -------------------------------------------------------------

    def insertar_factura(self, estado="pendiente", cliente_id=1, plan_id=2, monto="9000.00",
                         solicitud_id=1, intentos=0, creado="2026-01-01T10:00:00"):
        factura_id = self.store.siguiente_id("facturas")
        self.store.facturas[factura_id] = {
            "id": factura_id, "solicitud_id": solicitud_id, "cliente_id": cliente_id,
            "plan_id": plan_id, "monto": Decimal(monto) if monto is not None else None,
            "estado": estado, "intentos": intentos, "creado": creado,
        }
        return factura_id

    def facturar(self, factura_id, falla=False):
        datos = {"simular_falla": "1"} if falla else {}
        return self.client.post(f"/admin/facturas/{factura_id}/facturar", data=datos)

    def devolver(self, factura_id):
        return self.client.post(f"/admin/facturas/{factura_id}/devolver")

    # --- reclamos -------------------------------------------------------------

    def insertar_reclamo(self, cliente_id=1, asunto="Cobro duplicado", estado="pendiente",
                         sla_horas=48, horas_para_vencer=None, reiteraciones=0,
                         creado="2026-01-01T10:00:00", canal="web", escalado_por=None):
        """Carga un reclamo directo en el Store. `horas_para_vencer` puede ser negativo (ya vencido)."""
        reclamo_id = self.store.siguiente_id("reclamos")
        horas = sla_horas if horas_para_vencer is None else horas_para_vencer
        self.store.reclamos[reclamo_id] = {
            "id": reclamo_id, "cliente_id": cliente_id, "asunto": asunto, "canal": canal,
            "estado": estado, "reiteraciones": reiteraciones, "sla_horas": sla_horas,
            "mensajes": [{"autor": "cliente", "nombre": "Lucas Salvarrey",
                          "texto": f"Mensaje inicial de {asunto}", "fecha": creado}],
            "vence": (self.reloj.ahora() + timedelta(hours=horas)).isoformat(timespec="seconds"),
            "creado": creado, "escalado_por": escalado_por,
        }
        return reclamo_id

    def crear_reclamo(self, **cambios):
        datos = {"asunto": "Cobro duplicado", "canal": "web", "detalle": "Me cobraron dos veces."}
        datos.update(cambios)
        return self.client.post("/reclamos/nuevo", data=datos)

    def hoy(self):
        return datetime.now().isoformat(timespec="seconds")
