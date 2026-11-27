"""Tests for the delegation tool of agent 2."""

import asyncio
from unittest.mock import AsyncMock, patch

from agents.agent2.agent import build_tools
from agents.agent2.config import TARGET_AGENT_NAME, TEMPERATURE


def test_build_tools_exposes_consultar_agente1() -> None:
    """Expose one tool named consultar_agente1."""
    tools = build_tools("https://host.test")

    assert [tool.name for tool in tools] == ["consultar_agente1"]


def test_delegation_tool_calls_the_target_agent_url() -> None:
    """Send the question to the target agent route under the base URL."""
    tool = build_tools("https://host.test")[0]
    ask_mock = AsyncMock(return_value="Paris")

    with patch("agents.agent2.agent.ask_agent", ask_mock):
        answer = _run_tool(tool, "Capital da Franca?")

    assert answer == "Paris"
    ask_mock.assert_awaited_once_with(
        f"https://host.test/{TARGET_AGENT_NAME}",
        "Capital da Franca?",
    )


def test_agent2_temperature_is_read_from_config() -> None:
    """Keep the model temperature in the agent configuration."""
    assert TEMPERATURE == 0


def _run_tool(
    tool: object,
    question: str,
) -> str:
    """Invoke a LangChain tool from a synchronous test.

    Parameters
    ----------
    tool : object
        Tool created by build_tools.
    question : str
        Value of the ``pergunta`` argument.

    Returns
    -------
    str
        Output of the tool.
    """
    return asyncio.run(tool.ainvoke({"pergunta": question}))
