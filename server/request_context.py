"""Values of the current request that agent code can read.

The bearer token of a request is stored in a context variable by the
authorization middleware. Code that runs in the same asyncio task, such as
the tool that calls another agent, reads it from here, so the caller's
identity is forwarded without changing the agent signatures.
"""

from contextvars import ContextVar
from typing import Dict, Optional

BEARER_TOKEN_VAR: ContextVar[Optional[str]] = ContextVar(
    "bearer_token",
    default=None,
)


def forwarded_headers() -> Dict[str, str]:
    """Build the headers that carry the caller's token to another agent.

    Returns
    -------
    dict[str, str]
        ``Authorization`` header when the current request has a token,
        otherwise an empty dictionary.

    Example
    -------
    >>> forwarded_headers()
    {}
    """
    token = BEARER_TOKEN_VAR.get()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
