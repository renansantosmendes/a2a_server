"""Tests for the public base URL resolution in server.settings."""

import pytest

from server import settings


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove URL variables and skip reading the real .env file.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to change the environment for one test.

    Returns
    -------
    None
    """
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("VERCEL_URL", raising=False)
    monkeypatch.setattr(settings, "load_dotenv", lambda path: None)


def test_public_base_url_defaults_to_local_address() -> None:
    """Fall back to the local address when no variable is set."""
    assert settings.get_public_base_url() == settings.LOCAL_BASE_URL


def test_public_base_url_uses_vercel_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build an https URL from VERCEL_URL when it is set."""
    monkeypatch.setenv("VERCEL_URL", "my-app.vercel.app")

    assert settings.get_public_base_url() == "https://my-app.vercel.app"


def test_public_base_url_prefers_explicit_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use PUBLIC_BASE_URL first and remove its trailing slash."""
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://custom.example/")
    monkeypatch.setenv("VERCEL_URL", "my-app.vercel.app")

    assert settings.get_public_base_url() == "https://custom.example"
