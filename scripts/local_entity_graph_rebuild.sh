#!/usr/bin/env bash
# Local bankruptcy rebuild: purge entity graphs, re-extract with GROBID, rebuild NER graph.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CORPUS="${CORPUS:-$ROOT/corpora/AI-ML-research}"
export BIBLICUS_GROBID_URL="${BIBLICUS_GROBID_URL:-http://127.0.0.1:8070}"
export BIBLICUS_GROBID_MAX_CONCURRENT="${BIBLICUS_GROBID_MAX_CONCURRENT:-2}"
export BIBLICUS_GROBID_MAX_RETRIES="${BIBLICUS_GROBID_MAX_RETRIES:-3}"
export EXTRACT_MAX_WORKERS="${EXTRACT_MAX_WORKERS:-2}"
export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"
LOG_DIR="${LOG_DIR:-/tmp/biblicus-entity-rebuild}"
mkdir -p "$LOG_DIR"

cd "$ROOT"

echo "==> GROBID JIT auto-start enabled (Docker on localhost; sample probe)"
python3 scripts/diagnose_grobid_extraction.py --corpus "$CORPUS" --sample-size 8 --workers "$BIBLICUS_GROBID_MAX_CONCURRENT" \
  || { echo "GROBID probe failed after auto-start attempt." >&2; exit 1; }

echo "==> Purging local entity graph artifacts"
python3 scripts/purge_local_entity_graph.py --corpus "$CORPUS"

echo "==> Rebuilding text extraction snapshot (GROBID PDF + pipeline)"
python3 -m biblicus extract build \
  --corpus "$CORPUS" \
  --configuration-name ai-ml-research-topic-text \
  --configuration configurations/extraction/ai-ml-research-topic-text.yml \
  --force \
  --max-workers "${EXTRACT_MAX_WORKERS:-4}" \
  2>&1 | tee "$LOG_DIR/extract-build.log"

SNAPSHOT="$(python3 -c "
import json, subprocess
out = subprocess.check_output(['python3','-m','biblicus','extract','list','--corpus', '$CORPUS'], text=True)
entries = json.loads(out)
pipe = next(e for e in entries if e.get('extractor_id')=='pipeline')
print(f\"pipeline:{pipe['snapshot_id']}\")
")"
echo "==> Using extraction snapshot $SNAPSHOT"

echo "==> Building ner-entities graph snapshot"
python3 -m biblicus graph extract \
  --corpus "$CORPUS" \
  --extractor ner-entities \
  --configuration-name ner-entities \
  --configuration configurations/graph/ner-entities.yml \
  --extraction-snapshot "$SNAPSHOT" \
  --item-timeout-seconds 120 \
  2>&1 | tee "$LOG_DIR/graph-extract.log"

GRAPH_SNAP="$(python3 -c "
import json, subprocess
out = subprocess.check_output(['python3','-m','biblicus','graph','list','--corpus', '$CORPUS', '--extractor-id', 'ner-entities'], text=True)
latest = json.loads(out)[0]
print(f\"ner-entities:{latest['snapshot_id']}\")
")"
EXPORT="$LOG_DIR/graph-export.json"
echo "==> Exporting $GRAPH_SNAP to $EXPORT"
python3 -m biblicus graph export \
  --corpus "$CORPUS" \
  --snapshot "$GRAPH_SNAP" \
  --output "$EXPORT"

SUMMARY="$LOG_DIR/entity-summary.json"
echo "==> Analysis summary -> $SUMMARY"
python3 scripts/analyze_local_entity_graph.py "$EXPORT" --output "$SUMMARY"
echo "Done. Export: $EXPORT  Summary: $SUMMARY"
