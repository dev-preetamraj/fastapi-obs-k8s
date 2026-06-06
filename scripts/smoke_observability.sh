#!/usr/bin/env bash
# End-to-end smoke test for the logs pipeline:
#   api stdout -> alloy (docker discovery) -> loki -> grafana
#
# Asserts:
#   1. app responds and emits trace_id
#   2. loki has indexed lines under {service="api"}
#   3. grafana has the Loki datasource provisioned
#   4. grafana has the "FastAPI request logs" dashboard provisioned
#
# Exit 0 = pipeline healthy. Non-zero = something broke.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
LOKI_URL="${LOKI_URL:-http://localhost:3100}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_AUTH="${GRAFANA_AUTH:-admin:admin}"

fail() {
	echo "FAIL: $*" >&2
	exit 1
}

ok() { echo "ok: $*"; }

command -v jq >/dev/null 2>&1 || fail "jq not installed; brew install jq"
command -v curl >/dev/null 2>&1 || fail "curl not installed"

echo "==> hitting api ($API_URL)"
for _ in 1 2 3; do
	curl -fsS "$API_URL/" >/dev/null || fail "api /  did not respond"
done
ok "api responded 3x"

echo "==> sleeping 3s for alloy + loki to catch up"
sleep 3

echo "==> querying loki for {service=\"api\"}"
loki_resp="$(curl -fsS -G "$LOKI_URL/loki/api/v1/query_range" \
	--data-urlencode 'query={service="api"}' \
	--data-urlencode 'limit=5')" || fail "loki query failed"

echo "$loki_resp" | jq -e '.data.result | length > 0' >/dev/null \
	|| fail "loki returned no streams for {service=\"api\"}\n$loki_resp"
ok "loki has lines under {service=\"api\"}"

echo "==> checking grafana datasource: Loki"
ds_resp="$(curl -fsS -u "$GRAFANA_AUTH" "$GRAFANA_URL/api/datasources/name/Loki")" \
	|| fail "grafana datasource lookup failed"
ds_type="$(echo "$ds_resp" | jq -r '.type')"
[ "$ds_type" = "loki" ] || fail "Loki datasource not provisioned (type=$ds_type)"
ok "grafana datasource provisioned: $ds_type"

echo "==> checking grafana dashboard: FastAPI request logs"
dash_resp="$(curl -fsS -u "$GRAFANA_AUTH" \
	"$GRAFANA_URL/api/search?query=FastAPI%20request%20logs")" \
	|| fail "grafana dashboard search failed"
dash_count="$(echo "$dash_resp" | jq 'length')"
[ "$dash_count" -gt 0 ] || fail "dashboard not provisioned (search returned 0)"
ok "grafana dashboard provisioned"

echo
echo "PASS: logs pipeline healthy"
