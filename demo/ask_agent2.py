"""Send a question to agent 2 over A2A and print the answer."""

import asyncio
import sys

from demo.agent2_server import AGENT2_URL
from demo.common import ask_agent, load_environment


def main() -> None:
    """Read the question from the command line and print agent 2's answer.

    The question is taken from the command-line arguments. When none are
    given, it is requested interactively.

    Returns
    -------
    None

    Example
    -------
    python -m demo.ask_agent2 "Quem descobriu o Brasil?"
    """
    load_environment()
    sys.stdout.reconfigure(encoding="utf-8")
    question = " ".join(sys.argv[1:]).strip() or input("Pergunta: ")
    answer = asyncio.run(ask_agent(AGENT2_URL, question))
    print(answer)


if __name__ == "__main__":
    main()
