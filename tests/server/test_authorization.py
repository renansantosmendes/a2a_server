"""Tests for the authorization of agent calls in the FastAPI application."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server import app_factory
from server.app_factory import create_app
from server.identity import Identity, IdentityServiceError, TokenRejectedError

BASE_URL = "https://example.test"
AGENTS_SOURCE = Path(__file__).resolve().parents[2] / "agents"
JSON_RPC_BODY = (
    '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":'
    '{"message":{"messageId":"m-1","role":"ROLE_USER",'
    '"parts":[{"text":"Oi"}]}}}'
)


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


class FakeVerifier:
    """Verifier that answers from a table of tokens.

    Parameters
    ----------
    answers : dict[str, Identity | Exception]
        Answer of each known token. Exceptions are raised.

    Example
    -------
    >>> verifier = FakeVerifier({"tok": Identity("1", "student")})
    """

    def __init__(self, answers) -> None:
        """Store the answers table.

        Parameters
        ----------
        answers : dict[str, Identity | Exception]
            Answer of each known token.

        Returns
        -------
        None
        """
        self._answers = answers

    async def verify(self, token: str) -> Identity:
        """Return the scripted answer of a token.

        Parameters
        ----------
        token : str
            Token sent by the caller.

        Returns
        -------
        Identity
            Owner of the token.

        Raises
        ------
        Exception
            The scripted error of the token, or TokenRejectedError for
            unknown tokens.
        """
        answer = self._answers.get(token)
        if answer is None:
            raise TokenRejectedError(401, "Invalid token.")
        if isinstance(answer, Exception):
            raise answer
        return answer


def restricted_client(
    monkeypatch: pytest.MonkeyPatch,
    roles: tuple,
) -> TestClient:
    """Build a client whose agent1 accepts only the given roles.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to replace the spec loader for one test.
    roles : tuple[str, ...]
        Roles allowed to call agent1.

    Returns
    -------
    TestClient
        Client of the application with the restricted agent.
    """
    original_loader = app_factory.load_agent_spec

    def restricted_loader(name: str):
        spec = original_loader(name)
        return replace(spec, allowed_roles=roles) if name == "agent1" else spec

    monkeypatch.setattr(app_factory, "load_agent_spec", restricted_loader)
    return client_with(
        {
            "tok": Identity("12345", "student"),
            "prof": Identity("prof-1", "professor"),
        }
    )


def client_with(answers, agents_dir: Path = AGENTS_SOURCE) -> TestClient:
    """Helper client with."""
    app = create_app(
        base_url=BASE_URL,
        agents_dir=agents_dir,
        identity_verifier=FakeVerifier(answers),
    )
    return TestClient(app)


def test_agent_call_without_token_is_rejected():
    """Check that agent call without token is rejected."""
    response = client_with({}).post("/agent1", content=JSON_RPC_BODY)

    assert response.status_code == 401


def test_agent_call_with_unknown_token_is_rejected():
    """Check that agent call with unknown token is rejected."""
    response = client_with({}).post(
        "/agent1",
        content=JSON_RPC_BODY,
        headers={"Authorization": "Bearer unknown"},
    )

    assert response.status_code == 401


def test_agent_call_reports_an_unavailable_auth_service():
    """Check that agent call reports an unavailable auth service."""
    client = client_with({"tok": IdentityServiceError("down")})

    response = client.post(
        "/agent1",
        content=JSON_RPC_BODY,
        headers={"Authorization": "Bearer tok"},
    )

    assert response.status_code == 503


def test_agent_call_with_an_allowed_role_passes_the_gate():
    """Check that agent call with an allowed role passes the gate."""
    client = client_with({"tok": Identity("12345", "student")})

    response = client.post(
        "/agent1",
        content="not json",
        headers={"Authorization": "Bearer tok"},
    )

    assert response.status_code not in (401, 403, 503)


def test_agent_restricted_to_professors_rejects_students(monkeypatch):
    """Check that agent restricted to professors rejects students."""
    client = restricted_client(monkeypatch, ("professor",))

    response = client.post(
        "/agent1",
        content=JSON_RPC_BODY,
        headers={"Authorization": "Bearer tok"},
    )

    assert response.status_code == 403


def test_agent_restricted_to_professors_accepts_professors(monkeypatch):
    """Check that agent restricted to professors accepts professors."""
    client = restricted_client(monkeypatch, ("professor",))

    response = client.post(
        "/agent1",
        content="not json",
        headers={"Authorization": "Bearer prof"},
    )

    assert response.status_code not in (401, 403)


def test_agent_card_stays_public_and_declares_the_bearer_scheme():
    """Check that agent card stays public and declares the bearer scheme."""
    client = client_with({})

    response = client.get("/agent1/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    scheme = card["securitySchemes"]["bearerAuth"]["httpAuthSecurityScheme"]
    assert scheme["scheme"] == "bearer"
    assert "bearerAuth" in card["securityRequirements"][0]["schemes"]


def test_index_stays_public():
    """Check that index stays public."""
    assert client_with({}).get("/").status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/agent1/.well-known/agent-card.json", "/guide"],
)
def test_get_routes_do_not_require_a_token(path):
    """Check that get routes do not require a token."""
    assert client_with({}).get(path).status_code == 200
