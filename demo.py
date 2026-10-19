import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from difflib import get_close_matches

from dotenv import load_dotenv

load_dotenv()

with open("menu.json", encoding="utf-8") as f:
    meniu = json.load(f)
mic = {nume.lower(): nume for nume in meniu}
# Mărimea fără nume ("") = mărimea mică, cea din menu.json.
MARIMI_MICI = {"", "klein", "kleine", "small", "mică", "mica", "mic"}


def gaseste_produs(nume):
    """Întoarce (nume din meniu, None) sau (None, motiv)."""
    if not nume:
        return None, "kein Name"
    q = str(nume).strip().lower()
    if q in mic:
        return mic[q], None
    if "pizza " + q in mic:
        return mic["pizza " + q], None
    potrivite = [orig for low, orig in mic.items() if q in low]
    if len(potrivite) == 1:
        return potrivite[0], None
    if len(potrivite) > 1:
        return None, "unklar: " + " / ".join(potrivite[:3])
    apropiate = get_close_matches(q, list(mic), n=1, cutoff=0.75)
    if apropiate:
        return mic[apropiate[0]], None
    return None, "nicht im Menü"


def transcript_din_apel(apel):
    art = apel.get("artifact") or {}
    if art.get("transcript"):
        return art["transcript"]
    if apel.get("transcript"):
        return apel["transcript"]
    linii = []
    for m in art.get("messages") or apel.get("messages") or []:
        rol = m.get("role")
        text = m.get("message") or m.get("content")
        if rol in ("user", "bot", "assistant") and text:
            linii.append(("Client" if rol == "user" else "Robot") + ": " + text)
    return "\n".join(linii)


def ultimul_apel():
    cheie = os.getenv("VAPI_API_KEY")
    if not cheie:
        sys.exit("Lipsește VAPI_API_KEY din fișierul .env")
    cerere = urllib.request.Request(
        "https://api.vapi.ai/call?limit=5",
        headers={"Authorization": "Bearer " + cheie, "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(cerere, timeout=30) as r:
            apeluri = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Vapi a răspuns cu eroarea {e.code}. Verifică cheia din .env.")
    if not apeluri:
        sys.exit("Nu există niciun apel în Vapi.")
    apeluri.sort(key=lambda a: a.get("createdAt") or "", reverse=True)
    for a in apeluri:
        if transcript_din_apel(a).strip():
            return a
    sys.exit("Ultimul apel nu are încă transcriere. Așteaptă 10 secunde și rulează din nou.")


def citeste_comanda(text):
    from google import genai

    client = genai.Client()
    prompt = f"""Ești asistentul unei pizzerii din Hiltenfingen.
Mai jos e o convorbire (sau un text) cu un client. Scoate UN SINGUR obiect JSON cu:
"adresa", "oras", "telefon", "produse" (listă de obiecte cu "nume", "cantitate" și "marime").
"marime" e mărimea pizzei (klein / normal / groß / Familie etc.) DOAR dacă clientul a spus-o; altfel pune null. Nu o ghici.
"adresa" conține doar strada și numărul, fără oraș.
"oras" e orașul DOAR dacă clientul l-a spus explicit. Nu-l ghici și nu-l deduce din locul pizzeriei; dacă nu l-a spus, pune null.
Folosește varianta FINALĂ, cea confirmată de client. Ignoră ce a propus robotul și clientul n-a acceptat.
Pentru fiecare produs folosește numele exact din meniu dacă ești sigur: {list(meniu.keys())}.
Dacă nu ești sigur, scrie numele cum l-a spus clientul.
Dacă adresa sau telefonul lipsesc, pune null.
Răspunde doar cu JSON.

Convorbire:
{text}"""
    raspuns = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    comanda = json.loads(raspuns.text)
    if isinstance(comanda, list):
        comanda = comanda[0] if comanda else {}
    return comanda


def fa_bon(c, telefon_apel=None):
    total = 0
    de_verificat = False
    # Numărul din apel e sigur; cel spus de client e doar rezervă.
    telefon = telefon_apel or c.get("telefon")
    linii = [
        "=" * 36,
        "PIZZA SERVICE HILTENFINGEN",
        datetime.now().strftime("%d.%m.%Y  %H:%M"),
        "Adresse: " + (c.get("adresa") or "Straße fehlt") + ", " + (c.get("oras") or "Ort fehlt"),
        "Telefon: " + (telefon or "fehlt"),
        "-" * 36,
    ]
    for p in c.get("produse") or []:
        cant = p.get("cantitate") or 1
        nume, motiv = gaseste_produs(p.get("nume"))
        # Gemini poate trimite numere ca text ("2") sau mărimea ca număr (32).
        marime = str(p.get("marime") or "").strip()
        eticheta = f" ({marime})" if marime else ""
        try:
            cant = int(cant)
        except (TypeError, ValueError):
            nume, motiv = None, "Menge unklar"
        if nume and marime.lower() not in MARIMI_MICI:
            # menu.json are doar prețul mărimii mici, deci nu scriem un preț pentru altă mărime.
            de_verificat = True
            linii.append(f"{cant} x {nume}{eticheta}")
            linii.append("! Preis prüfen: Größe nicht im Menü hinterlegt")
        elif nume:
            pret = meniu[nume] * cant
            total += pret
            linii.append(f"{cant} x {nume}{eticheta} - {pret:.2f} EUR")
        else:
            de_verificat = True
            linii.append(f"! {cant} x {p.get('nume')}{eticheta} ({motiv})")
    linii.append("-" * 36)
    linii.append(f"GESAMT: {total:.2f} EUR")
    if de_verificat:
        linii.append("! ACHTUNG: Artikel prüfen, Summe unvollständig")
    if not c.get("adresa") or not telefon:
        linii.append("! ACHTUNG: Adresse oder Telefon fehlt")
    linii.append("=" * 36)
    return "\n".join(linii)


if __name__ == "__main__":
    telefon_apel = None
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        apel = ultimul_apel()
        text = transcript_din_apel(apel)
        telefon_apel = (apel.get("customer") or {}).get("number")
        print("--- Transcrierea apelului ---")
        print(text)
        print()
    bon = fa_bon(citeste_comanda(text), telefon_apel)
    print(bon)
    with open("bonuri.txt", "a", encoding="utf-8") as f:
        f.write(bon + "\n\n")
        