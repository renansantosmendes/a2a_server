"""Runtime settings shared by the local server and the Vercel deployment."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"
ENV_PATH = PROJECT_ROOT / ".env"
LOCAL_BASE_URL = "http://127.0.0.1:8000"


def get_public_base_url() -> str:
    """Return the public base URL used in the agent cards.

    The value is taken from ``PUBLIC_BASE_URL`` when set. Otherwise, on
    Vercel, it is built from ``VERCEL_URL``. Locally, it falls back to
    ``http://127.0.0.1:8000``. The ``.env`` file is loaded first when it
    exists.

    Returns
    -------
    str
        Base URL without a trailing slash, for example
        ``https://my-app.vercel.app``.

    Example
    -------
    >>> get_public_base_url()
    'http://127.0.0.1:8000'
    """
    load_dotenv(ENV_PATH)
    explicit_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if explicit_url:
        return explicit_url
    vercel_host = os.getenv("VERCEL_URL", "").strip().rstrip("/")
    if vercel_host:
        return f"https://{vercel_host}"
    return LOCAL_BASE_URL
