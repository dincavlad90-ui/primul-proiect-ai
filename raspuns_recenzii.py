from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

with open("recenzie.txt", encoding="utf-8") as f:
    recenzie = f.read()

prompt = f"""Ești proprietarul unei pizzerii din Hiltenfingen.
1. Spune dacă recenzia de mai jos e pozitivă, neutră sau negativă.
2. Scrie un răspuns politicos și profesional, în limba germană, de maximum 3 propoziții.

Recenzie:
{recenzie}"""

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
)
print(response.text)
