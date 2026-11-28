"""Configuration of agent 1."""

AGENT_DISPLAY_NAME = "Agent 1"
AGENT_DESCRIPTION = "Deep agent that answers general questions."
SKILL_ID = "answer"
SKILL_NAME = "Answer questions"
SKILL_DESCRIPTION = "Answers general questions in Portuguese."
ALLOWED_ROLES = ("student", "professor")
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0
SYSTEM_PROMPT = (
    "Voce e o Agente 1. Responda as perguntas em portugues, de forma "
    "clara e objetiva."
)
