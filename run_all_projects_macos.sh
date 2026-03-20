#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${HOME}/Documents/Dados"
LATEST_DIR_DEFAULT="${HOME}/Documents/dados/latest"
LATEST_DIR="${FLOW_PMO_LATEST_DIR:-$LATEST_DIR_DEFAULT}"
DATE_TAG="$(date +%Y%m%d)"
ENV_FILE="${SCRIPT_DIR}/jira_env.txt"
WORKERS=8
RUN_PORTFOLIO_EXPORT=true
RUN_METRICS=true
OPEN_DASHBOARD=true
RUN_DETAILED_CHANGELOG_EXPORT=false

usage() {
    cat <<'EOF_HELP'
Uso: ./run_all_projects_macos.sh [opcoes]

Opcoes:
  --out-dir PATH            Diretorio de saida (padrao: ~/Documents/Dados)
  --date-tag YYYYMMDD       Tag de data para os arquivos (padrao: data atual)
  --env-file PATH           Arquivo com variaveis JIRA_*
  --workers N               Numero de workers para exportacao (padrao: 8)
  --run-portfolio-export    Executa exportacao de portfolio (padrao)
  --no-run-portfolio-export Nao executa exportacao de portfolio
  --run-metrics             Executa metricas (padrao)
  --no-run-metrics          Nao executa metricas
  --open-dashboard          Abre dashboard no navegador (padrao)
  --no-open-dashboard       Nao abre dashboard
  --run-detailed-changelog-export    Gera CSV de changelog detalhado real por projeto
  --no-run-detailed-changelog-export Nao gera CSV de changelog detalhado (padrao)
  -h, --help                Mostra esta ajuda
EOF_HELP
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --out-dir)
            OUT_DIR="$2"
            shift 2
            ;;
        --date-tag)
            DATE_TAG="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --run-portfolio-export)
            RUN_PORTFOLIO_EXPORT=true
            shift
            ;;
        --no-run-portfolio-export)
            RUN_PORTFOLIO_EXPORT=false
            shift
            ;;
        --run-metrics)
            RUN_METRICS=true
            shift
            ;;
        --no-run-metrics)
            RUN_METRICS=false
            shift
            ;;
        --open-dashboard)
            OPEN_DASHBOARD=true
            shift
            ;;
        --no-open-dashboard)
            OPEN_DASHBOARD=false
            shift
            ;;
        --run-detailed-changelog-export)
            RUN_DETAILED_CHANGELOG_EXPORT=true
            shift
            ;;
        --no-run-detailed-changelog-export)
            RUN_DETAILED_CHANGELOG_EXPORT=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Opcao desconhecida: $1"
            usage
            exit 1
            ;;
    esac
done

import_env_file() {
    local path="$1"
    [[ -f "$path" ]] || return 0

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue

        local key="${line%%=*}"
        local value="${line#*=}"
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"

        if [[ -n "$key" && -n "$value" && -z "${!key:-}" ]]; then
            export "$key=$value"
        fi
    done < "$path"
}

import_env_file "$ENV_FILE"

looks_like_windows_path() {
    [[ "$1" =~ ^[A-Za-z]:[\\/].* ]]
}

if looks_like_windows_path "$LATEST_DIR"; then
    LATEST_DIR="$LATEST_DIR_DEFAULT"
fi

publish_latest_artifact() {
    local source_file="$1"
    local latest_dir="$2"
    [[ -f "$source_file" ]] || return 0
    local target_file="${latest_dir}/$(basename "$source_file")"
    cp -f "$source_file" "$target_file"
    echo "Alias latest publicado em: ${target_file}"
}

sync_latest_artifacts_from_out_dir() {
    local source_dir="$1"
    local latest_dir="$2"
    find "$source_dir" -maxdepth 1 -type f -iname "*latest*" -print0 | while IFS= read -r -d '' file; do
        publish_latest_artifact "$file" "$latest_dir"
    done
}

refresh_latest_upload_package() {
    "$PYTHON_BIN" "$COPY_LATEST_UPLOAD_SCRIPT" \
        --source-dir "$LATEST_DIR" \
        --dest-dir "${LATEST_DIR}/latest-upload" \
        --clean-dest
}

if [[ -z "${JIRA_BASE_URL:-}" || -z "${JIRA_EMAIL:-}" || -z "${JIRA_API_TOKEN:-}" ]]; then
    echo "Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN (ou preencha o arquivo $ENV_FILE) antes de executar."
    exit 1
fi

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

SCRIPT_PATH="${SCRIPT_DIR}/jira_to_pipeline_csv.py"
PORTFOLIO_SCRIPT="${SCRIPT_DIR}/jira_portfolio_to_csv.py"
METRICS_SCRIPT="${SCRIPT_DIR}/dash_board_metricas.py"
DASHBOARD_SCRIPT="${SCRIPT_DIR}/dashboard_full.py"
COPY_LATEST_UPLOAD_SCRIPT="${SCRIPT_DIR}/copy_latest_upload.py"

[[ -f "$SCRIPT_PATH" ]] || { echo "Arquivo nao encontrado: $SCRIPT_PATH"; exit 1; }
[[ -f "$COPY_LATEST_UPLOAD_SCRIPT" ]] || { echo "Arquivo nao encontrado: $COPY_LATEST_UPLOAD_SCRIPT"; exit 1; }
mkdir -p "$OUT_DIR"
mkdir -p "$LATEST_DIR"

PROJECT_KEYS=("W1NNR" "S1NC" "BF" "DT")
PROJECT_PREFIXES=("w1nner-downstream" "s1nc-downstream" "befinance-downstream" "dataanalytics-downstream")

