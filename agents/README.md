# Agents

Each sub-folder of this folder is one agent. The server finds the folders
automatically, publishes each one at its own route and needs no code change
to add a new agent.

## File pattern

```
agents/
  <agent_name>/
    __init__.py    docstring only
    config.py      identity, skill and model constants
    agent.py       build_agent(base_url) -> compiled deep agent
```

### Naming

- The folder name is the route name. It must start with a lowercase letter
  and use only lowercase letters, digits, `_` or `-`.
- Folder `agent1` is served at `POST /agent1` and its card is at
  `GET /agent1/.well-known/agent-card.json`.

### `config.py`

Required constants (the server fails at startup when one is missing):

| Constant | Description |
| --- | --- |
| `AGENT_DISPLAY_NAME` | Name shown in the agent card. |
| `AGENT_DESCRIPTION` | Short description of the agent. |
| `SKILL_ID` | Identifier of the skill advertised in the card. |
| `SKILL_NAME` | Display name of the skill. |
| `SKILL_DESCRIPTION` | What the skill answers. |

Other constants (model name, `TEMPERATURE`, system prompt, target agents)
are free. Keep them here, not in `agent.py`, so the hyperparameters of each
run are recorded in one place.

### `agent.py`

Must define:

```python
def build_agent(base_url: str) -> Any:
    ...
```

- `base_url` is the public base URL of the server, for example
  `http://127.0.0.1:8000` locally or `https://<project>.vercel.app` on
  Vercel. Use it when the agent calls other agents over A2A. Otherwise
  ignore it.
- Return a compiled deep agent that accepts
  `{"messages": [{"role": "user", "content": ...}]}`.

## Calling another agent

Use `server.a2a_client.ask_agent(url, question)` from a tool. The URL is
`f"{base_url}/<target_agent_name>"`. See `agents/agent2/agent.py`.

## Adding an agent

1. Create `agents/<name>/` with the three files above.
2. Start the server (see the root README). The new agent appears in `GET /`.
3. Add a test in `tests/` if the agent has logic beyond the defaults.

## Existing agents

| Folder | Route | Purpose |
| --- | --- | --- |
| `agent1/` | `/agent1` | Answers general questions. |
| `agent2/` | `/agent2` | Answers by consulting agent 1 through the `consultar_agente1` tool. |
