"""Shared fixtures for the test suite."""

import pytest

from server import settings


@pytest.fixture(autouse=True)
def isolate_tests_from_local_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the tests away from the real Langfuse keys and the ``.env`` file.

    Every test starts without the Langfuse keys, and the ``.env`` file is
    not read, so no test sends traces or depends on local secrets.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to change the environment for one test.

    Returns
    -------
    None
    """
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(settings, "load_dotenv", lambda path: None)
