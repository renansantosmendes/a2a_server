"""Tests for the agent 1 configuration and builder."""

import pytest

from agents.agent1.agent import build_agent
from agents.agent1.config import MODEL_NAME, TEMPERATURE


def test_agent1_model_settings_are_declared() -> None:
    """Declare the model name and temperature in the configuration."""
    assert MODEL_NAME == "gpt-4o-mini"
    assert TEMPERATURE == 0


def test_build_agent_returns_a_runnable_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build the deep agent with a placeholder key and no network calls."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    agent = build_agent("https://host.test")

    assert hasattr(agent, "ainvoke")
