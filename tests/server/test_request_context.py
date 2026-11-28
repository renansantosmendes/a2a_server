"""Tests for the request-scoped bearer token in server.request_context."""

from server.request_context import BEARER_TOKEN_VAR, forwarded_headers


def test_no_headers_are_forwarded_without_a_token():
    """Check that no headers are forwarded without a token."""
    assert not forwarded_headers()


def test_the_current_token_is_forwarded_as_bearer_header():
    """Check that the current token is forwarded as bearer header."""
    token_reference = BEARER_TOKEN_VAR.set("tok-caller")
    try:
        assert forwarded_headers() == {"Authorization": "Bearer tok-caller"}
    finally:
        BEARER_TOKEN_VAR.reset(token_reference)


def test_the_token_is_visible_only_inside_its_context():
    """Check that the token is visible only inside its context."""
    token_reference = BEARER_TOKEN_VAR.set("tok-temp")
    BEARER_TOKEN_VAR.reset(token_reference)

    assert not forwarded_headers()
