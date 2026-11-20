"""Simuladores de PagoNet (facturación), NotiSys (notificaciones) y el reloj."""
import unittest
from decimal import Decimal

from ayudas import PlanesBase  # noqa: F401  (deja el path del proyecto listo para los imports)
from notisys import NotiSysSimulado
from pagonet import PagoNetSimulado
from reloj import Reloj


class PagoNetSimuladoTest(unittest.TestCase):
    def setUp(self):
        self.pagonet = PagoNetSimulado()

    def facturar(self, monto, **kwargs):
        return self.pagonet.procesar_facturacion(
            {"cliente_id": 1, "plan_id": 2, "monto": monto}, **kwargs
        )

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

    def test_la_falla_simulada_rechaza_aunque_el_monto_sea_valido(self):
        r = self.facturar(Decimal("9000.00"), simular_falla=True)
        self.assertFalse(r.aprobado)
        self.assertIn("Falla de comunicación con PagoNet", r.motivo)

    def test_sin_falla_simulada_funciona_normal(self):
        self.assertTrue(self.facturar(Decimal("9000.00"), simular_falla=False).aprobado)


class NotiSysSimuladoTest(unittest.TestCase):
    def setUp(self):
        self.notisys = NotiSysSimulado()

    def test_arranca_sin_avisos(self):
        self.assertEqual(self.notisys.enviadas, [])

    def test_enviar_registra_el_aviso(self):
        aviso = self.notisys.enviar(1, "pendiente", "Hola", enlace="/solicitudes")
        self.assertEqual(self.notisys.enviadas, [aviso])
        self.assertEqual(
            (aviso["cliente_id"], aviso["evento"], aviso["mensaje"], aviso["enlace"]),
            (1, "pendiente", "Hola", "/solicitudes"),
        )
        self.assertIn("fecha", aviso)
        self.assertFalse(aviso["leido"])

    def test_el_enlace_es_opcional(self):
        self.assertIsNone(self.notisys.enviar(1, "pendiente", "Hola")["enlace"])

    def test_los_avisos_tienen_numero_propio(self):
        a = self.notisys.enviar(1, "x", "uno")
        b = self.notisys.enviar(1, "x", "dos")
        self.assertEqual((a["id"], b["id"]), (1, 2))

    def test_de_cliente_filtra_y_ordena_del_mas_nuevo_al_mas_viejo(self):
        self.notisys.enviar(1, "pendiente", "uno")
        self.notisys.enviar(2, "pendiente", "ajeno")
        self.notisys.enviar(1, "realizado", "dos")
        mensajes = [a["mensaje"] for a in self.notisys.de_cliente(1)]
        self.assertEqual(mensajes, ["dos", "uno"])

    def test_sin_leer_cuenta_solo_los_del_cliente(self):
        self.notisys.enviar(1, "x", "uno")
        self.notisys.enviar(1, "x", "dos")
        self.notisys.enviar(2, "x", "ajeno")
        self.assertEqual(self.notisys.sin_leer(1), 2)
        self.assertEqual(self.notisys.sin_leer(2), 1)
        self.assertEqual(self.notisys.sin_leer(3), 0)

    def test_marcar_leidos_solo_afecta_al_cliente(self):
        self.notisys.enviar(1, "x", "uno")
        self.notisys.enviar(2, "x", "ajeno")
        self.notisys.marcar_leidos(1)
        self.assertEqual(self.notisys.sin_leer(1), 0)
        self.assertEqual(self.notisys.sin_leer(2), 1)

    def test_cada_simulador_tiene_sus_propios_avisos(self):
        otro = NotiSysSimulado()
        self.notisys.enviar(1, "pendiente", "uno")
        self.assertEqual(otro.enviadas, [])


class RelojTest(unittest.TestCase):
    def test_arranca_sin_tiempo_simulado(self):
        self.assertEqual(Reloj().horas_simuladas, 0)

    def test_avanzar_suma_horas(self):
        reloj = Reloj()
        antes = reloj.ahora()
        reloj.avanzar(24)
        reloj.avanzar(6)
        self.assertEqual(reloj.horas_simuladas, 30)
        diferencia = (reloj.ahora() - antes).total_seconds() / 3600
        self.assertAlmostEqual(diferencia, 30, places=1)

    def test_cada_reloj_es_independiente(self):
        a, b = Reloj(), Reloj()
        a.avanzar(10)
        self.assertEqual(b.horas_simuladas, 0)


if __name__ == "__main__":
    unittest.main()