export_project_dashboard_artifacts() {
    local key="$1"
    local prefix="$2"
    local out_file="${OUT_DIR}/${prefix}-${DATE_TAG}-data.csv"
    local detailed_changelog_out="${OUT_DIR}/${prefix}-${DATE_TAG}-data_detailed_changelog.csv"

    echo
    echo "Projeto: ${key}"
    echo "Arquivo: ${out_file}"

    local export_cmd=(
        "$PYTHON_BIN" "$SCRIPT_PATH"
        --projects "$key"
        --out "$out_file"
        --env-file "$ENV_FILE"
        --workers "$WORKERS"
    )

    if [[ "$RUN_DETAILED_CHANGELOG_EXPORT" == true ]]; then
        export_cmd+=(--detailed-changelog-out "$detailed_changelog_out")
        echo "Changelog detalhado: ${detailed_changelog_out}"
    fi

    "${export_cmd[@]}"

    local downstream_latest="${OUT_DIR}/${prefix}-latest-data.csv"
    if [[ -f "$out_file" ]]; then
        cp -f "$out_file" "$downstream_latest"
        echo "Arquivo latest atualizado: ${downstream_latest}"
        publish_latest_artifact "$downstream_latest" "$LATEST_DIR"
    fi

    local bottleneck_out="${OUT_DIR}/${prefix}-${DATE_TAG}-data_bottlenecks.csv"
    local bottleneck_latest="${OUT_DIR}/${prefix}-latest-data_bottlenecks.csv"
    if [[ -f "$bottleneck_out" ]]; then
        cp -f "$bottleneck_out" "$bottleneck_latest"
        echo "Arquivo latest atualizado: ${bottleneck_latest}"
        publish_latest_artifact "$bottleneck_latest" "$LATEST_DIR"
    fi

    if [[ "$RUN_DETAILED_CHANGELOG_EXPORT" == true ]]; then
        local detailed_changelog_latest="${OUT_DIR}/${prefix}-latest-data_detailed_changelog.csv"
        if [[ -f "$detailed_changelog_out" ]]; then
            cp -f "$detailed_changelog_out" "$detailed_changelog_latest"
            echo "Arquivo latest atualizado: ${detailed_changelog_latest}"
            publish_latest_artifact "$detailed_changelog_latest" "$LATEST_DIR"
        fi
    fi
}

echo "Iniciando exportacao Jira -> CSV..."
echo "Base URL: ${JIRA_BASE_URL}"
echo "Saida: ${OUT_DIR}"
echo "Data: ${DATE_TAG}"

# The downstream exporter now resolves workflow by project/type.
# Ignore global JIRA_STATUS_MAP here to avoid forcing a single flow for all projects.
ORIGINAL_JIRA_STATUS_MAP="${JIRA_STATUS_MAP-}"
if [[ -n "${JIRA_STATUS_MAP-}" ]]; then
    echo "Ignorando JIRA_STATUS_MAP global durante exportacao downstream (fluxo por projeto habilitado)."
fi
unset JIRA_STATUS_MAP
export JIRA_IGNORE_STATUS_MAP=1

for i in "${!PROJECT_KEYS[@]}"; do
    key="${PROJECT_KEYS[$i]}"
    prefix="${PROJECT_PREFIXES[$i]}"
    export_project_dashboard_artifacts "$key" "$prefix"
done

if [[ -n "${ORIGINAL_JIRA_STATUS_MAP}" ]]; then
    export JIRA_STATUS_MAP="${ORIGINAL_JIRA_STATUS_MAP}"
fi
unset JIRA_IGNORE_STATUS_MAP

echo
echo "Exportacoes concluidas com sucesso."

if [[ "$RUN_PORTFOLIO_EXPORT" == true ]]; then
    [[ -f "$PORTFOLIO_SCRIPT" ]] || { echo "Arquivo nao encontrado: $PORTFOLIO_SCRIPT"; exit 1; }
    portfolio_out="${OUT_DIR}/portfolio-bt-ns-${DATE_TAG}-data.csv"
    echo
    echo "Exportando CSV de portfolio (BT/NS)..."
    echo "Arquivo: ${portfolio_out}"

    "$PYTHON_BIN" "$PORTFOLIO_SCRIPT" --projects BT NS --out "$portfolio_out" --env-file "$ENV_FILE"
    cp -f "$portfolio_out" "${OUT_DIR}/portfolio-bt-ns-latest-data.csv"
    echo "Arquivo latest atualizado: ${OUT_DIR}/portfolio-bt-ns-latest-data.csv"
    publish_latest_artifact "${OUT_DIR}/portfolio-bt-ns-latest-data.csv" "$LATEST_DIR"
fi

if [[ "$RUN_METRICS" == true ]]; then
    [[ -f "$METRICS_SCRIPT" ]] || { echo "Arquivo nao encontrado: $METRICS_SCRIPT"; exit 1; }
    echo
    echo "Executando processamento de metricas..."
    export DATA_FOLDER="$OUT_DIR"
    export FLOW_PMO_DATA_DIR="$OUT_DIR"
    "$PYTHON_BIN" "$METRICS_SCRIPT"
    sync_latest_artifacts_from_out_dir "$OUT_DIR" "$LATEST_DIR"
fi

refresh_latest_upload_package

if [[ "$OPEN_DASHBOARD" == true ]]; then
    [[ -f "$DASHBOARD_SCRIPT" ]] || { echo "Arquivo nao encontrado: $DASHBOARD_SCRIPT"; exit 1; }
    echo
    echo "Iniciando dashboard web..."
    (
        cd "$SCRIPT_DIR"
        "$PYTHON_BIN" "$DASHBOARD_SCRIPT" >/dev/null 2>&1 &
    )
    sleep 6
    open "http://127.0.0.1:8050" >/dev/null 2>&1 || true
    echo "Dashboard aberto em http://127.0.0.1:8050"
fi
