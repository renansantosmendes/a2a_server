"""Pydantic models of the HTTP responses served by the application."""

from pydantic import BaseModel


class AgentRoute(BaseModel):
    """Routes published for one agent.

    Attributes
    ----------
    name : str
        Route name of the agent, equal to its folder name.
    rpc : str
        Path of the JSON-RPC endpoint of the agent.
    agent_card : str
        Path of the AgentCard of the agent.
    """

    name: str
    rpc: str
    agent_card: str


class AgentIndex(BaseModel):
    """Index of every agent served by the application.

    Attributes
    ----------
    agents : list[AgentRoute]
        One entry per agent, in alphabetical order.
    """

    agents: list[AgentRoute]
