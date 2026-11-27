"""Builds the A2A AgentCard advertised by each agent."""

from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from a2a.utils.constants import PROTOCOL_VERSION_1_0

from server.registry import AgentSpec


def build_agent_card(
    spec: AgentSpec,
    rpc_url: str,
) -> AgentCard:
    """Create the AgentCard of one agent.

    Parameters
    ----------
    spec : AgentSpec
        Specification of the agent, with its name, description and skill.
    rpc_url : str
        Public URL of the agent's JSON-RPC endpoint.

    Returns
    -------
    AgentCard
        AgentCard with the JSON-RPC interface and one text skill.

    Example
    -------
    >>> card = build_agent_card(spec, "https://host/agent1")
    """
    skill = AgentSkill(
        id=spec.skill_id,
        name=spec.skill_name,
        description=spec.skill_description,
        tags=["demo"],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    )
    interface = AgentInterface(
        url=rpc_url,
        protocol_binding="JSONRPC",
        protocol_version=PROTOCOL_VERSION_1_0,
    )
    return AgentCard(
        name=spec.display_name,
        description=spec.description,
        version="0.1.0",
        supported_interfaces=[interface],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[skill],
    )
