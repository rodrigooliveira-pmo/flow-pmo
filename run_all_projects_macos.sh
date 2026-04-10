#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_SCRIPT="${SCRIPT_DIR}/run_all_projects.py"

if [[ ! -f "${RUNNER_SCRIPT}" ]]; then
    echo "Arquivo nao encontrado: ${RUNNER_SCRIPT}" >&2
    exit 1
fi

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

exec "${PYTHON_BIN}" "${RUNNER_SCRIPT}" "$@"
