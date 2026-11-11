"""Simuladores de PagoNet (facturación) y NotiSys (notificaciones)."""
import unittest
from decimal import Decimal

from ayudas import PlanesBase  # noqa: F401  (deja el path del proyecto listo para los imports)
from notisys import NotiSysSimulado
from pagonet import PagoNetSimulado


class PagoNetSimuladoTest(unittest.TestCase):
    def setUp(self):
        self.pagonet = PagoNetSimulado()

    def facturar(self, monto):
        return self.pagonet.procesar_facturacion({"cliente_id": 1, "plan_id": 2, "monto": monto})

    def test_acepta_un_monto_positivo(self):
        r = self.facturar(Decimal("9000.00"))
        self.assertTrue(r.aprobado)
        self.assertIsNone(r.motivo)

    def test_rechaza_si_no_hay_costo_definido(self):
        r = self.facturar(None)
        self.assertFalse(r.aprobado)
        self.assertIn("costo mensual", r.motivo)

    def test_rechaza_un_monto_en_cero_o_negativo(self):
        self.assertFalse(self.facturar(Decimal("0")).aprobado)
        self.assertFalse(self.facturar(Decimal("-5")).aprobado)


class NotiSysSimuladoTest(unittest.TestCase):
    def setUp(self):
        self.notisys = NotiSysSimulado()

    def test_arranca_sin_avisos(self):
        self.assertEqual(self.notisys.enviadas, [])

    def test_enviar_registra_el_aviso(self):
        aviso = self.notisys.enviar(1, 7, "pendiente", "Hola")
        self.assertEqual(self.notisys.enviadas, [aviso])
        self.assertEqual(
            (aviso["cliente_id"], aviso["solicitud_id"], aviso["evento"], aviso["mensaje"]),
            (1, 7, "pendiente", "Hola"),
        )
        self.assertIn("fecha", aviso)

    def test_de_cliente_filtra_y_ordena_del_mas_nuevo_al_mas_viejo(self):
        self.notisys.enviar(1, 1, "pendiente", "uno")
        self.notisys.enviar(2, 2, "pendiente", "ajeno")
        self.notisys.enviar(1, 1, "realizado", "dos")
        mensajes = [a["mensaje"] for a in self.notisys.de_cliente(1)]
        self.assertEqual(mensajes, ["dos", "uno"])

    def test_cada_simulador_tiene_sus_propios_avisos(self):
        otro = NotiSysSimulado()
        self.notisys.enviar(1, 1, "pendiente", "uno")
        self.assertEqual(otro.enviadas, [])


if __name__ == "__main__":
    unittest.main()
