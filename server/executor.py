"""AgentExecutor that runs each A2A request through a deep agent."""

from typing import Any

from a2a.helpers.proto_helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater

EMPTY_MESSAGE = "A mensagem recebida nao contem texto."
FAILURE_MESSAGE = "Nao foi possivel gerar a resposta no momento."


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
