"""Shared helpers for the two-agent A2A demo."""

from pathlib import Path
from typing import Any

from a2a.client.client import ClientConfig
from a2a.client.client_factory import create_client
from a2a.helpers.proto_helpers import (
    get_message_text,
    new_message,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.request_handlers.default_request_handler_v2 import (
    DefaultRequestHandlerV2,
)
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
    SendMessageRequest,
)
from a2a.utils.constants import PROTOCOL_VERSION_1_0
import httpx
from dotenv import load_dotenv
from starlette.applications import Starlette

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
FAILURE_MESSAGE = "Nao foi possivel gerar a resposta no momento."
EMPTY_MESSAGE = "A mensagem recebida nao contem texto."
REQUEST_TIMEOUT_SECONDS = 180.0


def load_environment() -> None:
    """Load the variables from the project ``.env`` file.

    Returns
    -------
    None
    """
    load_dotenv(ENV_PATH)


def build_agent_card(
    name: str,
    description: str,
    rpc_url: str,
    skill_id: str,
    skill_name: str,
    skill_description: str,
) -> AgentCard:
    """Create the AgentCard that describes an agent to other agents.

    Parameters
    ----------
    name : str
        Human readable name of the agent.
    description : str
        Short description of what the agent does.
    rpc_url : str
        URL of the JSON-RPC endpoint where the agent receives requests.
    skill_id : str
        Identifier of the single skill the agent advertises.
    skill_name : str
        Display name of the skill.
    skill_description : str
        Explanation of what the skill answers.

    Returns
    -------
    AgentCard
        AgentCard with the JSON-RPC interface and one text skill.

    Example
    -------
    >>> card = build_agent_card(
    ...     "Agent 1", "Answers", "http://127.0.0.1:9101/",
    ...     "answer", "Answer", "Answers questions.",
    ... )
    """
    skill = AgentSkill(
        id=skill_id,
        name=skill_name,
        description=skill_description,
        tags=["demo"],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    )
    interface = AgentInterface(
        url=rpc_url,
        protocol_binding="JSONRPC",
        protocol_version=PROTOCOL_VERSION_1_0,
    )
    return AgentCard(
        name=name,
        description=description,
        version="0.1.0",
        supported_interfaces=[interface],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[skill],
    )


def create_app(
    agent_card: AgentCard,
    executor: AgentExecutor,
) -> Starlette:
    """Build the Starlette application that serves an A2A agent.

    Parameters
    ----------
    agent_card : AgentCard
        AgentCard served at the well-known path.
    executor : AgentExecutor
        Executor that runs the agent for each incoming request.

    Returns
    -------
    Starlette
        Application exposing the agent card and the JSON-RPC endpoint.

    Example
    -------
    >>> app = create_app(card, DeepAgentExecutor(agent))
    """
    request_handler = DefaultRequestHandlerV2(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = [
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(request_handler, rpc_url="/"),
    ]
    return Starlette(routes=routes)


class DeepAgentExecutor(AgentExecutor):
    """Run each A2A request through a deep agent and return its answer.

    Parameters
    ----------
    agent : Any
        Compiled deep agent that accepts a ``messages`` input.

    Example
    -------
    >>> executor = DeepAgentExecutor(agent)
    """

    def __init__(self, agent: Any) -> None:
        """Store the deep agent used to answer requests.

        Parameters
        ----------
        agent : Any
            Compiled deep agent that accepts a ``messages`` input.

        Returns
        -------
        None
        """
        self._agent = agent

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Answer the text of the incoming message with the deep agent.

        Parameters
        ----------
        context : RequestContext
            Request context holding the incoming message and task ids.
        event_queue : EventQueue
            Queue where task, status and artifact events are published.

        Returns
        -------
        None
        """
        question = get_message_text(context.message).strip()
        if context.current_task is None:
            await event_queue.enqueue_event(
                new_task_from_user_message(context.message)
            )
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.start_work()

        if not question:
            await updater.failed(
                updater.new_agent_message([new_text_part(EMPTY_MESSAGE)])
            )
            return

        try:
            answer = await self._run_agent(question)
        except Exception:
            await updater.failed(
                updater.new_agent_message([new_text_part(FAILURE_MESSAGE)])
            )
            return

        await updater.add_artifact(
            parts=[new_text_part(answer)],
            name="answer",
        )
        await updater.complete()

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel a task by publishing a canceled status update.

        Parameters
        ----------
        context : RequestContext
            Request context holding the task id to cancel.
        event_queue : EventQueue
            Queue where the cancellation status update is published.

        Returns
        -------
        None
        """
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()

    async def _run_agent(self, question: str) -> str:
        """Invoke the deep agent with a single user question.

        Parameters
        ----------
        question : str
            Text of the user question.

        Returns
        -------
        str
            Content of the last message produced by the agent.
        """
        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        return str(result["messages"][-1].content)


async def ask_agent(agent_url: str, question: str) -> str:
    """Send a question to another A2A agent and return its answer.

    Parameters
    ----------
    agent_url : str
        Base URL of the target agent, where its agent card is served.
    question : str
        Text sent to the target agent as a user message.

    Returns
    -------
    str
        Text of the artifacts in the task returned by the target agent.

    Example
    -------
    >>> answer = await ask_agent("http://127.0.0.1:9101", "Oi")
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http_client:
        client = await create_client(
            agent_url,
            client_config=ClientConfig(
                streaming=False,
                httpx_client=http_client,
            ),
        )
        request = SendMessageRequest(
            message=new_message(
                parts=[new_text_part(question)],
                role=Role.ROLE_USER,
            ),
        )
        responses = [
            response async for response in client.send_message(request)
        ]

    for response in responses:
        if response.HasField("task"):
            return "".join(
                part.text
                for artifact in response.task.artifacts
                for part in artifact.parts
            )
    return ""
