"""Tests for the agent folder discovery in server.registry."""

from pathlib import Path

import pytest

from server.registry import (
    discover_agent_names,
    is_valid_agent_name,
    load_agent_spec,
)


def make_agent_folder(
    root: Path,
    name: str,
) -> None:
    """Create a minimal agent folder with config.py and agent.py.

    Parameters
    ----------
    root : Path
        Folder that will contain the agent folder.
    name : str
        Name of the agent folder to create.

    Returns
    -------
    None
    """
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "config.py").write_text("", encoding="utf-8")
    (folder / "agent.py").write_text("", encoding="utf-8")


@pytest.mark.parametrize(
    "name",
    ["agent1", "research_agent", "agent-2", "a"],
)
def test_is_valid_agent_name_accepts_url_safe_names(name: str) -> None:
    """Accept lowercase names that are safe as URL routes."""
    assert is_valid_agent_name(name) is True


@pytest.mark.parametrize(
    "name",
    ["Agent1", "1agent", "agent name", "agent.py", "", "agent/x"],
)
def test_is_valid_agent_name_rejects_unsafe_names(name: str) -> None:
    """Reject names with uppercase, spaces, dots or a leading digit."""
    assert is_valid_agent_name(name) is False


def test_discover_agent_names_returns_only_folders_with_agent_files(
    tmp_path: Path,
) -> None:
    """Return sorted agent folders and ignore incomplete folders."""
    make_agent_folder(tmp_path, "agent2")
    make_agent_folder(tmp_path, "agent1")
    (tmp_path / "incomplete").mkdir()
    (tmp_path / "loose_file.py").write_text("", encoding="utf-8")

    assert discover_agent_names(tmp_path) == ["agent1", "agent2"]


def test_discover_agent_names_rejects_invalid_folder_name(
    tmp_path: Path,
) -> None:
    """Raise ValueError when an agent folder name cannot be a route."""
    make_agent_folder(tmp_path, "Bad Name")

    with pytest.raises(ValueError, match="Invalid agent folder name"):
        discover_agent_names(tmp_path)


def test_load_agent_spec_reads_config_and_build_function() -> None:
    """Load the real agent1 package and read its identity fields."""
    spec = load_agent_spec("agent1")

    assert spec.name == "agent1"
    assert spec.display_name == "Agent 1"
    assert spec.skill_id == "answer"
    assert callable(spec.build)
