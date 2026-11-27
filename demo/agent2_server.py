"""Starts agent 2, a deep agent that consults agent 1 over A2A."""

from typing import Any

import uvicorn
from deepagents import create_deep_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from demo.agent1_server import AGENT1_URL, MODEL_NAME
from demo.common import (
    DeepAgentExecutor,
    ask_agent,
    build_agent_card,
    create_app,
    load_environment,
)

AGENT2_HOST = "127.0.0.1"
AGENT2_PORT = 9102
AGENT2_URL = f"http://{AGENT2_HOST}:{AGENT2_PORT}/"
SYSTEM_PROMPT = (
    "Voce e o Agente 2. Para responder ao usuario, use a ferramenta "
    "consultar_agente1 com a pergunta e entregue a resposta do Agente 1 "
    "de forma clara, em portugues."
)


@tool
async def consultar_agente1(pergunta: str) -> str:
    """Ask agent 1 a question over the A2A protocol and return its answer.

    Use this tool whenever the user's question needs an answer from agent 1.

    Parameters
    ----------
    pergunta : str
        Question to send to agent 1.

    Returns
    -------
    str
        Answer text produced by agent 1.
    """
    return await ask_agent(AGENT1_URL, pergunta)


def create_agent2() -> Any:
    """Create the deep agent that delegates questions to agent 1.

    Returns
    -------
    Any
        Compiled deep agent with the OpenAI chat model and the
        ``consultar_agente1`` tool.

    Example
    -------
    >>> agent = create_agent2()
    """
    return create_deep_agent(
        model=ChatOpenAI(model=MODEL_NAME, temperature=0),
        tools=[consultar_agente1],
        system_prompt=SYSTEM_PROMPT,
    )


def main() -> None:
    """Start the agent 2 HTTP server on port 9102.

    Returns
    -------
    None
    """
    load_environment()
    card = build_agent_card(
        name="Agent 2",
        description="Deep agent that answers questions by consulting agent 1.",
        rpc_url=AGENT2_URL,
        skill_id="answer-with-agent1",
        skill_name="Answer through agent 1",
        skill_description="Answers questions using agent 1 over A2A.",
    )
    app = create_app(card, DeepAgentExecutor(create_agent2()))
    uvicorn.run(app, host=AGENT2_HOST, port=AGENT2_PORT)


if __name__ == "__main__":
    main()
