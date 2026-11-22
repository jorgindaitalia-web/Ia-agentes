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
    allow_credentials=False,
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
    try:
        texto_baixo = dados.texto.lower().strip()

        # 1. Detecta qualquer pedido para criar/gerar/mostrar imagem ou desenho
        palavras_imagem = [
            "imagem", "foto", "desenh", "ilustra", "arte", "retrato", "pintura", "logo", "papel de parede"
        ]
        verbos_acao = [
            "cri", "ger", "faz", "faça", "faca", "mostr", "quero", "manda", "mande", "produz"
        ]

        pediu_imagem = (
            not dados.imagem_base64
            and any(p in texto_baixo for p in palavras_imagem)
            and (any(v in texto_baixo for v in verbos_acao) or len(texto_baixo.split()) <= 6)
        )

        if pediu_imagem:
            traducao = cliente_groq.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract the visual subject from the user request and write a rich, detailed image generation prompt in English. Reply ONLY with the English prompt, nothing else."
                    },
                    {"role": "user", "content": dados.texto}
                ]
            )
            texto_en = traducao.choices.message.content.strip()
            prompt_en = urllib.parse.quote(texto_en)
            url_imagem = f"https://pollinations.ai{prompt_en}?width=1024&height=1024&nologo=true"
            return {
                "resposta": "Aqui está a imagem:",
                "imagem_gerada": url_imagem
            }

        # 2. Ler e responder sobre foto enviada
        if dados.imagem_base64:
            resposta = cliente_groq.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": dados.texto or "Descreva esta imagem e responda em português de forma direta."},
                            {"type": "image_url", "image_url": {"url": dados.imagem_base64}}
                        ]
                    }
                ],
                temperature=0.5
            )
            return {"resposta": resposta.choices.message.content, "imagem_gerada": None}

        # 3. Resposta rápida e direta em texto (sem dar aula nem enrolar)
        resposta = cliente_groq.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente pessoal rápido e direto. Responda sempre em português de forma curta, prática e natural, sem dar aulas longas, sem listas gigantes e sem usar asteriscos ou símbolos estranhos para que a leitura em voz alta fique limpa."
                },
                {"role": "user", "content": dados.texto}
            ],
            temperature=0.6
        )
        return {"resposta": resposta.choices.message.content, "imagem_gerada": None}

    except Exception as erro:
        return {"resposta": f"Erro no servidor: {str(erro)}", "imagem_gerada": None}
