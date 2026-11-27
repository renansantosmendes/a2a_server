"""Builds the Starlette application that serves every agent."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from a2a.server.request_handlers.default_request_handler_v2 import (
    DefaultRequestHandlerV2,
)
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from server.agent_card import build_agent_card
from server.executor import DeepAgentExecutor
from server.registry import discover_agent_names, load_agent_spec
from server.settings import AGENTS_DIR, get_public_base_url

AGENT_CARD_PATH = ".well-known/agent-card.json"


def create_app(
    base_url: str | None = None,
    agents_dir: Path = AGENTS_DIR,
) -> Starlette:
    """Build the application with one route group per agent folder.

    For each agent folder ``<name>``, the application serves:

    - ``POST /<name>``: JSON-RPC endpoint of the A2A protocol.
    - ``GET /<name>/.well-known/agent-card.json``: the agent card.

    The index ``GET /`` lists the available agents.

    Parameters
    ----------
    base_url : str | None
        Public base URL written into the agent cards. When None, it is read
        from the settings module.
    agents_dir : Path
        Folder that contains one sub-folder per agent.

    Returns
    -------
    Starlette
        Application ready to be served by uvicorn or by Vercel.

    Example
    -------
    >>> app = create_app(base_url="http://127.0.0.1:8000")
    """
    resolved_base_url = base_url or get_public_base_url()
    agent_names = discover_agent_names(agents_dir)
    routes = [Route("/", endpoint=_build_index(agent_names))]

    for name in agent_names:
        spec = load_agent_spec(name)
        rpc_path = f"/{name}"
        card = build_agent_card(spec, f"{resolved_base_url}{rpc_path}")
        request_handler = DefaultRequestHandlerV2(
            agent_executor=DeepAgentExecutor(spec.build(resolved_base_url)),
            task_store=InMemoryTaskStore(),
            agent_card=card,
        )
        routes.extend(
            create_agent_card_routes(
                card,
                card_url=f"{rpc_path}/{AGENT_CARD_PATH}",
            )
        )
        routes.extend(
            create_jsonrpc_routes(request_handler, rpc_url=rpc_path)
        )

    return Starlette(routes=routes)


def _build_index(
    agent_names: list[str],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Create the endpoint that lists the available agents.

    Parameters
    ----------
    agent_names : list[str]
        Route names of the agents served by the application.

    Returns
    -------
    Callable[[Request], Awaitable[JSONResponse]]
        Starlette endpoint returning a JSON document with the agent routes.
    """

    async def index(request: Request) -> JSONResponse:
        """Return the list of agent routes as JSON.

        Parameters
        ----------
        request : Request
            Incoming HTTP request. Not used.

        Returns
        -------
        JSONResponse
            Document with the agent names and their card paths.
        """
        return JSONResponse(
            {
                "agents": [
                    {
                        "name": name,
                        "rpc": f"/{name}",
                        "agent_card": f"/{name}/{AGENT_CARD_PATH}",
                    }
                    for name in agent_names
                ]
            }
        )

    return index
