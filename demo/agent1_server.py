"""Starts agent 1, a deep agent that answers questions over A2A."""

from typing import Any

import uvicorn
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from demo.common import (
    DeepAgentExecutor,
    build_agent_card,
    create_app,
    load_environment,
)

AGENT1_HOST = "127.0.0.1"
AGENT1_PORT = 9101
AGENT1_URL = f"http://{AGENT1_HOST}:{AGENT1_PORT}/"
MODEL_NAME = "gpt-4o-mini"
SYSTEM_PROMPT = (
    "Voce e o Agente 1. Responda as perguntas em portugues, de forma "
    "clara e objetiva."
)


def create_agent1() -> Any:
    """Create the deep agent that answers questions for agent 2.

    Returns
    -------
    Any
        Compiled deep agent with the OpenAI chat model and no extra tools.

    Example
    -------
    >>> agent = create_agent1()
    """
    return create_deep_agent(
        model=ChatOpenAI(model=MODEL_NAME, temperature=0),
        system_prompt=SYSTEM_PROMPT,
    )


def main() -> None:
    """Start the agent 1 HTTP server on port 9101.

    Returns
    -------
    None
    """
    load_environment()
    card = build_agent_card(
        name="Agent 1",
        description="Deep agent that answers general questions.",
        rpc_url=AGENT1_URL,
        skill_id="answer",
        skill_name="Answer questions",
        skill_description="Answers general questions in Portuguese.",
    )
    app = create_app(card, DeepAgentExecutor(create_agent1()))
    uvicorn.run(app, host=AGENT1_HOST, port=AGENT1_PORT)


if __name__ == "__main__":
    main()
