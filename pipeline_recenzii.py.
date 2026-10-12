
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise SystemExit(
        "Lipsește GEMINI_API_KEY din fișierul .env local."
    )

MODEL = "gemini-3-flash-preview"


def genereaza(client, prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )
    text = (response.text or "").strip()

    if not text:
        raise RuntimeError("AI-ul nu a returnat un răspuns.")

    return text


def main():
    fisier = Path("recenzie.txt")

    if not fisier.exists():
        raise SystemExit(
            "Creează fișierul recenzie.txt cu o recenzie de test."
        )

    recenzie = fisier.read_text(encoding="utf-8").strip()

    if not recenzie:
        raise SystemExit("Fișierul recenzie.txt este gol.")

    client = genai.Client()

    # AI 1: analizează recenzia.
    analiza = genereaza(
        client,
        f"""
Analizează recenzia pentru o afacere din Germania.
Răspunde în română cu:
1. Sentiment: pozitiv, neutru sau negativ.
2. Problema principală.
3. Tonul recomandat pentru răspuns.
Nu inventa fapte.

Recenzie:
{recenzie}
""".strip(),
    )

    # AI 2: folosește analiza pentru a redacta răspunsul.
    raspuns = genereaza(
        client,
        f"""
Scrie un răspuns public în germană pentru această recenzie.
Maximum 3 propoziții, politicos și profesional.
Nu inventa fapte, reduceri, rambursări sau promisiuni.
Pentru o recenzie negativă, invită clientul să contacteze
direct afacerea, fără a cere date personale în public.
Returnează numai răspunsul final în germană.

Analiza:
{analiza}

Recenzia originală:
{recenzie}
""".strip(),
    )

    print("\n=== ANALIZA AI 1 ===\n")
    print(analiza)

    print("\n=== RĂSPUNS AI 2 ===\n")
    print(raspuns)

    print("\nVerifică răspunsul înainte de publicare.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Eroare: {exc}") from exc
