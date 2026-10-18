import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

with open("menu.json", encoding="utf-8") as f:
    meniu = json.load(f)


def citeste_comanda(text):
    prompt = f"""Ești asistentul unei pizzerii din Hiltenfingen.
Din textul comenzii, scoate UN SINGUR obiect JSON cu câmpurile:
"adresa", "telefon", "produse" (listă de obiecte cu "nume" și "cantitate").
Folosește numele din meniu: {list(meniu.keys())}.
Dacă adresa sau telefonul lipsesc, pune null.
Dacă un produs nu e în meniu, scrie numele lui exact cum l-a spus clientul.
Răspunde doar cu JSON.

Comanda: {text}"""
    raspuns = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    comanda = json.loads(raspuns.text)
    if isinstance(comanda, list):
        comanda = comanda[0] if comanda else {}
    return comanda


def fa_bon(comanda):
    total = 0
    linii = [
        "=" * 32,
        "PIZZA SERVICE HILTENFINGEN",
        datetime.now().strftime("%d.%m.%Y  %H:%M"),
        "Adresa : " + str(comanda.get("adresa")),
        "Telefon: " + str(comanda.get("telefon")),
        "-" * 32,
    ]
    for p in comanda.get("produse") or []:
        nume = p.get("nume")
        cant = p.get("cantitate") or 1
        if nume in meniu:
            pret = meniu[nume] * cant
            total += pret
            linii.append(f"{cant} x {nume:<14} {pret:6.2f} EUR")
        else:
            linii.append(f"! NU E ÎN MENIU: {nume}")
    linii.append("-" * 32)
    linii.append(f"TOTAL: {total:.2f} EUR")
    if not comanda.get("adresa") or not comanda.get("telefon"):
        linii.append("! ATENȚIE: lipsește adresa sau telefonul")
    linii.append("=" * 32)
    return "\n".join(linii)


print("Robot de comenzi. Scrie comanda clientului. Enter gol = ieșire.")
while True:
    text = input("\nComanda: ").strip()
    if not text:
        break
    try:
        comanda = citeste_comanda(text)
    except Exception as e:
        print("Eroare, încearcă din nou:", e)
        continue
    bon = fa_bon(comanda)
    print(bon)
    with open("bonuri.txt", "a", encoding="utf-8") as f:
        f.write(bon + "\n\n")
        