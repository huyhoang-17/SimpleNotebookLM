import os
from dotenv import load_dotenv
from google import genai

from retrieve_generate import GEMINI_MODEL


load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
print("GOOGLE_API_KEY =", repr(API_KEY))

if not API_KEY:
    raise SystemExit("Chưa thấy biến môi trường GOOGLE_API_KEY")

client = genai.Client(api_key=API_KEY)

while True:
    msg = input("Bạn: ").strip()
    if msg.lower() in {"exit", "quit", "/exit"}:
        break

    GEMINI_MODEL = os.getenv("GEMINI_MODEL")
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=msg,
    )
    print("Gemini:", response.text)