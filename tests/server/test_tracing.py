"""Tests for the Langfuse tracing helpers in server.tracing."""

from unittest.mock import MagicMock

import pytest

from server import tracing


def test_tracing_is_disabled_without_keys() -> None:
    """Report tracing as disabled when no Langfuse key is set."""
    assert tracing.is_tracing_enabled() is False


def test_tracing_is_disabled_with_only_the_public_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require both the public and the secret key to enable tracing."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")

    assert tracing.is_tracing_enabled() is False


def test_build_callbacks_is_empty_when_disabled() -> None:
    """Return no callbacks, so the agent runs without tracing."""
    assert not tracing.build_tracing_callbacks()


def test_build_callbacks_creates_langfuse_handler_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create one Langfuse callback handler when both keys are set."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    handler_class = MagicMock(return_value="handler")
    monkeypatch.setattr(tracing, "CallbackHandler", handler_class)

    callbacks = tracing.build_tracing_callbacks()

    assert callbacks == ["handler"]
    handler_class.assert_called_once_with()


def test_flush_does_nothing_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip the Langfuse client entirely when tracing is disabled."""
    get_client_mock = MagicMock()
    monkeypatch.setattr(tracing, "get_client", get_client_mock)

    tracing.flush_traces()

    get_client_mock.assert_not_called()


def test_flush_sends_pending_traces_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flush the Langfuse client when tracing is enabled."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    get_client_mock = MagicMock()
    monkeypatch.setattr(tracing, "get_client", get_client_mock)

    tracing.flush_traces()

    get_client_mock.return_value.flush.assert_called_once_with()


def test_flush_error_does_not_break_the_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Log and ignore a failing flush, so the agent answer still returns."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    get_client_mock = MagicMock(side_effect=RuntimeError("offline"))
    monkeypatch.setattr(tracing, "get_client", get_client_mock)

    tracing.flush_traces()
