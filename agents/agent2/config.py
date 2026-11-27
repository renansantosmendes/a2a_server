"""Configuration of agent 2."""

AGENT_DISPLAY_NAME = "Agent 2"
AGENT_DESCRIPTION = "Deep agent that answers questions by consulting agent 1."
SKILL_ID = "answer-with-agent1"
SKILL_NAME = "Answer through agent 1"
SKILL_DESCRIPTION = "Answers questions using agent 1 over A2A."
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0
TARGET_AGENT_NAME = "agent1"
SYSTEM_PROMPT = (
    "Voce e o Agente 2. Para responder ao usuario, use a ferramenta "
    "consultar_agente1 com a pergunta e entregue a resposta do Agente 1 "
    "de forma clara, em portugues."
)
