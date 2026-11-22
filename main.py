import os
import base64
import socket
from typing import Optional
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import edge_tts
import httpx
import dns.resolver

_orig_getaddrinfo = socket.getaddrinfo
def _custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if isinstance(host, bytes):
        host = host.decode()
    try:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        res = dns.resolver.Resolver(configure=False)
        res.nameservers = ["8.8.8.8", "1.1.1.1"]
        ans = res.resolve(host, "A")
        ip = next(iter(ans)).to_text()
        return _orig_getaddrinfo(ip, port, family, type, proto, flags)

socket.getaddrinfo = _custom_getaddrinfo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

cliente_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

PAGINA = (
    '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/>'
    '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>'
    '<title>Agentes IA</title><style>'
    '*{box-sizing:border-box;margin:0;padding:0;font-family:sans-serif}'
    'body{background:#0b111a;color:#e2e8f0;display:flex;flex-direction:column;height:100dvh}'
    'header{background:#131c2a;padding:14px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b}'
    'header h1{font-size:18px;color:#38bdf8}'
    '#v{background:#10b981;color:#fff;border:none;padding:6px 12px;border-radius:20px;font-weight:bold}'
    '#v.off{background:#475569}'
    '#c{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}'
    '.m{max-width:85%;padding:12px;border-radius:16px;font-size:15px;line-height:1.4;word-wrap:break-word}'
    '.u{background:#0284c7;color:#fff;align-self:flex-end}'
    '.b{background:#1e293b;color:#f1f5f9;align-self:flex-start}'
    '.b img{max-width:100%;border-radius:10px;margin-top:8px;display:block}'
    '.o{margin-top:8px;background:#334155;color:#38bdf8;border:none;padding:5px 10px;border-radius:8px;font-size:12px}'
    'footer{background:#131c2a;padding:10px;display:flex;gap:8px;align-items:center;border-top:1px solid #1e293b}'
    'input[type=text]{flex:1;background:#1e293b;border:1px solid #334155;color:#fff;padding:12px;border-radius:24px;font-size:15px;outline:none}'
    '.i{width:44px;height:44px;border-radius:50%;border:none;background:#1e293b;color:#38bdf8;font-size:18px;flex-shrink:0}'
    '.g{background:#ef4444!important;color:#fff!important}'
    '#e{background:#10b981;color:#fff}'
    '</style></head><body>'
    '<header><h1>Agentes IA</h1><button id="v">Voz: ON</button></header>'
    '<div id="c"><div class="m b">Ola! Pode digitar, tocar no microfone para falar ou pedir uma imagem.</div></div>'
    '<footer><input type="file" id="f" accept="image/*" hidden/>'
    '<button class="i" id="bf">📷</button>'
    '<input type="text" id="t" placeholder="Escreva ou fale..."/>'
    '<button class="i" id="bm">🎤</button>'
    '<button class="i" id="e">➤</button></footer>'
    '<script>'
    'const c=document.getElementById("c"),t=document.getElementById("t"),e=document.getElementById("e"),'
    'bm=document.getElementById("bm"),bf=document.getElementById("bf"),f=document.getElementById("f"),v=document.getElementById("v");'
    'let va=true,fb=null,mr=null,ac=[],aa=null;'
    'v.onclick=()=>{va=!va;v.textContent=va?"Voz: ON":"Voz: OFF";v.classList.toggle("off",!va)};'
    'bf.onclick=()=>f.click();'
    'f.onchange=ev=>{const fl=ev.target.files;if(!fl)return;const r=new FileReader();'
    'r.onload=()=>{fb=r.result;t.placeholder="Foto anexada! Digite..."};r.readAsDataURL(fl)};'
    'function toc(b){if(!b)return;if(aa)aa.pause();aa=new Audio(b);aa.play().catch(()=>{})}'
    'function add(tx,tp,im=null,au=null){const d=document.createElement("div");d.className="m "+tp;d.textContent=tx;'
    'if(im){const i=document.createElement("img");i.src=im;d.appendChild(i)}'
    'if(au){const b=document.createElement("button");b.className="o";b.textContent="🔊 Ouvir";b.onclick=()=>toc(au);'
    'd.appendChild(document.createElement("br"));d.appendChild(b);if(va)toc(au)}'
    'c.appendChild(d);c.scrollTop=c.scrollHeight;return d}'
    'async function env(tm=null){const tx=tm||t.value.trim();if(!tx&&!fb)return;add(tx||"Foto","u");'
    't.value="";t.placeholder="Escreva ou fale...";const im=fb;fb=null;const cg=add("Pensando...","b");'
    'try{const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({texto:tx||"Descreva esta foto",imagem_base64:im})});'
    'const d=await r.json();cg.remove();add(d.resposta,"b",d.imagem_gerada,d.audio_mp3)'
    '}catch(er){cg.textContent="Erro de rede: "+er.message}}'
    'e.onclick=()=>env();t.onkeypress=ev=>{if(ev.key==="Enter")env()};'
    'bm.onclick=async()=>{if(mr&&mr.state==="recording"){mr.stop();bm.classList.remove("g");return}'
    'try{const s=await navigator.mediaDevices.getUserMedia({audio:true});mr=new MediaRecorder(s);ac=[];'
    'mr.ondataavailable=ev=>ac.push(ev.data);mr.onstop=async()=>{s.getTracks().forEach(k=>k.stop());'
    'const b=new Blob(ac,{type:"audio/webm"}),fd=new FormData();fd.append("audio",b,"v.webm");'
    't.placeholder="Ouvindo...";const r=await fetch("/transcrever",{method:"POST",body:fd});'
    'const d=await r.json();t.placeholder="Escreva ou fale...";if(d.texto)env(d.texto)};'
    'mr.start();bm.classList.add("g")}catch(er){alert("Permita o microfone no navegador!")}};'
    '</script></body></html>'
)

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

