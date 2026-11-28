"""Discovery and loading of the agents stored in the agents folder."""

import importlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Tuple

AGENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
REQUIRED_CONFIG_FIELDS = (
    "AGENT_DISPLAY_NAME",
    "AGENT_DESCRIPTION",
    "SKILL_ID",
    "SKILL_NAME",
    "SKILL_DESCRIPTION",
)
DEFAULT_ALLOWED_ROLES = ("student", "professor")


@dataclass(frozen=True)
class AgentSpec:
    """Everything the server needs to publish one agent.

    Parameters
    ----------
    name : str
        Route name of the agent, equal to its folder name.
    display_name : str
        Human readable name shown in the agent card.
    description : str
        Short description of the agent.
    skill_id : str
        Identifier of the skill advertised by the agent.
    skill_name : str
        Display name of the skill.
    skill_description : str
        Explanation of what the skill answers.
    build : Callable[[str], Any]
        Function that receives the public base URL and returns the
        compiled agent.
    allowed_roles : tuple[str, ...]
        Roles allowed to send messages to the agent, taken from the
        ``ALLOWED_ROLES`` constant of ``config.py``.

    Example
    -------
    >>> load_agent_spec("agent1").skill_id
    'answer'
    """

    name: str
    display_name: str
    description: str
    skill_id: str
    skill_name: str
    skill_description: str
    build: Callable[[str], Any]
    allowed_roles: Tuple[str, ...] = DEFAULT_ALLOWED_ROLES


def is_valid_agent_name(name: str) -> bool:
    """Check whether a folder name can be used as a URL route.

    Parameters
    ----------
    name : str
        Folder name to check.

    Returns
    -------
    bool
        True when the name starts with a lowercase letter and contains only
        lowercase letters, digits, underscores or hyphens.

    Example
    -------
    >>> is_valid_agent_name("agent1")
    True
    """
    return AGENT_NAME_PATTERN.match(name) is not None


def discover_agent_names(agents_dir: Path) -> list[str]:
    """List the agent folders that follow the agent file pattern.

    A folder is an agent when it contains both ``config.py`` and
    ``agent.py``.

    Parameters
    ----------
    agents_dir : Path
        Folder that contains one sub-folder per agent.

    Returns
    -------
    list[str]
        Sorted names of the valid agent folders.

    Raises
    ------
    ValueError
        If a folder with the agent files has an invalid route name.

    Example
    -------
    >>> discover_agent_names(Path("agents"))
    ['agent1', 'agent2']
    """
    names = []
    for folder in sorted(agents_dir.iterdir()):
        has_files = (folder / "config.py").is_file() and (
            folder / "agent.py"
        ).is_file()
        if not folder.is_dir() or not has_files:
            continue
        if not is_valid_agent_name(folder.name):
            raise ValueError(
                f"Invalid agent folder name: {folder.name!r}. Use lowercase "
                "letters, digits, '_' or '-', starting with a letter."
            )
        names.append(folder.name)
    return names


def load_agent_spec(name: str) -> AgentSpec:
    """Import the config and agent modules of one agent folder.

    Parameters
    ----------
    name : str
        Folder name of the agent, used as route name.

    Returns
    -------
    AgentSpec
        Specification built from the agent's ``config.py`` and ``agent.py``.

    Raises
    ------
    AttributeError
        If ``config.py`` does not define one of the required fields or
        ``agent.py`` does not define ``build_agent``.

    Example
    -------
    >>> load_agent_spec("agent1").display_name
    'Agent 1'
    """
    config = importlib.import_module(f"agents.{name}.config")
    agent_module = importlib.import_module(f"agents.{name}.agent")
    for field_name in REQUIRED_CONFIG_FIELDS:
        getattr(config, field_name)
    build_agent = getattr(agent_module, "build_agent")
    return AgentSpec(
        name=name,
        display_name=config.AGENT_DISPLAY_NAME,
        description=config.AGENT_DESCRIPTION,
        skill_id=config.SKILL_ID,
        skill_name=config.SKILL_NAME,
        skill_description=config.SKILL_DESCRIPTION,
        build=build_agent,
        allowed_roles=tuple(
            getattr(config, "ALLOWED_ROLES", DEFAULT_ALLOWED_ROLES)
        ),
    )
