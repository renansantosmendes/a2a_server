# A2A agents server

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![A2A SDK](https://img.shields.io/badge/A2A_SDK-1.3.0-4B5563)
![deepagents](https://img.shields.io/badge/deepagents-0.7.9-1C3C3C)
![LangChain](https://img.shields.io/badge/langchain--openai-1.6.0-1C3C3C?logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.11-1C3C3C)
![Starlette](https://img.shields.io/badge/Starlette-1.10.0-EE2B2B)
![uvicorn](https://img.shields.io/badge/uvicorn-0.52.4-499848)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)
![Langfuse](https://img.shields.io/badge/Langfuse-5.2.0-000000)
![Vercel](https://img.shields.io/badge/Vercel-deploy-000000?logo=vercel&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9)
![pytest](https://img.shields.io/badge/pytest-9.0.3-0A9EDC?logo=pytest&logoColor=white)
![pylint](https://img.shields.io/badge/pylint-10%2F10-yellow)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)

One HTTP application that serves every agent in the `agents/` folder over the
[A2A protocol](https://a2aproject.github.io/A2A/). Each agent is a deep agent
(`deepagents`) that uses OpenAI models, and agents can call each other over A2A.

## Overview

```mermaid
flowchart LR
    client["Cliente A2A<br/>curl, chat local"] -->|JSON-RPC| app["app.py<br/>Starlette"]
    app --> r2["/agent2"]
    app --> r1["/agent1"]
    r2 --> e2["DeepAgentExecutor<br/>agente 2"]
    r1 --> e1["DeepAgentExecutor<br/>agente 1"]
    e2 -->|"tool consultar_agente1<br/>A2A SendMessage"| r1
    e1 --> openai["OpenAI"]
    e2 --> openai
    e1 -.->|traces| langfuse["Langfuse"]
    e2 -.->|traces| langfuse
```

A larger architecture diagram, in Excalidraw, is in
[`docs/architecture.excalidraw`](docs/architecture.excalidraw). Open it at
[excalidraw.com](https://excalidraw.com) with **Open**, or with the Excalidraw
extension in VS Code.

## Request flow

The sequence below shows what happens when a client asks agent 2 a question
that needs agent 1.

```mermaid
sequenceDiagram
    autonumber
    participant U as Cliente
    participant S as Servidor (app.py)
    participant A2 as Agente 2
    participant A1 as Agente 1
    participant O as OpenAI
    participant L as Langfuse
    U->>S: POST /agent2 SendMessage
    S->>A2: ainvoke(messages, callbacks)
    A2->>O: chamada LLM
    O-->>A2: usar consultar_agente1
    A2->>S: POST /agent1 SendMessage (A2A)
    S->>A1: ainvoke(messages)
    A1->>O: chamada LLM
    O-->>A1: resposta
    A1-->>S: task completed com artifact
    S-->>A2: resposta do agente 1
    A2->>O: chamada LLM com a resposta
    O-->>A2: resposta final
    A2-->>S: task completed com artifact
    S-->>U: resposta do agente 2
    A2-->>L: traces enviados antes da resposta
```

## How agents are discovered

Each folder in `agents/` becomes a route. Adding an agent needs no change in
the server code.

```mermaid
flowchart TD
    start["create_app()"] --> discover["discover_agent_names(agents/)<br/>pastas com config.py e agent.py"]
    discover --> loop{"para cada agente"}
    loop --> load["load_agent_spec(nome)<br/>importa config.py e agent.py"]
    load --> build["spec.build(base_url)<br/>devolve o deep agent"]
    build --> executor["DeepAgentExecutor"]
    executor --> routes["POST /nome<br/>GET /nome/.well-known/agent-card.json"]
    routes --> loop
    loop -->|"todos publicados"| index["GET / e GET /docs"]
```

## Routes

| Method and path | Description |
| --- | --- |
| `GET /` | Lists the agents and their routes as JSON. |
| `GET /docs` | Documentation page with the endpoints, skills and an example `curl` for each agent. Open it at `http://localhost:8000/docs`. |
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
  server/                generic code
    registry.py          finds and loads the agent folders
    app_factory.py       builds the Starlette app and the routes
    executor.py          runs each request through a deep agent
    a2a_client.py        A2A client used by agents to call other agents
    agent_card.py        builds the AgentCard
    tracing.py           Langfuse callbacks and flush
    settings.py          environment and public base URL
  tests/                 pytest suite, mirrors server/ and agents/
  docs/                  architecture diagram (Excalidraw)
  vercel.json            maxDuration for app.py
  .python-version        Python 3.13 for Vercel
  .vercelignore          files not sent to Vercel
  .pylintrc              pylint settings
  .github/workflows/     CI pipeline
  requirements.txt       runtime dependencies
  requirements-dev.txt   runtime dependencies plus the development tools
```

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | yes | Key used by the OpenAI models. Read from `.env` locally. |
| `PUBLIC_BASE_URL` | no | Public base URL written into the agent cards and used by agent 2 to call agent 1. Defaults to `https://$VERCEL_URL` on Vercel and `http://127.0.0.1:8000` locally. |
| `LANGFUSE_PUBLIC_KEY` | no | Public key of the Langfuse project. Tracing is enabled only when this and the secret key are set. |
| `LANGFUSE_SECRET_KEY` | no | Secret key of the Langfuse project. |
| `LANGFUSE_HOST` | no | Langfuse host, for example `https://cloud.langfuse.com`. |

The `.env` file stays on your machine. On Vercel, set the variables in the
project settings.

## Tracing with Langfuse

When the Langfuse keys are set, every agent run is sent to Langfuse with its
LLM calls, tool calls and token usage. Each trace is named after the agent
route (for example `agent1`) and carries the A2A task id in its metadata.

- Without the keys, the agents run normally and no trace is sent.
- The traces are flushed before each answer is returned, which matters on
  Vercel because the function can stop right after responding.
- Failures to send traces are logged and do not affect the answer.
- The tracing code lives in `server/tracing.py`. The executor in
  `server/executor.py` attaches the callbacks to each run.

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

The tests do not call the OpenAI API and do not send traces to Langfuse. A
fixture in `tests/conftest.py` removes the Langfuse keys and skips the `.env`
file for every test.

Lint, coverage and security checks, run the same way as in CI:

```powershell
.venv\Scripts\python.exe -m pylint server agents app.py tests
.venv\Scripts\python.exe -m pytest -q tests --cov=server --cov=agents --cov-fail-under=80
.venv\Scripts\python.exe -m bandit -r server agents app.py -ll
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

Pylint settings are in `.pylintrc`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request.

```mermaid
flowchart LR
    trigger["push ou pull request"] --> structure["structure<br/>arquivos, .env, pins, agentes"]
    structure --> lint["lint<br/>pylint"]
    lint --> unit["unit-test<br/>pytest, cobertura 80%"]
    lint --> security["security<br/>bandit, pip-audit, gitleaks"]
    unit --> report["test-report"]
    security --> report
    report --> success["pipeline-success"]
```

| Job | Checks |
| --- | --- |
| `structure` | Required files, `.env` ignored and not tracked, Vercel config, pinned dependencies, every agent folder has `config.py`, `agent.py` and `tests/agents/test_<name>.py`. |
| `lint` | pylint on `server`, `agents`, `app.py` and `tests`. |
| `unit-test` | pytest with coverage of at least 80%. Uploads the JUnit and coverage reports. |
| `security` | bandit on the application code, pip-audit on `requirements.txt`, gitleaks on the git history. |
| `test-report` | Job summary table. |
| `pipeline-success` | Fails if any required job did not succeed. |

## Deploy on Vercel

The app is deployed as a Python function. Vercel finds `app.py` and the
variable `app` automatically, and reads the dependencies from
`requirements.txt`.

1. Install the Vercel CLI and log in: `vercel login`.
2. In the project folder, run `vercel` for a preview, or `vercel --prod`.
3. In the Vercel dashboard, add `OPENAI_API_KEY` to the environment variables
   of the project. Add the Langfuse variables too, if you want tracing.
4. Open `https://<project>.vercel.app/` to check the agent index.

### Limits to keep in mind

- **Duration:** `vercel.json` sets `maxDuration` to 300 seconds, the limit on
  the Hobby plan. A request to agent 2 makes two LLM chains, so long questions
  can time out on this plan.
- **Memory:** tasks are kept in memory. On Vercel, a later request can run on
  another instance, so `GetTask` and `CancelTask` for a task created earlier
  may fail. Persistent storage is the next step if this matters.
- **Size:** the bundle must stay under 500 MB uncompressed.
- **Protection:** a deployment with Vercel Authentication enabled answers
  external clients with a login page, so they cannot call the agents.
