# TODOS

Deferred follow-ups to the structured-logging PR. Each item has the context needed to pick up cold.

## 1. Wire OpenTelemetry SDK + OTLP → Tempo

**Makes trace_id values in Loki log lines clickable spans in Tempo.** The Grafana + Loki + Alloy slice is now live; this PR completes the trace pillar.

- Install: `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp`.
- Replace hand-rolled `secrets.token_hex` ID generation in `src/app/middleware/logging.py` with IDs from the OTel SDK. Field names and ID format don't change — the swap is mechanical.
- Replace `RequestContextMiddleware` with `FastAPIInstrumentor.instrument_app(app)` (keep the contextvar-binding bits so structlog still sees `trace_id` / `span_id`).
- Add a `tempo` service to `docker-compose.yml` and route OTLP through Alloy (`otelcol.receiver.otlp` → `otelcol.exporter.otlp` → tempo).
- Wire the `derivedFields` block in `observability/grafana/provisioning/datasources/loki.yaml` — set `datasourceUid` to the Tempo datasource UID and `url` to `${__value.raw}`. The regex hook is already in place.

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

## 4. Healthchecks + `depends_on.condition: service_healthy` on the observability stack

**Eliminates cold-start error spam in `alloy` logs while `loki` is still booting.**

- Add a `healthcheck:` block to each of `loki`, `alloy`, `grafana` in `docker-compose.yml`:
  - `loki`: `wget -q -O /dev/null http://localhost:3100/ready`
  - `grafana`: `wget -q -O /dev/null http://localhost:3000/api/health`
  - `alloy`: `wget -q -O /dev/null http://localhost:12345/-/ready`
- Switch `alloy.depends_on` and `grafana.depends_on` to the long form with `condition: service_healthy`.
- Same pattern lift-and-shifts cleanly into k8s readiness/liveness probes when manifests land.

**Blocked by:** Nothing. Cosmetic for local dev; useful before sharing the compose with others.

## 5. Enable Alloy `loki.write` write-ahead log (WAL)

**Survives brief Loki unavailability instead of dropping logs from the in-memory queue.**

- Add a `wal { enabled = true, max_segment_age = "1h" }` block to `loki.write "default"` in `observability/alloy/config.alloy`.
- Add a small named volume `alloy-wal:/var/lib/alloy/data` in `docker-compose.yml` (Alloy already writes its `--storage.path` there).
- Today, Alloy buffers in memory; on overflow it warns and drops. WAL turns drops into durable retry until Loki returns.

**Blocked by:** Nothing. Local dev rarely sees sustained Loki outages, but this is the "right default" for any non-throwaway pipeline.
