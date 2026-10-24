import os
import sys

from google import genai

chave = os.getenv("GEMINI_API_KEY")
modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

if not chave:
    print("GEMINI_API_KEY não definida nesta sessão do PowerShell")
    sys.exit(1)

try:
    resposta = genai.Client(api_key=chave).models.generate_content(
        model=modelo, contents="Responda apenas: ok"
    )
    print("OK:", resposta.text)
except Exception as erro:
    print("ERRO:", type(erro).__name__)
    print(str(erro)[:300])