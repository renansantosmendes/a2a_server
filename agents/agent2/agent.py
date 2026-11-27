"""Creation of the agent 2 deep agent and its A2A delegation tool."""

from typing import Any

from deepagents import create_deep_agent
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from agents.agent2.config import (
    MODEL_NAME,
    SYSTEM_PROMPT,
    TARGET_AGENT_NAME,
    TEMPERATURE,
)
from server.a2a_client import ask_agent


def build_tools(base_url: str) -> list[BaseTool]:
    """Create the tools that let agent 2 call agent 1 over A2A.

    Parameters
    ----------
    base_url : str
        Public base URL of the server, used to build the URL of the
        target agent.

    Returns
    -------
    list[BaseTool]
        List with the ``consultar_agente1`` tool.

    Example
    -------
    >>> tools = build_tools("http://127.0.0.1:8000")
    """
    target_url = f"{base_url}/{TARGET_AGENT_NAME}"

    @tool
    async def consultar_agente1(pergunta: str) -> str:
        """Ask agent 1 a question over the A2A protocol and return its answer.

        Use this tool whenever the user's question needs an answer from
        agent 1.

        Parameters
        ----------
        pergunta : str
            Question to send to agent 1.

        Returns
        -------
        str
            Answer text produced by agent 1.
        """
        return await ask_agent(target_url, pergunta)

    return [consultar_agente1]


def build_agent(base_url: str) -> Any:
    """Create the deep agent of agent 2.

    Parameters
    ----------
    base_url : str
        Public base URL of the server, passed to the delegation tool.

    Returns
    -------
    Any
        Compiled deep agent with the OpenAI chat model and the
        ``consultar_agente1`` tool.

    Example
    -------
    >>> agent = build_agent("http://127.0.0.1:8000")
    """
    return create_deep_agent(
        model=ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE),
        tools=build_tools(base_url),
        system_prompt=SYSTEM_PROMPT,
    )
