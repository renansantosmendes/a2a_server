"""Verification of the bearer tokens issued by pgl_auth_server."""

import hashlib
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import httpx

from server.settings import get_auth_service_url

VERIFY_PATH = "/api/token/verify"
CACHE_TTL_SECONDS = 60.0
REQUEST_TIMEOUT_SECONDS = 10.0
BEARER_PREFIX = "bearer "


@dataclass(frozen=True)
class Identity:
    """Owner of a verified bearer token.

    Attributes
    ----------
    registration_number : str
        Registration number of the owner.
    role : str
        ``student`` or ``professor``.
    """

    registration_number: str
    role: str


class TokenRejectedError(Exception):
    """The token is missing, invalid, revoked or inactive.

    Attributes
    ----------
    status_code : int
        HTTP status returned by the authentication service (401 or 403).
    detail : str
        Message to show to the caller.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        """Store the status code and the message.

        Parameters
        ----------
        status_code : int
            HTTP status returned by the authentication service.
        detail : str
            Message to show to the caller.

        Returns
        -------
        None
        """
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class IdentityServiceError(Exception):
    """The authentication service could not be reached or failed."""


def read_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract the token from an Authorization header.

    Parameters
    ----------
    authorization : str | None
        Value of the ``Authorization`` header.

    Returns
    -------
    str | None
        Token without the ``Bearer`` prefix, or None when the header is
        missing or does not use the bearer scheme.

    Example
    -------
    >>> read_bearer_token("Bearer abc")
    'abc'
    """
    if not authorization:
        return None
    if not authorization.lower().startswith(BEARER_PREFIX):
        return None
    token = authorization[len(BEARER_PREFIX):].strip()
    return token or None


class IdentityVerifier:
    """Check bearer tokens with pgl_auth_server and cache the answers.

    A verified token is remembered for ``CACHE_TTL_SECONDS``, so a token
    that is revoked is still accepted for up to that long. Rejections are
    never cached. Tokens are stored only as SHA-256 digests.

    Parameters
    ----------
    auth_base_url : str | None
        Base URL of pgl_auth_server. Defaults to the value read by
        ``get_auth_service_url``.
    transport : httpx.AsyncBaseTransport | None
        Transport used by the HTTP client, replaced in tests.
    clock : Callable[[], float] | None
        Monotonic clock used for the cache expiration, replaced in tests.

    Example
    -------
    >>> verifier = IdentityVerifier("https://pgl-auth-server.vercel.app")
    """

    def __init__(
        self,
        auth_base_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        """Store the service URL and the cache.

        Parameters
        ----------
        auth_base_url : str | None
            Base URL of pgl_auth_server.
        transport : httpx.AsyncBaseTransport | None
            Transport used by the HTTP client.
        clock : Callable[[], float] | None
            Monotonic clock used for the cache expiration.

        Returns
        -------
        None
        """
        self._base_url = (auth_base_url or get_auth_service_url()).rstrip("/")
        self._transport = transport
        self._clock = clock or time.monotonic
        self._cache: Dict[str, Tuple[Identity, float]] = {}

    async def verify(self, token: str) -> Identity:
        """Return the owner of a token, asking the service when needed.

        Parameters
        ----------
        token : str
            Bearer token sent by the caller.

        Returns
        -------
        Identity
            Registration number and role of the token owner.

        Raises
        ------
        TokenRejectedError
            If the service rejects the token.
        IdentityServiceError
            If the service cannot be reached or answers unexpectedly.
        """
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = self._clock()
        cached = self._cache.get(digest)
        if cached is not None and cached[1] > now:
            return cached[0]

        identity = await self._request_identity(token)
        self._forget_expired(now)
        self._cache[digest] = (identity, now + CACHE_TTL_SECONDS)
        return identity

    async def _request_identity(self, token: str) -> Identity:
        """Call the verification endpoint of pgl_auth_server.

        Parameters
        ----------
        token : str
            Bearer token to check.

        Returns
        -------
        Identity
            Owner of the token as reported by the service.

        Raises
        ------
        TokenRejectedError
            For status 401 or 403.
        IdentityServiceError
            For connection errors and any other status.
        """
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    f"{self._base_url}{VERIFY_PATH}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as error:
            raise IdentityServiceError(
                "Authentication service unreachable."
            ) from error

        if response.status_code in (401, 403):
            raise TokenRejectedError(
                response.status_code, _detail_of(response)
            )
        if response.status_code != 200:
            raise IdentityServiceError(
                f"Authentication service answered {response.status_code}."
            )
        body = response.json()
        return Identity(
            registration_number=body["registration_number"],
            role=body["role"],
        )

    def _forget_expired(self, now: float) -> None:
        """Drop the cached answers whose time has passed.

        Parameters
        ----------
        now : float
            Current reading of the clock.

        Returns
        -------
        None
        """
        expired = [
            key
            for key, (_, expires_at) in self._cache.items()
            if expires_at <= now
        ]
        for key in expired:
            del self._cache[key]


def _detail_of(response: httpx.Response) -> str:
    """Read the message of an error response from the authentication service.

    Parameters
    ----------
    response : httpx.Response
        Error response.

    Returns
    -------
    str
        Message sent by the service, or a generic one.
    """
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    return detail if isinstance(detail, str) else "Token inválido."
