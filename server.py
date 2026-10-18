import hmac
import os
import threading

from flask import Flask, abort, request, send_file

from demo import citeste_comanda, fa_bon, transcript_din_apel

app = Flask(__name__)
SECRET = os.getenv("VAPI_WEBHOOK_SECRET")
CHEIE_BONURI = os.getenv("BONURI_KEY")
blocare_fisier = threading.Lock()


def parola_corecta():
    """Vapi trimite parola în antetul X-Vapi-Secret (sau ca Bearer token)."""
    primit = request.headers.get("X-Vapi-Secret", "")
    auth = request.headers.get("Authorization", "")
    if not primit and auth.startswith("Bearer "):
        primit = auth[len("Bearer "):]
    return hmac.compare_digest(primit.encode(), SECRET.encode())


def cheie_corecta():
    """Ecranul cu bonuri se deschide doar cu ?cheie=... din .env (BONURI_KEY)."""
    primit = request.args.get("cheie", "")
    return bool(CHEIE_BONURI) and hmac.compare_digest(primit.encode(), CHEIE_BONURI.encode())


def proceseaza_apel(mesaj):
    try:
        text = transcript_din_apel(mesaj)
        if not text.strip():
            print("Apel fără transcriere, nu fac bon.")
            return
        comanda = citeste_comanda(text)
        if not comanda.get("produse"):
            print("Apel fără produse (probabil întrerupt), nu fac bon.", flush=True)
            return
        telefon_apel = (
            ((mesaj.get("call") or {}).get("customer") or {}).get("number")
            or (mesaj.get("customer") or {}).get("number")
        )
        bon = fa_bon(comanda, telefon_apel)
        print(bon, flush=True)
        with blocare_fisier, open("bonuri.txt", "a", encoding="utf-8") as f:
            f.write(bon + "\n\n")
    except Exception as e:
        print(f"! Eroare la procesarea apelului: {e}", flush=True)


@app.post("/vapi")
def vapi():
    if not parola_corecta():
        return {"eroare": "parolă greșită"}, 401
    mesaj = (request.get_json(silent=True) or {}).get("message") or {}
    if mesaj.get("type") == "end-of-call-report":
        # Gemini durează câteva secunde; răspundem imediat ca Vapi să nu reîncerce.
        threading.Thread(target=proceseaza_apel, args=(mesaj,)).start()
    return {"ok": True}


@app.get("/bonuri")
def ecran_bonuri():
    if not cheie_corecta():
        abort(404)
    return send_file("bonuri.html")


@app.get("/bonuri.json")
def lista_bonuri():
    if not cheie_corecta():
        abort(404)
    try:
        with blocare_fisier, open("bonuri.txt", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    bonuri = [b.strip() for b in text.split("\n\n") if b.strip().startswith("=")]
    return {"bonuri": bonuri[-20:][::-1]}  # cele mai noi primele


if __name__ == "__main__":
    if not SECRET:
        raise SystemExit("Lipsește VAPI_WEBHOOK_SECRET din fișierul .env")
    if not CHEIE_BONURI:
        print("Atenție: lipsește BONURI_KEY din .env, ecranul cu bonuri e oprit.")
    app.run(host="127.0.0.1", port=5000)
