"""Builds the Starlette application that serves every agent."""

import html
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
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from server.agent_card import build_agent_card
from server.executor import DeepAgentExecutor
from server.registry import AgentSpec, discover_agent_names, load_agent_spec
from server.settings import AGENTS_DIR, get_public_base_url

AGENT_CARD_PATH = ".well-known/agent-card.json"
EXAMPLE_REQUEST_BODY = (
    '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":'
    '{"message":{"messageId":"msg-1","role":"ROLE_USER",'
    '"parts":[{"text":"Oi"}]}}}'
)


def create_app(
    base_url: str | None = None,
    agents_dir: Path = AGENTS_DIR,
) -> Starlette:
    """Build the application with one route group per agent folder.

    For each agent folder ``<name>``, the application serves:

    - ``POST /<name>``: JSON-RPC endpoint of the A2A protocol.
    - ``GET /<name>/.well-known/agent-card.json``: the agent card.

    The index ``GET /`` lists the available agents as JSON, and
    ``GET /docs`` shows a human readable page with the endpoints and an
    example request for each agent.

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
    specs = []

    for name in agent_names:
        spec = load_agent_spec(name)
        specs.append(spec)
        rpc_path = f"/{name}"
        card = build_agent_card(spec, f"{resolved_base_url}{rpc_path}")
        request_handler = DefaultRequestHandlerV2(
            agent_executor=DeepAgentExecutor(
                spec.build(resolved_base_url),
                trace_name=spec.name,
            ),
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

    routes.append(
        Route("/docs", endpoint=_build_docs_page(specs, resolved_base_url))
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


def _build_docs_page(
    specs: list[AgentSpec],
    base_url: str,
) -> Callable[[Request], Awaitable[HTMLResponse]]:
    """Create the endpoint that renders the documentation page.

    Parameters
    ----------
    specs : list[AgentSpec]
        Specifications of the agents served by the application.
    base_url : str
        Public base URL used to build the links and example requests.

    Returns
    -------
    Callable[[Request], Awaitable[HTMLResponse]]
        Starlette endpoint returning the HTML documentation page.
    """

    async def docs(request: Request) -> HTMLResponse:
        """Return the HTML documentation page.

        Parameters
        ----------
        request : Request
            Incoming HTTP request. Not used.

        Returns
        -------
        HTMLResponse
            Page describing every agent endpoint.
        """
        return HTMLResponse(_render_docs_html(specs, base_url))

    return docs


def _render_docs_html(
    specs: list[AgentSpec],
    base_url: str,
) -> str:
    """Render the documentation page for all agents.

    Parameters
    ----------
    specs : list[AgentSpec]
        Specifications of the agents served by the application.
    base_url : str
        Public base URL used to build the links and example requests.

    Returns
    -------
    str
        Complete HTML document.

    Example
    -------
    >>> page = _render_docs_html([], "http://127.0.0.1:8000")
    """
    sections = "".join(_render_agent_section(spec, base_url) for spec in specs)
    return (
        "<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        "<title>A2A agents</title><style>"
        "body{font-family:system-ui,sans-serif;max-width:900px;"
        "margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "pre{background:#f4f4f4;padding:.75rem;overflow-x:auto}"
        "code{font-family:Consolas,monospace}"
        "section{border-top:1px solid #ddd;padding-top:1rem;margin-top:2rem}"
        "</style></head><body>"
        "<h1>A2A agents</h1>"
        "<p>Each agent is served over the A2A protocol (JSON-RPC 2.0). "
        "Send a <code>POST</code> with the <code>SendMessage</code> method "
        "to the agent endpoint, and read the agent card to discover its "
        "skills.</p>"
        f"{sections}"
        "</body></html>"
    )


def _render_agent_section(
    spec: AgentSpec,
    base_url: str,
) -> str:
    """Render the documentation block of one agent.

    Parameters
    ----------
    spec : AgentSpec
        Specification of the agent to document.
    base_url : str
        Public base URL used to build the links and example requests.

    Returns
    -------
    str
        HTML section with the endpoints, the skill and an example request.
    """
    rpc_url = f"{base_url}/{spec.name}"
    card_url = f"{rpc_url}/{AGENT_CARD_PATH}"
    example = (
        f"curl -X POST {rpc_url} \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -H \"A2A-Version: 1.0\" \\\n"
        f"  -d '{EXAMPLE_REQUEST_BODY}'"
    )
    return (
        f"<section><h2>{html.escape(spec.display_name)} "
        f"<code>/{html.escape(spec.name)}</code></h2>"
        f"<p>{html.escape(spec.description)}</p>"
        f"<p><strong>Skill:</strong> {html.escape(spec.skill_name)} - "
        f"{html.escape(spec.skill_description)}</p>"
        f"<p><strong>Agent card:</strong> <a href=\"{html.escape(card_url)}\">"
        f"{html.escape(card_url)}</a></p>"
        f"<p><strong>JSON-RPC endpoint:</strong> "
        f"<code>POST {html.escape(rpc_url)}</code></p>"
        f"<p><strong>Example:</strong></p>"
        f"<pre><code>{html.escape(example)}</code></pre></section>"
    )
