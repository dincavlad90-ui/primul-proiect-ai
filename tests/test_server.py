"""Teste pentru server.py. Gemini e înlocuit cu date false; bonuri.txt nu e atins."""
import unittest
from unittest import mock

from tests import ajutor  # noqa: F401  (trebuie importat primul)
import server

RAPORT = {"message": {"type": "end-of-call-report", "artifact": {"transcript": "Client: Eine Pizza"}}}


class ParolaVapi(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        # Nu pornim procesarea reală (ar chema Gemini și ar scrie în bonuri.txt).
        self.thread = mock.patch.object(server.threading, "Thread").start()
        self.addCleanup(mock.patch.stopall)

    def test_fara_parola_e_refuzat(self):
        r = self.client.post("/vapi", json=RAPORT)
        self.assertEqual(r.status_code, 401)
        self.thread.assert_not_called()

    def test_parola_gresita_e_refuzata(self):
        r = self.client.post("/vapi", json=RAPORT, headers={"X-Vapi-Secret": "gresit"})
        self.assertEqual(r.status_code, 401)
        self.thread.assert_not_called()

    def test_bearer_gresit_e_refuzat(self):
        r = self.client.post("/vapi", json=RAPORT, headers={"Authorization": "Bearer gresit"})
        self.assertEqual(r.status_code, 401)

    def test_parola_corecta_merge(self):
        r = self.client.post("/vapi", json=RAPORT, headers={"X-Vapi-Secret": ajutor.PAROLA_TEST})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"ok": True})
        self.thread.assert_called_once()
        self.assertEqual(self.thread.call_args.kwargs["args"], (RAPORT["message"],))

    def test_parola_corecta_ca_bearer_merge(self):
        r = self.client.post("/vapi", json=RAPORT,
                             headers={"Authorization": "Bearer " + ajutor.PAROLA_TEST})
        self.assertEqual(r.status_code, 200)

    def test_alt_tip_de_mesaj_nu_face_bon(self):
        r = self.client.post("/vapi", json={"message": {"type": "status-update"}},
                             headers={"X-Vapi-Secret": ajutor.PAROLA_TEST})
        self.assertEqual(r.status_code, 200)
        self.thread.assert_not_called()

    def test_fara_parola_in_env_refuza_fara_sa_crape(self):
        # Dacă serverul e pornit altfel decât cu "python server.py" și lipsește parola din .env.
        with mock.patch.object(server, "SECRET", None):
            r = self.client.post("/vapi", json=RAPORT, headers={"X-Vapi-Secret": "orice"})
        self.assertEqual(r.status_code, 401)


class EcranBonuri(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_cheie_gresita_da_404(self):
        self.assertEqual(self.client.get("/bonuri?cheie=gresit").status_code, 404)
        self.assertEqual(self.client.get("/bonuri.json?cheie=gresit").status_code, 404)
        self.assertEqual(self.client.get("/bonuri.json").status_code, 404)

    def test_cheie_corecta_arata_ecranul(self):
        r = self.client.get("/bonuri?cheie=" + ajutor.CHEIE_TEST)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Bestellungen", r.data)
        r.close()

    def test_cheie_corecta_da_bonurile_noi_primele(self):
        fals = "=== bon 1\nGESAMT\n===\n\n=== bon 2\nGESAMT\n===\n\n"
        with mock.patch("server.open", mock.mock_open(read_data=fals), create=True):
            r = self.client.get("/bonuri.json?cheie=" + ajutor.CHEIE_TEST)
        self.assertEqual(r.status_code, 200)
        bonuri = r.get_json()["bonuri"]
        self.assertEqual(len(bonuri), 2)
        self.assertTrue(bonuri[0].startswith("=== bon 2"))


class ProceseazaApel(unittest.TestCase):
    """Telefonul luat din apel ajunge pe bon (Gemini e înlocuit cu un răspuns fals)."""

    def ruleaza(self, mesaj, comanda):
        fisier = mock.mock_open()
        with mock.patch.object(server, "citeste_comanda", return_value=comanda), \
             mock.patch("server.open", fisier, create=True), \
             mock.patch("builtins.print"):
            server.proceseaza_apel(mesaj)
        return "".join(c.args[0] for c in fisier().write.call_args_list)

    def test_telefonul_din_call_customer(self):
        mesaj = dict(RAPORT["message"], call={"customer": {"number": "+49 170 999999"}})
        scris = self.ruleaza(mesaj, {"adresa": "Hauptstraße 5", "telefon": "0151 1",
                                     "produse": [{"nume": "Pizza Salami", "cantitate": 1}]})
        self.assertIn("Telefon: +49 170 999999", scris)

    def test_telefonul_din_customer(self):
        mesaj = dict(RAPORT["message"], customer={"number": "+49 170 888888"})
        scris = self.ruleaza(mesaj, {"adresa": "Hauptstraße 5",
                                     "produse": [{"nume": "Pizza Salami", "cantitate": 1}]})
        self.assertIn("Telefon: +49 170 888888", scris)

    def test_fara_produse_nu_scrie_bon(self):
        scris = self.ruleaza(RAPORT["message"], {"adresa": "x", "produse": []})
        self.assertEqual(scris, "")

    def test_fara_transcriere_nu_cheama_gemini(self):
        with mock.patch.object(server, "citeste_comanda") as gemini, mock.patch("builtins.print"):
            server.proceseaza_apel({"type": "end-of-call-report"})
        gemini.assert_not_called()


if __name__ == "__main__":
    unittest.main()
