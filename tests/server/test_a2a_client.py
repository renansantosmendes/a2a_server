"""Tests for the A2A client helper in server.a2a_client."""

import asyncio
from unittest.mock import AsyncMock, patch

from a2a.types.a2a_pb2 import Artifact, Part, StreamResponse, Task

from server.a2a_client import ask_agent


class FakeClient:
    """Minimal A2A client that yields a fixed list of responses.

    Parameters
    ----------
    responses : list[StreamResponse]
        Responses returned by ``send_message``.

    Example
    -------
    >>> client = FakeClient([])
    """

    def __init__(
        self,
        responses: list[StreamResponse],
    ) -> None:
        """Store the responses returned by send_message.

        Parameters
        ----------
        responses : list[StreamResponse]
            Responses yielded by ``send_message``.

        Returns
        -------
        None
        """
        self._responses = responses
        self.close = AsyncMock()

    async def send_message(self, request: object):
        """Yield the stored responses.

        Parameters
        ----------
        request : object
            Request received from the caller. Not checked.

        Yields
        ------
        StreamResponse
            Each stored response, in order.
        """
        for response in self._responses:
            yield response


def make_task_response(answer_text: str) -> StreamResponse:
    """Build a response that carries one task with a text artifact.

    Parameters
    ----------
    answer_text : str
        Text stored in the artifact part.

    Returns
    -------
    StreamResponse
        Response whose task has one artifact with the given text.
    """
    artifact = Artifact(parts=[Part(text=answer_text)])
    return StreamResponse(task=Task(artifacts=[artifact]))


def test_ask_agent_returns_artifact_text() -> None:
    """Join the text of the artifacts of the returned task."""
    fake_client = FakeClient([make_task_response("Paris")])

    with patch(
        "server.a2a_client.create_client",
        AsyncMock(return_value=fake_client),
    ):
        answer = _run_ask("http://agent.test/agent1", "Capital?")

    assert answer == "Paris"
    fake_client.close.assert_awaited_once()


def test_ask_agent_returns_empty_text_without_task() -> None:
    """Return an empty string when the agent returns no task."""
    fake_client = FakeClient([StreamResponse()])

    with patch(
        "server.a2a_client.create_client",
        AsyncMock(return_value=fake_client),
    ):
        answer = _run_ask("http://agent.test/agent1", "Oi")

    assert answer == ""


def _run_ask(
    agent_url: str,
    question: str,
) -> str:
    """Run the async ask_agent helper from a synchronous test.

    Parameters
    ----------
    agent_url : str
        URL passed to ask_agent.
    question : str
        Question passed to ask_agent.

    Returns
    -------
    str
        Answer returned by ask_agent.
    """
    return asyncio.run(ask_agent(agent_url, question))
