"""Teste pentru demo.py. Nu se face niciun apel la Gemini sau Vapi."""
import unittest

from tests import ajutor  # noqa: F401  (trebuie importat primul)
import demo


def comanda(**campuri):
    baza = {
        "adresa": "Hauptstraße 5",
        "oras": "Hiltenfingen",
        "telefon": "0151 111111",
        "produse": [{"nume": "Pizza Margherita", "cantitate": 1, "marime": None}],
    }
    baza.update(campuri)
    return baza


class BonInGermana(unittest.TestCase):
    def test_textele_bonului_sunt_in_germana(self):
        bon = demo.fa_bon(comanda())
        self.assertIn("PIZZA SERVICE HILTENFINGEN", bon)
        self.assertIn("Adresse: Hauptstraße 5, Hiltenfingen", bon)
        self.assertIn("Telefon: 0151 111111", bon)
        self.assertIn("1 x Pizza Margherita - 8.00 EUR", bon)
        self.assertIn("GESAMT: 8.00 EUR", bon)
        self.assertNotIn("ACHTUNG", bon)

    def test_bonul_incepe_si_se_termina_cu_egal(self):
        # server.py recunoaște bonurile după "=" de la început.
        linii = demo.fa_bon(comanda()).splitlines()
        self.assertTrue(linii[0].startswith("="))
        self.assertTrue(linii[-1].startswith("="))
        self.assertNotIn("", linii)  # fără rânduri goale: bonurile se despart prin "\n\n"

    def test_cantitatea_inmulteste_pretul(self):
        bon = demo.fa_bon(comanda(produse=[{"nume": "Pizza Salami", "cantitate": 3}]))
        self.assertIn("3 x Pizza Salami - 30.00 EUR", bon)
        self.assertIn("GESAMT: 30.00 EUR", bon)

    def test_produs_necunoscut_e_marcat(self):
        bon = demo.fa_bon(comanda(produse=[{"nume": "Sushi", "cantitate": 1}]))
        self.assertIn("! 1 x Sushi (nicht im Menü)", bon)
        self.assertIn("! ACHTUNG: Artikel prüfen, Summe unvollständig", bon)


class OrasLipsa(unittest.TestCase):
    def test_oras_null(self):
        bon = demo.fa_bon(comanda(oras=None))
        self.assertIn("Adresse: Hauptstraße 5, Ort fehlt", bon)

    def test_oras_si_strada_lipsa(self):
        bon = demo.fa_bon(comanda(adresa=None, oras=None))
        self.assertIn("Adresse: Straße fehlt, Ort fehlt", bon)
        self.assertIn("! ACHTUNG: Adresse oder Telefon fehlt", bon)

    def test_oras_lipsa_singur_nu_da_avertisment_de_adresa(self):
        bon = demo.fa_bon(comanda(oras=None))
        self.assertNotIn("Adresse oder Telefon fehlt", bon)


class MarimeaPizzei(unittest.TestCase):
    def test_marime_mica_are_pret(self):
        for marime in ["klein", "Klein", "small", "mică", ""]:
            with self.subTest(marime=marime):
                bon = demo.fa_bon(comanda(produse=[
                    {"nume": "Pizza Margherita", "cantitate": 1, "marime": marime}
                ]))
                self.assertIn("GESAMT: 8.00 EUR", bon)
                self.assertNotIn("Preis prüfen", bon)

    def test_marimea_apare_pe_bon(self):
        bon = demo.fa_bon(comanda(produse=[
            {"nume": "Pizza Margherita", "cantitate": 1, "marime": "klein"}
        ]))
        self.assertIn("1 x Pizza Margherita (klein) - 8.00 EUR", bon)

    def test_marime_numerica_nu_strica_bonul(self):
        # Gemini poate trimite mărimea ca număr (ex. 32 cm).
        bon = demo.fa_bon(comanda(produse=[
            {"nume": "Pizza Margherita", "cantitate": 1, "marime": 32}
        ]))
        self.assertIn("1 x Pizza Margherita (32)", bon)
        self.assertIn("Preis prüfen", bon)


