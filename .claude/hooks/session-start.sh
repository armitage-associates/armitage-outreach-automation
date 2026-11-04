#!/bin/bash
# SessionStart hook: install Python deps and verify the Salesforce connection.
# Runs only in the Claude Code on the web (remote) environment.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

echo "[session-start] Installing Python dependencies..."
pip install --quiet -r requirements.txt

echo "[session-start] Verifying Salesforce connection..."
set +e
python salesforce/verify_connection.py
sf_status=$?
set -e

if [ "$sf_status" -eq 3 ]; then
  echo "[session-start] Salesforce credentials not configured - live check skipped."
  echo "[session-start] Add SALESFORCE_DOMAIN, CONSUMER_KEY, CONSUMER_SECRET as environment"
  echo "[session-start] secrets in the web environment settings to enable live queries."
elif [ "$sf_status" -ne 0 ]; then
  echo "[session-start] WARNING: Salesforce connection check failed (continuing anyway)."
fi

exit 0
