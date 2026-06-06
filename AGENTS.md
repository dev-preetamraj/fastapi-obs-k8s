# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project intent

Learning playground for **FastAPI + Observability + Kubernetes** (per the repo name `fastapi-obs-k8s`). The codebase is at day-zero: a single FastAPI `GET /` handler in `src/main.py` and nothing else. README is empty. There are no tests, lint config, Dockerfile, or k8s manifests yet — when adding them, you are establishing convention, not following one.

## Toolchain

- Python **3.13+** (pinned in `.python-version`), managed by **uv**. `pyproject.toml` is the single source of truth — do not introduce `requirements.txt`.
- Only runtime dependency today: `fastapi[standard]` (pulls in `uvicorn`, `httpx`, CLI, etc.).

## Common commands

```bash
uv sync                              # install/refresh deps into .venv
uv run fastapi dev src/main.py       # dev server with reload (http://127.0.0.1:8000)
uv run fastapi run src/main.py       # production-style run
uv add <pkg>                         # add a dependency (updates pyproject.toml + uv.lock)
uv run python -m <module>            # run anything inside the project venv
uv run ruff format .                 # format codebase
uv run ruff check --fix .            # lint + auto-fix (incl. import sorting via `I` rules)
```

Ruff handles both formatting and linting (no Black). Config lives in `pyproject.toml` under `[tool.ruff]`. VS Code is wired via `.vscode/settings.json` to format and organize imports on save using the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff).

No test runner is wired up yet. If you add one, prefer `pytest` and record the invocation here.

## Layout note

`src/` is a plain directory (not a configured package in `pyproject.toml`). FastAPI is launched by **file path** (`src/main.py`), not by import path. If you later need `from src...` imports or `uv build`, add a `[tool.hatch.build.targets.wheel]` / `[tool.setuptools]` block — don't assume one exists.
