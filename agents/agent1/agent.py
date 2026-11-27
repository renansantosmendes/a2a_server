"""Creation of the agent 1 deep agent."""

from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from agents.agent1.config import MODEL_NAME, SYSTEM_PROMPT


def build_agent(base_url: str) -> Any:
    """Create the deep agent of agent 1.

    Parameters
    ----------
    base_url : str
        Public base URL of the server. Agent 1 does not call other agents,
        so it is not used.

    Returns
    -------
    Any
        Compiled deep agent with the OpenAI chat model and no extra tools.

    Example
    -------
    >>> agent = build_agent("http://127.0.0.1:8000")
    """
    return create_deep_agent(
        model=ChatOpenAI(model=MODEL_NAME, temperature=0),
        system_prompt=SYSTEM_PROMPT,
    )
