import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

with open("menu.json", encoding="utf-8") as f:
    meniu = json.load(f)

with open("comanda.txt", encoding="utf-8") as f:
    text = f.read()

prompt = f"""Ești asistentul unei pizzerii din Hiltenfingen.
Din textul comenzii, scoate un JSON cu câmpurile:
"adresa", "telefon", "produse" (listă de obiecte cu "nume" și "cantitate").
Folosește DOAR numele din meniu: {list(meniu.keys())}.
Dacă ceva lipsește sau nu e în meniu, pune null.
Răspunde doar cu JSON.

Comanda: {text}"""

raspuns = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
    config={"response_mime_type": "application/json"},
)
comanda = json.loads(raspuns.text)

total = 0
print("=" * 32)
print("PIZZA SERVICE HILTENFINGEN")
print(datetime.now().strftime("%d.%m.%Y  %H:%M"))
print("Adresa :", comanda.get("adresa"))
print("Telefon:", comanda.get("telefon"))
print("-" * 32)
for p in comanda.get("produse") or []:
    nume, cant = p["nume"], p["cantitate"]
    if nume in meniu:
        pret = meniu[nume] * cant
        total += pret
        print(f"{cant} x {nume:<14} {pret:6.2f} EUR")
    else:
        print(f"! Necunoscut: {nume}")
print("-" * 32)
print(f"TOTAL: {total:.2f} EUR")
