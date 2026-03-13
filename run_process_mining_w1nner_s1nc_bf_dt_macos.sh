#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_SCRIPT="${SCRIPT_DIR}/run_process_mining_projects_macos.sh"

usage() {
    cat <<'EOF_HELP'
Uso: ./run_process_mining_w1nner_s1nc_bf_dt_macos.sh [opcoes]

Wrapper explicito para gerar downstream, process mining e Bitbucket de:
  - W1NNER
  - S1NC
  - BEFINANCE
  - DATA&ANALYTICS

Opcoes:
  --out-dir PATH      Diretorio de saida para changelog detalhado
  --latest-dir PATH   Diretorio latest central
  --date-tag YYYYMMDD Tag de data para os arquivos
  --env-file PATH     Arquivo com variaveis JIRA_*
  --workers N         Numero de workers para exportacao
  --jql-extra JQL     Filtro JQL adicional repassado ao export Jira
  -h, --help          Mostra esta ajuda

Observacao:
  Este wrapper apenas delega para run_process_mining_projects_macos.sh,
  que hoje ja processa exatamente esse conjunto de quatro projetos.
EOF_HELP
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [[ ! -f "${BASE_SCRIPT}" ]]; then
    echo "Arquivo nao encontrado: ${BASE_SCRIPT}" >&2
    exit 1
fi

echo "Executando pipeline dedicado para W1NNER + S1NC + BEFINANCE + DATA&ANALYTICS..."
exec "${BASE_SCRIPT}" "$@"
