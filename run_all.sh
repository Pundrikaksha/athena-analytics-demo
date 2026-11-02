#!/bin/sh
# Build the page, run the tests, evaluate the detector and prove the outputs are reproducible.
# Usage: ./run_all.sh                 (uses python3.12 if present, otherwise python3)
#        PYTHON=/path/to/python ./run_all.sh
set -eu
cd "$(dirname "$0")"

PINNED=3.12
MINIMUM_MINOR=9
if [ -z "${PYTHON:-}" ]; then
  if command -v "python$PINNED" >/dev/null 2>&1; then PYTHON="python$PINNED"; else PYTHON=python3; fi
fi
export PYTHONDONTWRITEBYTECODE=1

VERSION=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
"$PYTHON" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, $MINIMUM_MINOR) else 1)" || {
  echo "ERROR: Python 3.$MINIMUM_MINOR or newer is required, found $VERSION" >&2; exit 1; }
echo "== Python: $("$PYTHON" --version 2>&1) (reference version: $PINNED)"
[ "$VERSION" = "$PINNED" ] || echo "   note: not the reference version; outputs are still checked below"

echo "== 1/4 Build"
"$PYTHON" -m athena_demo.build

echo "== 2/4 Evaluate"
"$PYTHON" scripts/evaluate_anomaly.py --out docs/data/anomaly_evaluation.json >/dev/null
"$PYTHON" - <<'PY'
import json
report = json.load(open("docs/data/anomaly_evaluation.json"))
test = report["test_seeds_1000_1199"]
print(f"{'held-out seeds 1000-1199':<26}{'precision':>10}{'recall':>8}{'f1':>7}")
for name, m in list(test["by_type"].items()) + [("all types", test)]:
    print(f"{name:<26}{m['precision']:>10.3f}{m['recall']:>8.3f}{m['f1']:>7.3f}")
PY

echo "== 3/4 Test"
"$PYTHON" -m unittest

echo "== 4/4 Reproduce"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PYTHONHASHSEED=12345 "$PYTHON" -m athena_demo.build --out "$TMP" >/dev/null
PYTHONHASHSEED=12345 "$PYTHON" scripts/evaluate_anomaly.py --out "$TMP/data/anomaly_evaluation.json" >/dev/null
diff -r docs "$TMP" >/dev/null || { echo "ERROR: a second build differs from docs/" >&2; diff -rq docs "$TMP" >&2; exit 1; }
echo "a second, independent build is byte-identical to docs/"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -z "$(git status --porcelain -- docs)" ]; then
    echo "docs/ matches the committed version"
  else
    echo "note: docs/ differs from the last commit (expected only if you changed the code)"
  fi
fi

if command -v node >/dev/null 2>&1; then
  echo "== Optional: browser check"
  node scripts/browser_check.js | tail -1
else
  echo "== Optional: browser check SKIPPED (node not installed)"
fi
echo "ALL STEPS PASSED"
