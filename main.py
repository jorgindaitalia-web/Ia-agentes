import os
from fastapi import FastAPI
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process

app = FastAPI()

modelo_groq = "groq/openai/gpt-oss-120b"

class Pedido(BaseModel):
    tema: str

@app.get("/")
def inicio():
    return {"status": "Servidor dos Agentes Online!"}

@app.post("/gerar")
async def gerar_conteudo(pedido: Pedido):
    pesquisador = Agent(
        role="Pesquisador de Ideias",
        goal="Descobrir as melhores tendências e ideias sobre {tema}",
        backstory="Você é um especialista em encontrar oportunidades e ideias inovadoras.",
        llm=modelo_groq
    )

    redator = Agent(
        role="Redator Criativo",
        goal="Transformar a pesquisa sobre {tema} em um texto claro, envolvente e bem estruturado",
        backstory="Você escreve textos diretos, fáceis de ler e muito persuasivos.",
        llm=modelo_groq
    )

    revisor = Agent(
        role="Revisor de Qualidade",
        goal="Revisar o texto final para garantir que não tenha erros e esteja pronto para publicar",
        backstory="Você é exigente e deixa o texto impecável.",
        llm=modelo_groq
    )

    tarefa1 = Task(
        description="Pesquise 3 ideias fortes sobre {tema}.",
        expected_output="Lista com 3 pontos principais.",
        agent=pesquisador
    )

    tarefa2 = Task(
        description="Escreva um roteiro curto usando as ideias pesquisadas.",
        expected_output="Roteiro pronto.",
        agent=redator
    )

    tarefa3 = Task(
        description="Revise e entregue a versão final organizada.",
        expected_output="Texto final revisado.",
        agent=revisor
    )

    equipe = Crew(
        agents=[pesquisador, redator, revisor],
        tasks=[tarefa1, tarefa2, tarefa3],
        process=Process.sequential
    )

    resultado = await equipe.kickoff_async(inputs={"tema": pedido.tema})
    return {"resposta": str(resultado)}