class AvertismentPreisPruefen(unittest.TestCase):
    def test_marime_mare_fara_pret(self):
        bon = demo.fa_bon(comanda(produse=[
            {"nume": "Pizza Margherita", "cantitate": 2, "marime": "groß"}
        ]))
        self.assertIn("2 x Pizza Margherita (groß)", bon)
        self.assertIn("! Preis prüfen: Größe nicht im Menü hinterlegt", bon)
        self.assertNotIn("16.00", bon)
        self.assertIn("GESAMT: 0.00 EUR", bon)
        self.assertIn("! ACHTUNG: Artikel prüfen, Summe unvollständig", bon)

    def test_doar_pizza_mare_iese_din_total(self):
        bon = demo.fa_bon(comanda(produse=[
            {"nume": "Pizza Margherita", "cantitate": 1, "marime": "Familie"},
            {"nume": "Pizza Salami", "cantitate": 1, "marime": None},
        ]))
        self.assertIn("GESAMT: 10.00 EUR", bon)
        self.assertEqual(bon.count("Preis prüfen"), 1)


class CantitateCaText(unittest.TestCase):
    def test_cantitate_text_cifra(self):
        # Gemini poate trimite "2" (text) în loc de 2 (număr).
        bon = demo.fa_bon(comanda(produse=[{"nume": "Pizza Salami", "cantitate": "2"}]))
        self.assertIn("2 x Pizza Salami - 20.00 EUR", bon)
        self.assertIn("GESAMT: 20.00 EUR", bon)

    def test_cantitate_neclara(self):
        bon = demo.fa_bon(comanda(produse=[{"nume": "Pizza Salami", "cantitate": "zwei"}]))
        self.assertIn("! zwei x Pizza Salami (Menge unklar)", bon)
        self.assertIn("GESAMT: 0.00 EUR", bon)
        self.assertIn("! ACHTUNG: Artikel prüfen, Summe unvollständig", bon)


class TelefonulDinApel(unittest.TestCase):
    def test_telefonul_din_apel_are_prioritate(self):
        bon = demo.fa_bon(comanda(telefon="0151 111111"), telefon_apel="+49 170 999999")
        self.assertIn("Telefon: +49 170 999999", bon)
        self.assertNotIn("0151 111111", bon)

    def test_fara_apel_se_foloseste_telefonul_spus(self):
        bon = demo.fa_bon(comanda(telefon="0151 111111"), telefon_apel=None)
        self.assertIn("Telefon: 0151 111111", bon)

    def test_telefon_din_apel_cand_clientul_nu_l_a_spus(self):
        bon = demo.fa_bon(comanda(telefon=None), telefon_apel="+49 170 999999")
        self.assertIn("Telefon: +49 170 999999", bon)
        self.assertNotIn("Adresse oder Telefon fehlt", bon)

    def test_niciun_telefon(self):
        bon = demo.fa_bon(comanda(telefon=None))
        self.assertIn("Telefon: fehlt", bon)
        self.assertIn("! ACHTUNG: Adresse oder Telefon fehlt", bon)


class GasesteProdus(unittest.TestCase):
    def test_nume_exact_fara_majuscule(self):
        self.assertEqual(demo.gaseste_produs("pizza margherita"), ("Pizza Margherita", None))

    def test_fara_cuvantul_pizza(self):
        self.assertEqual(demo.gaseste_produs("Salami"), ("Pizza Salami", None))

    def test_greseala_de_scriere(self):
        self.assertEqual(demo.gaseste_produs("Pizza Margarita"), ("Pizza Margherita", None))

    def test_nume_gol(self):
        self.assertEqual(demo.gaseste_produs(None), (None, "kein Name"))


class TranscriptDinApel(unittest.TestCase):
    def test_din_artifact(self):
        self.assertEqual(demo.transcript_din_apel({"artifact": {"transcript": "Hallo"}}), "Hallo")

    def test_din_mesaje(self):
        apel = {"messages": [
            {"role": "system", "message": "instrucțiuni"},
            {"role": "bot", "message": "Guten Tag"},
            {"role": "user", "message": "Eine Pizza"},
        ]}
        self.assertEqual(demo.transcript_din_apel(apel), "Robot: Guten Tag\nClient: Eine Pizza")

    def test_apel_gol(self):
        self.assertEqual(demo.transcript_din_apel({}), "")


if __name__ == "__main__":
    unittest.main()
