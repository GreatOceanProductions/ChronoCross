#!/bin/bash
# Test runner wrapper that scrubs PYTHONPATH contamination from
# hermes-agent so the project venv is the import source.
# Per §11.10 of the design document, the test runner is the single
# entry point for the test pipeline.
#
# Usage:
#   tools/run_tests.sh           # all tests
#   tools/run_tests.sh -v        # verbose
#   tools/run_tests.sh tests/test_validate_data.py   # one file
#
# Cron jobs should call this script, not pytest directly.

set -e

# Scrub hermes-agent contamination
unset PYTHONPATH
unset PYTHONHOME
for v in $(env | cut -d= -f1); do
    case "$v" in
        *_HERMES*|HERMES_*)
            unset "$v" ;;
    esac
done

# Activate project venv if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/Scripts/activate"
fi

cd "$PROJECT_DIR"
python -m pytest "$@"
