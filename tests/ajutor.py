"""Pregătire comună pentru teste.

- Mută directorul curent în rădăcina proiectului (demo.py citește menu.json de acolo).
- Înlocuiește load_dotenv cu o funcție goală, ca testele să NU citească .env.
- Pune parole false în mediu, înainte să fie importat server.py.
"""
import os
import sys
import types

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RADACINA)
if RADACINA not in sys.path:
    sys.path.insert(0, RADACINA)

dotenv_fals = types.ModuleType("dotenv")
dotenv_fals.load_dotenv = lambda *a, **k: False
sys.modules["dotenv"] = dotenv_fals

PAROLA_TEST = "parola-de-test"
CHEIE_TEST = "cheie-de-test"
os.environ["VAPI_WEBHOOK_SECRET"] = PAROLA_TEST
os.environ["BONURI_KEY"] = CHEIE_TEST
