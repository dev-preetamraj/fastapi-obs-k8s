# TODOS

Deferred follow-ups to the structured-logging PR. Each item has the context needed to pick up cold.

## 1. Wire OpenTelemetry SDK + OTLP → Tempo

**Closes the loop on the "Grafana-ready" promise.** The logging PR emits Loki-correlatable IDs in W3C format; this PR makes those IDs click through to real spans in Tempo.

- Install: `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp`.
- Replace hand-rolled `secrets.token_hex` ID generation in `src/middleware/logging.py` with IDs from the OTel SDK. Field names and ID format don't change — the swap is mechanical.
- Replace `RequestContextMiddleware` with `FastAPIInstrumentor.instrument_app(app)` (keep the contextvar-binding bits so structlog still sees `trace_id` / `span_id`).
- Export to Tempo via Grafana Alloy (or direct OTLP HTTP/gRPC).

**Blocked by:** Tempo (or any OTLP-receiving collector) reachable from the cluster.

## 2. Add Prometheus `/metrics` endpoint

**Completes the observability triad (logs + traces + metrics).**

- Add `prometheus-fastapi-instrumentator`, expose `/metrics`, label with `service` and `path`.
- Add a `ServiceMonitor` to k8s manifests when Prometheus/Mimir is deployed.
- Network-policy `/metrics` off public ingress in real clusters.

**Blocked by:** Nothing technical. Value gated on Prometheus scraping being configured.

## 3. Outbound `traceparent` propagation on `httpx`

**Prevents the trace breaking at the first outbound call.**

- Provide an `httpx.AsyncClient` factory that injects `traceparent: 00-{trace_id}-{span_id}-01` via an event hook, reading the IDs from `structlog.contextvars.get_contextvars()`.

**Blocked by:** First outbound HTTP call being added to the app.
**Superseded by TODO 1** if OTel lands first — `HTTPXClientInstrumentor` makes this automatic.
