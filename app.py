"""Entrypoint of the A2A agents server, used locally and on Vercel."""

import uvicorn

from server.app_factory import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
