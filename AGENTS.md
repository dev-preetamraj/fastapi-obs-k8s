# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project intent

Learning playground for **FastAPI + Observability + Kubernetes** (per the repo name `fastapi-obs-k8s`). Early-stage: one `GET /` handler in `src/app/main.py` and a containerised local-run setup. No k8s manifests yet — when adding them, you are establishing convention, not following one.

## Toolchain

- Python **3.13+** (pinned in `.python-version`), managed by **uv**. `pyproject.toml` is the single source of truth — do not introduce `requirements.txt`.
- Runtime deps: `fastapi[standard]`, `structlog`. Dev deps: `ruff`, `pytest`, `pytest-asyncio`, `httpx`.

## Common commands

```bash
uv sync                              # install/refresh deps into .venv
uv run fastapi dev src/app/main.py       # dev server with reload (http://127.0.0.1:8000)
uv run fastapi run src/app/main.py       # production-style run
uv add <pkg>                         # add a dependency (updates pyproject.toml + uv.lock)
uv run python -m <module>            # run anything inside the project venv
uv run ruff format .                 # format codebase
uv run ruff check --fix .            # lint + auto-fix (incl. import sorting via `I` rules)
uv run pytest                        # test suite (asyncio mode = auto, testpaths = tests/)
bash scripts/smoke_observability.sh  # end-to-end logs pipeline check (stack must be up)
```

Ruff handles both formatting and linting (no Black). Config lives in `pyproject.toml` under `[tool.ruff]`. VS Code is wired via `.vscode/settings.json` to format and organize imports on save using the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff).

## Container workflow

Always use `docker compose` — never raw `docker build` / `docker run`.

```bash
docker compose up --build -d        # build + start `api` on :8000
docker compose down                 # stop + remove
```

`Dockerfile` is a two-stage uv build → non-root `python:3.13-slim-bookworm` runtime. Compose file is v2 spec (no `version:` key), single `api` service. No `HEALTHCHECK` (k8s probes will own that) and no `src/` bind-mount (image runs production-style; add a `compose.override.yml` if you want `fastapi dev` reload).

## Layout note

Project uses the **src-layout**: the importable package is `src/app/`, wired through `[tool.hatch.build.targets.wheel] packages = ["src/app"]` in `pyproject.toml`. `uv sync` installs `app` editably into the venv, so every module imports as `from app.<module> import ...` — never `from src...`, never a `sys.path` hack. New modules go inside `src/app/` (or a subpackage of it).

FastAPI is launched via file path (`src/app/main.py`) — the editable install means imports inside `main.py` resolve the same way they do in tests.

## Observability

Structured logging via **structlog** → JSON to stdout. Every request log line carries `trace_id` (W3C 32-hex) and `span_id` (16-hex) bound via `structlog.contextvars`. Responses carry `X-Trace-Id`. Inbound `traceparent` is honored; malformed values fall back to a fresh ID.

Env knobs: `LOG_LEVEL` (default `INFO`), `LOG_FORMAT` (`json` default, `console` for dev), `SERVICE_NAME` (default `fastapi-obs-k8s`).

Stack lives under `observability/` (loki, alloy, prometheus, grafana). `docker compose up -d` brings it up alongside `api`. Grafana on `:3000` (anonymous Admin), Loki on `:3100`, Alloy UI on `:12345`, Prometheus on `:9090`. Alloy discovers containers via compose labels — dashboards/datasources are gitops-provisioned (UI edits are ephemeral).

Prometheus scrapes `api:8000/metrics` directly (see `observability/prometheus/prometheus.yml`). App-level metrics are defined in `src/app/metrics.py` and use the `fastapi_*` prefix with an `app_name` label (sourced from `SERVICE_NAME`) — the names match grafana.com dashboard 16110.
