"""Builds the FastAPI application that serves every agent."""

import html
from pathlib import Path

from a2a.server.request_handlers.default_request_handler_v2 import (
    DefaultRequestHandlerV2,
)
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse

from server.agent_card import build_agent_card
from server.executor import DeepAgentExecutor
from server.registry import AgentSpec, discover_agent_names, load_agent_spec
from server.schemas import AgentIndex, AgentRoute
from server.settings import AGENTS_DIR, get_public_base_url

AGENT_CARD_PATH = ".well-known/agent-card.json"
GUIDE_PATH = "/guide"
APP_TITLE = "A2A agents server"
EXAMPLE_REQUEST_BODY = (
    '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":'
    '{"message":{"messageId":"msg-1","role":"ROLE_USER",'
    '"parts":[{"text":"Oi"}]}}}'
)


def create_app(
    base_url: str | None = None,
    agents_dir: Path = AGENTS_DIR,
) -> FastAPI:
    """Build the application with one route group per agent folder.

    For each agent folder ``<name>``, the application serves:

    - ``POST /<name>``: JSON-RPC endpoint of the A2A protocol.
    - ``GET /<name>/.well-known/agent-card.json``: the agent card.

    The application also serves ``GET /`` (JSON index of the agents),
    ``GET /guide`` (human readable page with an example request for each
    agent) and the interactive API documentation of FastAPI at ``/docs``.

    Parameters
    ----------
    base_url : str | None
        Public base URL written into the agent cards. When None, it is read
        from the settings module.
    agents_dir : Path
        Folder that contains one sub-folder per agent.

    Returns
    -------
    FastAPI
        Application ready to be served by uvicorn or by Vercel.

    Example
    -------
    >>> app = create_app(base_url="http://127.0.0.1:8000")  # doctest: +SKIP
    """
    resolved_base_url = base_url or get_public_base_url()
    agent_names = discover_agent_names(agents_dir)
    specs = [load_agent_spec(name) for name in agent_names]
    app = FastAPI(title=APP_TITLE)
    app.include_router(_build_pages_router(specs, resolved_base_url))
    for spec in specs:
        _mount_agent(app, spec, resolved_base_url)
    return app


def _build_pages_router(
    specs: list[AgentSpec],
    base_url: str,
) -> APIRouter:
    """Create the router with the index and the guide page.

    Parameters
    ----------
    specs : list[AgentSpec]
        Specifications of the agents served by the application.
    base_url : str
        Public base URL used to build the links and example requests.

    Returns
    -------
    APIRouter
        Router with ``GET /`` and ``GET /guide``.
    """
    router = APIRouter()

    @router.get("/", response_model=AgentIndex, tags=["agents"])
    def list_agents() -> AgentIndex:
        """List the agents served by the application and their routes.

        Returns
        -------
        AgentIndex
            One entry per agent with its JSON-RPC and card paths.
        """
        return AgentIndex(
            agents=[
                AgentRoute(
                    name=spec.name,
                    rpc=f"/{spec.name}",
                    agent_card=f"/{spec.name}/{AGENT_CARD_PATH}",
                )
                for spec in specs
            ]
        )

    @router.get(GUIDE_PATH, response_class=HTMLResponse, tags=["agents"])
    def agents_guide() -> HTMLResponse:
        """Render the human readable guide with an example for each agent.

        Returns
        -------
        HTMLResponse
            Page describing the endpoints, skills and example requests.
        """
        return HTMLResponse(_render_guide_html(specs, base_url))

    return router


def _mount_agent(
    app: FastAPI,
    spec: AgentSpec,
    base_url: str,
) -> None:
    """Attach the A2A routes of one agent to the application.

    Parameters
    ----------
    app : FastAPI
        Application that receives the routes.
    spec : AgentSpec
        Specification of the agent to publish.
    base_url : str
        Public base URL written into the agent card.

    Returns
    -------
    None
    """
    rpc_path = f"/{spec.name}"
    card = build_agent_card(spec, f"{base_url}{rpc_path}")
    request_handler = DefaultRequestHandlerV2(
        agent_executor=DeepAgentExecutor(
            spec.build(base_url),
            trace_name=spec.name,
        ),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app.router.routes.extend(
        create_agent_card_routes(
            card,
            card_url=f"{rpc_path}/{AGENT_CARD_PATH}",
        )
    )
    app.router.routes.extend(
        create_jsonrpc_routes(request_handler, rpc_url=rpc_path)
    )


def _render_guide_html(
    specs: list[AgentSpec],
    base_url: str,
) -> str:
    """Render the guide page for all agents.

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
    >>> page = _render_guide_html([], "http://127.0.0.1:8000")
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
        "skills. The interactive API documentation is at "
        "<a href=\"/docs\">/docs</a>.</p>"
        f"{sections}"
        "</body></html>"
    )


def _render_agent_section(
    spec: AgentSpec,
    base_url: str,
) -> str:
    """Render the guide block of one agent.

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