async def gerar_imagem_segura(prompt_en: str):
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        return None, "Configure GEMINI_API_KEY no Render."
    url = f"https://googleapis.com{chave.strip()}"
    payload = {
        "instances": [{"prompt": prompt_en}],
        "parameters": {"sampleCount": 1}
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            dados = resp.json()
            if "predictions" in dados and len(dados["predictions"]) > 0:
                b64 = next(iter(dados["predictions"]))["bytesBase64Encoded"]
                return f"data:image/jpeg;base64,{b64}", None
            return None, f"Aviso Google: {str(dados)[:130]}"
    except Exception as e:
        return None, f"Erro servidor: {str(e)[:120]}"

@app.get("/", response_class=HTMLResponse)
def abrir_app():
    return PAGINA

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
        if dados.imagem_base64:
            resposta = cliente_groq.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": dados.texto or "Descreva esta imagem em portugues de forma direta."},
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
                {
                    "role": "system",
                    "content": (
                        "Voce e um assistente pessoal rapido e direto. "
                        "Se o usuario pedir para criar, gerar, desenhar ou mostrar uma imagem/foto/desenho, "
                        "NAO explique como desenhar. Responda APENAS com o prefixo 'IMG:' seguido da descricao visual detalhada em ingles (ex: IMG: a futuristic car with wings flying in the sky). "
                        "Para qualquer outra pergunta, responda em portugues de forma curta, natural e sem asteriscos."
                    )
                },
                {"role": "user", "content": dados.texto}
            ],
            temperature=0.6
        )
        texto_final = next(iter(resposta.choices)).message.content.strip()

        if texto_final.startswith("IMG:"):
            prompt_en = texto_final[4:].strip()
            img_pronta, motivo_erro = await gerar_imagem_segura(prompt_en)
            if img_pronta:
                msg_resposta = "Aqui esta a imagem que voce pediu."
                audio_mp3 = await gerar_voz_mp3(msg_resposta)
                return {"resposta": msg_resposta, "imagem_gerada": img_pronta, "audio_mp3": audio_mp3}
            else:
                audio_mp3 = await gerar_voz_mp3(motivo_erro)
                return {"resposta": motivo_erro, "imagem_gerada": None, "audio_mp3": audio_mp3}

        audio_mp3 = await gerar_voz_mp3(texto_final)
        return {"resposta": texto_final, "imagem_gerada": None, "audio_mp3": audio_mp3}

    except Exception as erro:
        return {"resposta": f"Erro no servidor: {str(erro)}", "imagem_gerada": None, "audio_mp3": None}
