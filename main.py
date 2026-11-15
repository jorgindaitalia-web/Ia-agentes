import os
import urllib.parse
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cliente_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class Mensagem(BaseModel):
    texto: str
    imagem_base64: Optional[str] = None

@app.get("/")
def inicio():
    return {"status": "Assistente Completo Online!"}

@app.post("/chat")
def conversar(dados: Mensagem):
    texto_baixo = dados.texto.lower().strip()

    # 1. Se o usuário pedir para criar/gerar uma imagem (sem enviar foto)
    gatilhos_imagem = ["crie uma imagem", "gere uma imagem", "desenhe", "faça uma imagem", "criar imagem", "gerar imagem"]
    if not dados.imagem_base64 and any(g in texto_baixo for g in gatilhos_imagem):
        # Traduz o pedido rapidamente para inglês para a imagem sair perfeita
        traducao = cliente_groq.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Traduza a descrição da imagem para inglês em uma frase curta e detalhada. Responda apenas a tradução."},
                {"role": "user", "content": dados.texto}
            ]
        )
        prompt_en = urllib.parse.quote(traducao.choices[0].message.content.strip())
        url_imagem = f"https://pollinations.ai{prompt_en}?width=1024&height=1024&nologo=true"
        return {
            "resposta": "Aqui está a imagem que você pediu:",
            "imagem_gerada": url_imagem
        }

    # 2. Se o usuário enviou uma foto para a IA ler/analisar
    if dados.imagem_base64:
        resposta = cliente_groq.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": dados.texto or "Descreva esta imagem e responda em português."},
                        {"type": "image_url", "image_url": {"url": dados.imagem_base64}}
                    ]
                }
            ],
            temperature=0.5
        )
        return {"resposta": resposta.choices[0].message.content, "imagem_gerada": None}

    # 3. Conversa normal ultra rápida (responde perguntas direto, sem formato de vídeo)
    resposta = cliente_groq.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": "Você é um assistente pessoal rápido, inteligente e direto. Responda sempre em português de forma clara, natural e objetiva, sem transformar tudo em roteiro."
            },
            {"role": "user", "content": dados.texto}
        ],
        temperature=0.6
    )
    return {"resposta": resposta.choices[0].message.content, "imagem_gerada": None}
