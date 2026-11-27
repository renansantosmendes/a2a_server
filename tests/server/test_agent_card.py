"""Tests for the AgentCard builder in server.agent_card."""

from server.agent_card import build_agent_card
from server.registry import AgentSpec


def make_spec() -> AgentSpec:
    """Create an agent specification used by the card tests.

    Returns
    -------
    AgentSpec
        Specification with fixed identity and skill values.
    """
    return AgentSpec(
        name="agent1",
        display_name="Agent 1",
        description="Answers questions.",
        skill_id="answer",
        skill_name="Answer questions",
        skill_description="Answers general questions.",
        build=lambda base_url: None,
    )


def test_build_agent_card_uses_spec_identity() -> None:
    """Copy the name, description and skill fields from the spec."""
    card = build_agent_card(make_spec(), "https://host/agent1")

    assert card.name == "Agent 1"
    assert card.description == "Answers questions."
    assert card.skills[0].id == "answer"
    assert card.skills[0].name == "Answer questions"


def test_build_agent_card_advertises_the_rpc_url() -> None:
    """Expose the given URL as the JSON-RPC interface."""
    card = build_agent_card(make_spec(), "https://host/agent1")

    interface = card.supported_interfaces[0]
    assert interface.url == "https://host/agent1"
    assert interface.protocol_binding == "JSONRPC"
