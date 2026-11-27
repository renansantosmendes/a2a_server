"""Langfuse tracing of the LLM calls made by the agents."""

import logging
import os
from typing import Any

from langfuse import get_client
from langfuse.langchain import CallbackHandler

from server.settings import load_environment

PUBLIC_KEY_VARIABLE = "LANGFUSE_PUBLIC_KEY"
SECRET_KEY_VARIABLE = "LANGFUSE_SECRET_KEY"
logger = logging.getLogger(__name__)


def is_tracing_enabled() -> bool:
    """Check whether the Langfuse keys are configured.

    The ``.env`` file is loaded first. Tracing is enabled only when both
    ``LANGFUSE_PUBLIC_KEY`` and ``LANGFUSE_SECRET_KEY`` are set.

    Returns
    -------
    bool
        True when both keys are available.

    Example
    -------
    >>> is_tracing_enabled()
    True
    """
    load_environment()
    return bool(
        os.getenv(PUBLIC_KEY_VARIABLE) and os.getenv(SECRET_KEY_VARIABLE)
    )


def build_tracing_callbacks() -> list[Any]:
    """Create the callbacks that send LLM calls to Langfuse.

    Returns
    -------
    list[Any]
        A list with one Langfuse LangChain callback handler when tracing is
        enabled, or an empty list otherwise.

    Example
    -------
    >>> callbacks = build_tracing_callbacks()
    """
    if not is_tracing_enabled():
        return []
    return [CallbackHandler()]


def flush_traces() -> None:
    """Send the pending traces to Langfuse.

    Serverless runtimes can stop the process right after the response, so
    the traces are flushed before the answer is returned. Failures are
    logged and never break the agent answer.

    Returns
    -------
    None

    Example
    -------
    >>> flush_traces()
    """
    if not is_tracing_enabled():
        return
    try:
        get_client().flush()
    except Exception:
        logger.exception("Could not flush traces to Langfuse.")
