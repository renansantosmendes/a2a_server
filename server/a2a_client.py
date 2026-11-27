"""A2A client used by agents to ask questions to other agents."""

import httpx
from a2a.client.client import ClientConfig
from a2a.client.client_factory import create_client
from a2a.helpers.proto_helpers import new_message, new_text_part
from a2a.types.a2a_pb2 import Role, SendMessageRequest

REQUEST_TIMEOUT_SECONDS = 180.0


async def ask_agent(
    agent_url: str,
    question: str,
) -> str:
    """Send a question to another A2A agent and return its answer.

    Parameters
    ----------
    agent_url : str
        URL of the target agent, where its agent card is served.
    question : str
        Text sent to the target agent as a user message.

    Returns
    -------
    str
        Text of the artifacts of the task returned by the target agent, or
        an empty string when no task is returned.

    Example
    -------
    >>> answer = await ask_agent("http://127.0.0.1:8000/agent1", "Oi")
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
        client = await create_client(
            agent_url,
            client_config=ClientConfig(streaming=False, httpx_client=http),
        )
        request = SendMessageRequest(
            message=new_message(
                parts=[new_text_part(question)],
                role=Role.ROLE_USER,
            ),
        )
        try:
            responses = [
                response async for response in client.send_message(request)
            ]
        finally:
            await client.close()
    for response in responses:
        if response.HasField("task"):
            return "".join(
                part.text
                for artifact in response.task.artifacts
                for part in artifact.parts
            )
    return ""
