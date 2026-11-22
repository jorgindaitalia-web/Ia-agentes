import os
import base64
import urllib.parse
from typing import Optional
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import edge_tts

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

async def gerar_voz_mp3(texto: str) -> str:
    comunicador = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
    bytes_audio = b""
    async for pedaco in comunicador.stream():
        if pedaco["type"] == "audio":
            bytes_audio += pedaco["data"]
    audio_b64 = base64.b64encode(bytes_audio).decode("utf-8")
    return f"data:audio/mp3;base64,{audio_b64}"

@app.get("/", response_class=HTMLResponse)
def abrir_app():
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho_html = os.path.join(pasta, "index.html")
    with open(caminho_html, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/transcrever")
async def transcrever_audio(audio: UploadFile = File(...)):
    try:
        conteudo = await audio.read()
        transcricao = cliente_groq.audio.transcriptions.create(
            file=(audio.filename or "voz.webm", conteudo),
            model="whisper-large-v3-turbo",
            language="pt"
        )
        return {"texto": transcricao.text}
    except Exception as erro:
        return {"texto": "", "erro": str(erro)}

@app.post("/chat")
async def conversar(dados: Mensagem):
    try:
        texto_baixo = dados.texto.lower().strip()
        palavras_imagem = ["imagem", "foto", "desenh", "ilustra", "arte", "retrato", "pintura", "logo", "papel de parede"]
        verbos_acao = ["cri", "ger", "faz", "faça", "faca", "mostr", "quero", "manda", "mande", "produz"]
        pediu_imagem = (
            not dados.imagem_base64
            and any(p in texto_baixo for p in palavras_imagem)
            and (any(v in texto_baixo for v in verbos_acao) or len(texto_baixo.split()) <= 6)
        )

        if pediu_imagem:
            traducao = cliente_groq.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "Extract the visual subject and write a detailed image prompt in English. Reply ONLY with the prompt."},
                    {"role": "user", "content": dados.texto}
                ]
            )
            texto_en = next(iter(traducao.choices)).message.content.strip()
            prompt_en = urllib.parse.quote(texto_en)
            url_imagem = f"https://pollinations.ai{prompt_en}?width=1024&height=1024&nologo=true"
            msg_resposta = "Aqui está a imagem que você pediu."
            audio_mp3 = await gerar_voz_mp3(msg_resposta)
            return {"resposta": msg_resposta, "imagem_gerada": url_imagem, "audio_mp3": audio_mp3}

        if dados.imagem_base64:
            resposta = cliente_groq.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": dados.texto or "Descreva esta imagem em português de forma direta."},
                        {"type": "image_url", "image_url": {"url": dados.imagem_base64}}
                    ]
                }],
                temperature=0.5
            )
            texto_final = next(iter(resposta.choices)).message.content
            audio_mp3 = await gerar_voz_mp3(texto_final)
            return {"resposta": texto_final, "imagem_gerada": None, "audio_mp3": audio_mp3}

        resposta = cliente_groq.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Você é um assistente pessoal rápido e direto. Responda sempre em português de forma curta e natural, sem asteriscos ou símbolos estranhos."},
                {"role": "user", "content": dados.texto}
            ],
            temperature=0.6
        )
        texto_final = next(iter(resposta.choices)).message.content
        audio_mp3 = await gerar_voz_mp3(texto_final)
        return {"resposta": texto_final, "imagem_gerada": None, "audio_mp3": audio_mp3}

    except Exception as erro:
        return {"resposta": f"Erro no servidor: {str(erro)}", "imagem_gerada": None, "audio_mp3": None}
