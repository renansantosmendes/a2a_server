"""Tests for the deep agent executor in server.executor."""

import asyncio
from types import SimpleNamespace
from typing import Any

from a2a.helpers.proto_helpers import new_message, new_text_part
from a2a.types.a2a_pb2 import (
    Role,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

from server.executor import (
    EMPTY_MESSAGE,
    FAILURE_MESSAGE,
    DeepAgentExecutor,
)


class FakeEventQueue:
    """Event queue that records every event instead of publishing it.

    Example
    -------
    >>> queue = FakeEventQueue()
    """

    def __init__(self) -> None:
        """Start with no recorded events.

        Returns
        -------
        None
        """
        self.events = []

    async def enqueue_event(self, event: Any) -> None:
        """Record an event.

        Parameters
        ----------
        event : Any
            Event produced by the executor.

        Returns
        -------
        None
        """
        self.events.append(event)


class FakeDeepAgent:
    """Deep agent stand-in that returns a fixed answer or raises.

    Parameters
    ----------
    answer : str
        Content of the last message returned by ``ainvoke``.
    should_fail : bool
        When True, ``ainvoke`` raises RuntimeError.

    Example
    -------
    >>> agent = FakeDeepAgent("ok", should_fail=False)
    """

    def __init__(
        self,
        answer: str,
        should_fail: bool,
    ) -> None:
        """Store the answer and the failure flag.

        Parameters
        ----------
        answer : str
            Content returned by ``ainvoke``.
        should_fail : bool
            When True, ``ainvoke`` raises an error.

        Returns
        -------
        None
        """
        self._answer = answer
        self._should_fail = should_fail
        self.received_messages = []

    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the fixed answer as the last message.

        Parameters
        ----------
        payload : dict[str, Any]
            Input with the ``messages`` list.

        Returns
        -------
        dict[str, Any]
            Dictionary whose ``messages`` list ends with the answer.

        Raises
        ------
        RuntimeError
            When the fake agent was built to fail.
        """
        self.received_messages = payload["messages"]
        if self._should_fail:
            raise RuntimeError("model unavailable")
        return {"messages": [SimpleNamespace(content=self._answer)]}


def make_context(text: str) -> SimpleNamespace:
    """Build a request context carrying one user text message.

    Parameters
    ----------
    text : str
        Text of the user message.

    Returns
    -------
    SimpleNamespace
        Object with the attributes the executor reads from the context.
    """
    message = new_message(
        parts=[new_text_part(text)],
        role=Role.ROLE_USER,
    )
    return SimpleNamespace(
        message=message,
        current_task=None,
        task_id="task-1",
        context_id="context-1",
    )


def run_execute(
    agent: FakeDeepAgent,
    text: str,
) -> FakeEventQueue:
    """Run the executor for one message and return the recorded events.

    Parameters
    ----------
    agent : FakeDeepAgent
        Deep agent used by the executor.
    text : str
        Text of the user message.

    Returns
    -------
    FakeEventQueue
        Queue holding the events published during the run.
    """
    executor = DeepAgentExecutor(agent)
    queue = FakeEventQueue()
    asyncio.run(executor.execute(make_context(text), queue))
    return queue


def artifact_texts(queue: FakeEventQueue) -> list[str]:
    """Collect the text of every artifact published in the queue.

    Parameters
    ----------
    queue : FakeEventQueue
        Queue with the recorded events.

    Returns
    -------
    list[str]
        Text of each artifact part, in publication order.
    """
    texts = []
    for event in queue.events:
        if isinstance(event, TaskArtifactUpdateEvent):
            for part in event.artifact.parts:
                texts.append(part.text)
    return texts


def status_messages(queue: FakeEventQueue) -> list[str]:
    """Collect the text of every status message in the queue.

    Parameters
    ----------
    queue : FakeEventQueue
        Queue with the recorded events.

    Returns
    -------
    list[str]
        Text of the message attached to each status update that has one.
    """
    texts = []
    for event in queue.events:
        if not isinstance(event, TaskStatusUpdateEvent):
            continue
        message_parts = event.status.message.parts
        if message_parts:
            texts.append(message_parts[0].text)
    return texts


def test_execute_publishes_the_agent_answer_as_artifact() -> None:
    """Send the question to the agent and publish its answer."""
    agent = FakeDeepAgent("A capital e Paris.", should_fail=False)

    queue = run_execute(agent, "Qual a capital da Franca?")

    assert artifact_texts(queue) == ["A capital e Paris."]
    assert agent.received_messages == [
        {"role": "user", "content": "Qual a capital da Franca?"}
    ]


def test_execute_rejects_blank_message_without_calling_agent() -> None:
    """Publish the empty-message failure and skip the agent."""
    agent = FakeDeepAgent("unused", should_fail=False)

    queue = run_execute(agent, "   ")

    assert status_messages(queue) == [EMPTY_MESSAGE]
    assert not artifact_texts(queue)
    assert agent.received_messages == []


def test_execute_reports_failure_when_agent_raises() -> None:
    """Publish the generic failure message when the agent raises."""
    agent = FakeDeepAgent("unused", should_fail=True)

    queue = run_execute(agent, "Pergunta")

    assert status_messages(queue) == [FAILURE_MESSAGE]
    assert not artifact_texts(queue)
