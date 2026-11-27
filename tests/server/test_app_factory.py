"""Tests for the routes built by server.app_factory.create_app."""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from server.app_factory import create_app

BASE_URL = "https://example.test"


@pytest.fixture(autouse=True)
def fake_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a placeholder API key so the chat models can be created.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to set the environment variable for one test.

    Returns
    -------
    None
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the real agents folder.

    Returns
    -------
    TestClient
        Client for the application built with the project agents.
    """
    return TestClient(create_app(base_url=BASE_URL))


def test_index_lists_every_agent_folder(client: TestClient) -> None:
    """Return the agent routes from the index endpoint."""
    response = client.get("/")

    names = [agent["name"] for agent in response.json()["agents"]]
    assert names == ["agent1", "agent2"]


def test_agent_card_is_served_under_the_agent_route(
    client: TestClient,
) -> None:
    """Serve each card at /<name>/.well-known/agent-card.json."""
    response = client.get("/agent1/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Agent 1"
    assert card["supportedInterfaces"][0]["url"] == f"{BASE_URL}/agent1"


def test_unknown_agent_route_returns_not_found(client: TestClient) -> None:
    """Return 404 for a card of an agent folder that does not exist."""
    response = client.get("/agent9/.well-known/agent-card.json")

    assert response.status_code == 404


def test_create_app_serves_only_the_folders_given(tmp_path: Path) -> None:
    """Build routes from an agents folder that only has agent1."""
    source_agents = Path(__file__).resolve().parents[2] / "agents"
    target = tmp_path / "agents"
    target.mkdir()
    (target / "__init__.py").write_text("", encoding="utf-8")
    agent1_source = source_agents / "agent1"
    agent1_target = target / "agent1"
    agent1_target.mkdir()
    for file_name in ("__init__.py", "config.py", "agent.py"):
        content = (agent1_source / file_name).read_text(encoding="utf-8")
        (agent1_target / file_name).write_text(content, encoding="utf-8")

    app = create_app(base_url=BASE_URL, agents_dir=target)
    local_client = TestClient(app)

    agent1_card = local_client.get("/agent1/.well-known/agent-card.json")
    agent2_card = local_client.get("/agent2/.well-known/agent-card.json")

    assert agent1_card.status_code == 200
    assert agent2_card.status_code == 404
