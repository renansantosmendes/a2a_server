"""Tests for the bearer token verification in server.identity."""

import asyncio

import httpx
import pytest

from server.identity import (
    Identity,
    IdentityServiceError,
    IdentityVerifier,
    TokenRejectedError,
    read_bearer_token,
)

AUTH_BASE = "https://auth.test"


class ScriptedTransport:
    """Answer verification requests with a scripted response.

    Parameters
    ----------
    responder : Callable[[httpx.Request], httpx.Response]
        Function that builds the response of each request.

    Example
    -------
    >>> transport = ScriptedTransport(lambda request: httpx.Response(200))
    """

    def __init__(self, responder) -> None:
        """Store the responder and start counting requests.

        Parameters
        ----------
        responder : Callable[[httpx.Request], httpx.Response]
            Function that builds the response of each request.

        Returns
        -------
        None
        """
        self._responder = responder
        self.requests = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Record the request and return the scripted response.

        Parameters
        ----------
        request : httpx.Request
            Request sent by the verifier.

        Returns
        -------
        httpx.Response
            Scripted response.
        """
        self.requests.append(request)
        return self._responder(request)

    def transport(self) -> httpx.MockTransport:
        """Build the mock transport used by the verifier.

        Returns
        -------
        httpx.MockTransport
            Transport that calls ``handler``.
        """
        return httpx.MockTransport(self.handler)


def ok_response(request: httpx.Request) -> httpx.Response:
    """Helper ok response."""
    return httpx.Response(
        200,
        json={"registration_number": "12345", "role": "student"},
    )


class FakeClock:
    """Helper FakeClock."""
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def verify(verifier: IdentityVerifier, token: str) -> Identity:
    """Helper verify."""
    return asyncio.run(verifier.verify(token))


def test_valid_token_returns_its_identity_and_calls_the_service():
    """Check that valid token returns its identity and calls the service."""
    transport = ScriptedTransport(ok_response)
    verifier = IdentityVerifier(AUTH_BASE, transport=transport.transport())

    identity = verify(verifier, "tok-1")

    assert identity == Identity(registration_number="12345", role="student")
    request = transport.requests[0]
    assert request.url.path == "/api/token/verify"
    assert request.headers["authorization"] == "Bearer tok-1"


def test_rejected_token_raises_with_the_service_message():
    """Check that rejected token raises with the service message."""
    transport = ScriptedTransport(
        lambda request: httpx.Response(401, json={"detail": "Token expired."})
    )
    verifier = IdentityVerifier(AUTH_BASE, transport=transport.transport())

    with pytest.raises(TokenRejectedError) as error:
        verify(verifier, "old")

    assert error.value.status_code == 401
    assert error.value.detail == "Token expired."


def test_inactive_account_is_reported_as_403():
    """Check that inactive account is reported as 403."""
    transport = ScriptedTransport(lambda request: httpx.Response(403, json={}))
    verifier = IdentityVerifier(AUTH_BASE, transport=transport.transport())

    with pytest.raises(TokenRejectedError) as error:
        verify(verifier, "tok")

    assert error.value.status_code == 403


def test_unexpected_status_raises_service_error():
    """Check that unexpected status raises service error."""
    transport = ScriptedTransport(lambda request: httpx.Response(500))
    verifier = IdentityVerifier(AUTH_BASE, transport=transport.transport())

    with pytest.raises(IdentityServiceError):
        verify(verifier, "tok")


def test_connection_failure_raises_service_error():
    """Check that connection failure raises service error."""
    def unreachable(request):
        raise httpx.ConnectError("down", request=request)

    transport = httpx.MockTransport(unreachable)
    verifier = IdentityVerifier(AUTH_BASE, transport=transport)

    with pytest.raises(IdentityServiceError):
        verify(verifier, "tok")


def test_accepted_tokens_are_cached_until_the_ttl_expires():
    """Check that accepted tokens are cached until the ttl expires."""
    transport = ScriptedTransport(ok_response)
    clock = FakeClock(now=100.0)
    verifier = IdentityVerifier(
        AUTH_BASE,
        transport=transport.transport(),
        clock=clock,
    )

    verify(verifier, "tok")
    verify(verifier, "tok")
    assert len(transport.requests) == 1

    clock.now = 100.0 + 61.0
    verify(verifier, "tok")
    assert len(transport.requests) == 2


def test_rejections_are_never_cached():
    """Check that rejections are never cached."""
    transport = ScriptedTransport(lambda request: httpx.Response(401, json={}))
    verifier = IdentityVerifier(AUTH_BASE, transport=transport.transport())

    for _ in range(2):
        with pytest.raises(TokenRejectedError):
            verify(verifier, "bad")

    assert len(transport.requests) == 2


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer abc", "abc"),
        ("bearer   abc  ", "abc"),
        (None, None),
        ("", None),
        ("Basic abc", None),
        ("Bearer ", None),
    ],
)
def test_read_bearer_token(header, expected):
    """Check that read bearer token."""
    assert read_bearer_token(header) == expected
