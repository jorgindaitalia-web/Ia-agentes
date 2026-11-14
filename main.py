import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

# Libera qualquer aplicativo ou site para conversar com o seu servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cliente_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODELO = "openai/gpt-oss-120b"

class Pedido(BaseModel):
    tema: str

def rodar_agente(papel: str, instrucao: str, entrada: str) -> str:
    resposta = cliente_groq.chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system", "content": f"Você é um {papel}. {instrucao}"},
            {"role": "user", "content": entrada}
        ],
        temperature=0.5
    )
    return resposta.choices[0].message.content

@app.get("/")
def inicio():
    return {"status": "Servidor dos 3 Agentes Online!"}

@app.post("/gerar")
def gerar_conteudo(pedido: Pedido):
    # 1. Agente Pesquisador
    ideias = rodar_agente(
        papel="Pesquisador de Ideias",
        instrucao="Descubra as melhores tendências e liste 3 ideias fortes e práticas.",
        entrada=f"Pesquise 3 ideias fortes sobre: {pedido.tema}"
    )

    # 2. Agente Redator
    rascunho = rodar_agente(
        papel="Redator Criativo",
        instrucao="Transforme a pesquisa recebida em um texto claro, envolvente e bem estruturado.",
        entrada=f"Crie um roteiro ou conteúdo completo usando estas ideias:\n{ideias}"
    )

    # 3. Agente Revisor
    texto_final = rodar_agente(
        papel="Revisor de Qualidade",
        instrucao="Revise o texto recebido para eliminar erros, melhorar a clareza e entregar a versão final organizada em português.",
        entrada=f"Revise e entregue a versão final impecável deste texto:\n{rascunho}"
    )

    return {"resposta": texto_final}
