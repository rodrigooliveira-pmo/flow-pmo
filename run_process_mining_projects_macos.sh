#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${HOME}/Documents/Dados"
LATEST_DIR_DEFAULT="${HOME}/Documents/dados/latest"
LATEST_DIR="${FLOW_PMO_LATEST_DIR:-$LATEST_DIR_DEFAULT}"
DATE_TAG="$(date +%Y%m%d)"
ENV_FILE="${SCRIPT_DIR}/jira_env.txt"
WORKERS=8
JQL_EXTRA=""
PROCESS_MINING_FAILURES=()
BITBUCKET_FAILURES=()
JIRA_BITBUCKET_MIN_INTERVAL_MS="${FLOW_PMO_JIRA_BB_MIN_REQUEST_INTERVAL_MS:-750}"
BITBUCKET_EXPORT_WORKERS="${FLOW_PMO_BITBUCKET_EXPORT_WORKERS:-1}"
BITBUCKET_EXPORT_MIN_INTERVAL_MS="${FLOW_PMO_BITBUCKET_EXPORT_MIN_REQUEST_INTERVAL_MS:-900}"
DT_BOARD_JQL='project in (10290) AND issuetype in (10254, 10255,10258, 10257,Bug,Ad-hoc) ORDER BY Rank ASC'

usage() {
    cat <<'EOF_HELP'
Uso: ./run_process_mining_projects_macos.sh [opcoes]

Opcoes:
  --out-dir PATH      Diretorio de saida para changelog detalhado (padrao: ~/Documents/Dados)
  --latest-dir PATH   Diretorio latest central (padrao: ~/Documents/dados/latest)
  --date-tag YYYYMMDD Tag de data para os arquivos (padrao: data atual)
  --env-file PATH     Arquivo com variaveis JIRA_*
  --workers N         Numero de workers para exportacao (padrao: 8)
  --jql-extra JQL     Filtro JQL adicional repassado ao export Jira
  -h, --help          Mostra esta ajuda
EOF_HELP
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --out-dir)
            OUT_DIR="$2"
            shift 2
            ;;
        --latest-dir)
            LATEST_DIR="$2"
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
        --jql-extra)
            JQL_EXTRA="$2"
            shift 2
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

looks_like_windows_path() {
    [[ "$1" =~ ^[A-Za-z]:[\\/].* ]]
}

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

upload_to_s3() {
    local upload_dir="${LATEST_DIR}/latest-upload"
    if ! command -v aws >/dev/null 2>&1; then
        echo "Aviso: aws CLI nao encontrado. Upload S3 pulado."
        return 0
    fi
    local bucket="${AWS_S3_BUCKET:-w1-flow-pmo-dashboards}"
    local region="${AWS_DEFAULT_REGION:-us-east-1}"
    echo
    echo "Iniciando upload para S3 (bucket: ${bucket}, regiao: ${region})..."
    aws s3 cp "${upload_dir}/" "s3://${bucket}/" --recursive --region "${region}"
    echo "Upload S3 concluido."
}

import_env_file "$ENV_FILE"

if looks_like_windows_path "$LATEST_DIR"; then
    LATEST_DIR="$LATEST_DIR_DEFAULT"
fi

if [[ -z "${JIRA_BASE_URL:-}" || -z "${JIRA_EMAIL:-}" || -z "${JIRA_API_TOKEN:-}" ]]; then
    echo "Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN (ou preencha o arquivo $ENV_FILE) antes de executar."
    exit 1
fi

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

SCRIPT_PATH="${SCRIPT_DIR}/jira_to_pipeline_csv.py"
PROCESS_MINING_SCRIPT="${SCRIPT_DIR}/process_mining_jira.py"
BITBUCKET_SCRIPT="${SCRIPT_DIR}/bitbucket_export.py"
PROCESS_MINING_OUT_DIR="${SCRIPT_DIR}/artifacts/process_mining"
COPY_LATEST_UPLOAD_SCRIPT="${SCRIPT_DIR}/copy_latest_upload.py"

[[ -f "$SCRIPT_PATH" ]] || { echo "Arquivo nao encontrado: $SCRIPT_PATH"; exit 1; }
[[ -f "$PROCESS_MINING_SCRIPT" ]] || { echo "Arquivo nao encontrado: $PROCESS_MINING_SCRIPT"; exit 1; }
[[ -f "$BITBUCKET_SCRIPT" ]] || { echo "Arquivo nao encontrado: $BITBUCKET_SCRIPT"; exit 1; }
[[ -f "$COPY_LATEST_UPLOAD_SCRIPT" ]] || { echo "Arquivo nao encontrado: $COPY_LATEST_UPLOAD_SCRIPT"; exit 1; }

mkdir -p "$OUT_DIR"
mkdir -p "$LATEST_DIR"
mkdir -p "$PROCESS_MINING_OUT_DIR"

PROJECT_KEYS=("W1NNR" "S1NC" "BF" "DT")
PROJECT_PREFIXES=("w1nner-downstream" "s1nc-downstream" "befinance-downstream" "dataanalytics-downstream")
PROCESS_MINING_PREFIXES=("w1nner-process-mining" "s1nc-process-mining" "befinance-process-mining" "dataanalytics-process-mining")

