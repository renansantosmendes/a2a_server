"""Tests for the allowed roles declared by each agent configuration."""

from server.registry import DEFAULT_ALLOWED_ROLES, load_agent_spec


def test_agents_declare_student_and_professor_access():
    """Check that agents declare student and professor access."""
    assert load_agent_spec("agent1").allowed_roles == ("student", "professor")
    assert load_agent_spec("agent2").allowed_roles == ("student", "professor")


def test_default_roles_cover_both_profiles():
    """Check that default roles cover both profiles."""
    assert DEFAULT_ALLOWED_ROLES == ("student", "professor")
