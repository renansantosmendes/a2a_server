# A2A agents server

One HTTP application that serves every agent in the `agents/` folder over the
[A2A protocol](https://a2aproject.github.io/A2A/). Each agent is a deep agent
(`deepagents`) with OpenAI models, and agents can call each other.

## Routes

Each folder in `agents/` is published at its own route:

| Method and path | Description |
| --- | --- |
| `GET /` | Lists the agents and their routes. |
| `GET /<agent>/.well-known/agent-card.json` | AgentCard of the agent. |
| `POST /<agent>` | A2A JSON-RPC endpoint (`SendMessage`, `GetTask`, `CancelTask`). |

The current agents are `agent1` and `agent2`. Agent 2 calls agent 1 through
the `consultar_agente1` tool.

## Layout

```
a2a_server/
  app.py                 entrypoint: `app` for Vercel and uvicorn
  agents/                one folder per agent (see agents/README.md)
    agent1/  config.py, agent.py
    agent2/  config.py, agent.py
  server/                generic code: registry, app factory, executor, A2A client
  tests/                 pytest suite
  demo/                  earlier two-server demo on ports 9101 and 9102 (independent)
  vercel.json            maxDuration for app.py
  .python-version        Python 3.13 for Vercel
  .vercelignore          files not sent to Vercel
  requirements.txt       runtime dependencies
  requirements-dev.txt   runtime dependencies plus pytest
```

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | yes | Key used by the OpenAI models. Read from `.env` locally. |
| `PUBLIC_BASE_URL` | no | Public base URL written into the agent cards and used by agent 2 to call agent 1. Defaults to `https://$VERCEL_URL` on Vercel and `http://127.0.0.1:8000` locally. |

The `.env` file stays on your machine. On Vercel, set the variables in the
project settings.

## Run locally

Create the environment once, from this folder:

```powershell
uv venv .venv --python 3.13
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
```

Start the server:

```powershell
.venv\Scripts\python.exe app.py
```

Check the routes:

```powershell
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/agent1/.well-known/agent-card.json
```

Ask agent 2 a question (it calls agent 1 internally):

```powershell
.venv\Scripts\python.exe -c "import asyncio; from server.a2a_client import ask_agent; print(asyncio.run(ask_agent('http://127.0.0.1:8000/agent2', 'Qual e a capital da Franca?')))"
```

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q tests
```

The tests do not call the OpenAI API. They use a placeholder key.

## Deploy on Vercel

The app is deployed as a Python function. Vercel finds `app.py` and the
variable `app` automatically, and reads the dependencies from
`requirements.txt`.

1. Install the Vercel CLI and log in: `vercel login`.
2. In the project folder, run `vercel` for a preview, or `vercel --prod`.
3. In the Vercel dashboard, add `OPENAI_API_KEY` to the environment variables
   of the project.
4. Open `https://<project>.vercel.app/` to check the agent index.

### Limits to keep in mind

- **Duration:** `vercel.json` sets `maxDuration` to 300 seconds, the limit on
  the Hobby plan. A request to agent 2 makes two LLM chains, so long questions
  can time out on this plan.
- **Memory:** tasks are kept in memory. On Vercel, a later request can run on
  another instance, so `GetTask` and `CancelTask` for a task created earlier
  may fail. Persistent storage is the next step if this matters.
- **Size:** the bundle must stay under 500 MB uncompressed.