get_project_custom_jql() {
    local key="$1"
    case "${key}" in
        DT) printf '%s\n' "${DT_BOARD_JQL}" ;;
        *) printf '\n' ;;
    esac
}

echo "Iniciando exportacao dedicada de process mining..."
echo "Base URL: ${JIRA_BASE_URL}"
echo "Saida changelog: ${OUT_DIR}"
echo "Saida process mining: ${PROCESS_MINING_OUT_DIR}"
echo "Data: ${DATE_TAG}"
if [[ -n "${JQL_EXTRA}" ]]; then
    echo "Filtro JQL adicional: ${JQL_EXTRA}"
fi

ORIGINAL_JIRA_STATUS_MAP="${JIRA_STATUS_MAP-}"
if [[ -n "${JIRA_STATUS_MAP-}" ]]; then
    echo "Ignorando JIRA_STATUS_MAP global durante exportacao downstream para process mining (fluxo por projeto habilitado)."
fi
unset JIRA_STATUS_MAP
export JIRA_IGNORE_STATUS_MAP=1

for i in "${!PROJECT_KEYS[@]}"; do
    key="${PROJECT_KEYS[$i]}"
    prefix="${PROJECT_PREFIXES[$i]}"
    process_mining_prefix="${PROCESS_MINING_PREFIXES[$i]}"
    detailed_changelog_out="${OUT_DIR}/${prefix}-${DATE_TAG}-data_detailed_changelog.csv"
    detailed_changelog_latest="${OUT_DIR}/${prefix}-latest-data_detailed_changelog.csv"

    echo
    echo "Projeto: ${key}"
    echo "Changelog detalhado: ${detailed_changelog_out}"
    project_jql="$(get_project_custom_jql "$key")"

    jira_cmd=(
        "$PYTHON_BIN" "$SCRIPT_PATH"
        --projects "$key"
        --out "${OUT_DIR}/${prefix}-${DATE_TAG}-data.csv"
        --env-file "$ENV_FILE"
        --workers "$WORKERS"
        --detailed-changelog-out "$detailed_changelog_out"
        --skip-devexecutor-bitbucket
    )
    if [[ -n "${project_jql}" ]]; then
        jira_cmd+=(--jql "$project_jql")
        echo "Usando JQL dedicada do projeto: ${project_jql}"
        if [[ -n "${JQL_EXTRA}" ]]; then
            echo "Aviso: --jql-extra global foi ignorado para ${key} porque este projeto usa uma JQL completa dedicada." >&2
        fi
    elif [[ -n "${JQL_EXTRA}" ]]; then
        jira_cmd+=(--jql-extra "$JQL_EXTRA")
    fi

    "${jira_cmd[@]}"

    if [[ -f "$detailed_changelog_out" ]]; then
        cp -f "$detailed_changelog_out" "$detailed_changelog_latest"
        echo "Arquivo latest atualizado: ${detailed_changelog_latest}"
        publish_latest_artifact "$detailed_changelog_latest" "$LATEST_DIR"
    fi

    echo "Gerando process mining para ${key}..."
    if "$PYTHON_BIN" "$PROCESS_MINING_SCRIPT" --input "$detailed_changelog_out" --out-dir "$PROCESS_MINING_OUT_DIR" --project "$key" --prefix "$process_mining_prefix"; then
        sync_latest_artifacts_from_out_dir "$PROCESS_MINING_OUT_DIR" "$LATEST_DIR"
    else
        status=$?
        echo "Aviso: process mining falhou para ${key} (exit ${status})." >&2
        PROCESS_MINING_FAILURES+=("${key}:exit-${status}")
    fi

    echo "Exportando Bitbucket para ${key}..."
    if "$PYTHON_BIN" "$BITBUCKET_SCRIPT" \
        --project "$key" \
        --out-dir "$OUT_DIR" \
        --workers "$BITBUCKET_EXPORT_WORKERS" \
        --min-request-interval-ms "$BITBUCKET_EXPORT_MIN_INTERVAL_MS"; then
        for suffix in commits pullrequests pipelines; do
            bitbucket_file="${OUT_DIR}/${prefix%-downstream}_${suffix}.csv"
            if [[ -f "$bitbucket_file" ]]; then
                publish_latest_artifact "$bitbucket_file" "$LATEST_DIR"
            fi
        done
    else
        status=$?
        echo "Aviso: exportacao Bitbucket falhou para ${key} (exit ${status})." >&2
        BITBUCKET_FAILURES+=("${key}:exit-${status}")
    fi
done

if [[ -n "${ORIGINAL_JIRA_STATUS_MAP}" ]]; then
    export JIRA_STATUS_MAP="${ORIGINAL_JIRA_STATUS_MAP}"
fi
unset JIRA_IGNORE_STATUS_MAP

refresh_latest_upload_package

export FLOW_PMO_LATEST_DIR="$LATEST_DIR"
upload_to_s3

echo
echo "Exportacao dedicada de process mining concluida."
if [[ ${#PROCESS_MINING_FAILURES[@]} -gt 0 ]]; then
    echo "Avisos Process Mining: ${PROCESS_MINING_FAILURES[*]}" >&2
fi
if [[ ${#BITBUCKET_FAILURES[@]} -gt 0 ]]; then
    echo "Avisos Bitbucket: ${BITBUCKET_FAILURES[*]}" >&2
fi
