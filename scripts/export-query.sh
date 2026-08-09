#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
DATABASE_ID=""
EXPORT_FORMAT=""
QUERY_TEXT=""
OUTPUT_FILE=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/export-query.sh --database-id <id> --format <csv|json> --query <sql> [--output <file>]

Environment:
  API_BASE_URL  Backend API base URL (default: http://127.0.0.1:8000/api/v1)
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --database-id)
      DATABASE_ID="${2:-}"
      shift 2
      ;;
    --format)
      EXPORT_FORMAT="${2:-}"
      shift 2
      ;;
    --query)
      QUERY_TEXT="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$DATABASE_ID" ] || [ -z "$QUERY_TEXT" ] || { [ "$EXPORT_FORMAT" != "csv" ] && [ "$EXPORT_FORMAT" != "json" ]; }; then
  echo "database-id, format and query are required; format must be csv or json" >&2
  usage >&2
  exit 2
fi

if [ -z "$OUTPUT_FILE" ]; then
  OUTPUT_FILE="query-result-$(date +%Y%m%d-%H%M%S).${EXPORT_FORMAT}"
fi

PAYLOAD="$(DATABASE_ID_VALUE="$DATABASE_ID" EXPORT_FORMAT_VALUE="$EXPORT_FORMAT" QUERY_TEXT_VALUE="$QUERY_TEXT" python3 - <<'PY'
import json
import os

print(json.dumps({
    "databaseId": os.environ["DATABASE_ID_VALUE"],
    "queryText": os.environ["QUERY_TEXT_VALUE"],
    "exportFormat": os.environ["EXPORT_FORMAT_VALUE"],
    "querySource": "command",
}, ensure_ascii=False))
PY
)"

curl --fail-with-body -sS \
  -X POST "${API_BASE_URL}/query/export" \
  -H 'Content-Type: application/json' \
  --data "$PAYLOAD" \
  -o "$OUTPUT_FILE"

echo "Exported ${EXPORT_FORMAT} result to ${OUTPUT_FILE}"
