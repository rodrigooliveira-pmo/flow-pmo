#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import webbrowser
from contextlib import contextmanager
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
IS_WINDOWS = platform.system() == "Windows"
DEFAULT_OUT_DIR = (
    Path(r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados")
    if IS_WINDOWS
    else Path.home() / "Documents" / "Dados"
)
DEFAULT_LATEST_DIR = (
    Path(r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest")
    if IS_WINDOWS
    else Path.home() / "Documents" / "dados" / "latest"
)
DT_BOARD_JQL = "project in (10290) AND issuetype in (10254, 10255,10258, 10257,Bug,Ad-hoc) ORDER BY Rank ASC"


def looks_like_windows_path(value: str) -> bool:
    return len(value) >= 3 and value[1] == ":" and value[2] in ("\\", "/")


def load_env_file(path: Path, override_existing: bool = True) -> None:
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value:
            continue

        if override_existing or key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo de exportacao Jira, metricas e dashboard."
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--date-tag")
    parser.add_argument("--env-file", default=str(SCRIPT_DIR / "jira_env.txt"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--run-detailed-changelog-export",
        dest="run_detailed_changelog_export",
        action="store_true",
    )
    parser.add_argument(
        "--no-run-detailed-changelog-export",
        dest="run_detailed_changelog_export",
        action="store_false",
    )
    parser.set_defaults(run_detailed_changelog_export=False)
    parser.add_argument(
        "--run-portfolio",
        "--run-portfolio-export",
        dest="portfolio",
        action="store_true",
    )
    parser.add_argument(
        "--no-run-portfolio",
        "--no-run-portfolio-export",
        dest="portfolio",
        action="store_false",
    )
    parser.add_argument(
        "--run-gmud-coverage",
        dest="gmud_coverage",
        action="store_true",
    )
    parser.add_argument(
        "--no-run-gmud-coverage",
        dest="gmud_coverage",
        action="store_false",
    )
    parser.add_argument(
        "--run-capex-export",
        dest="capex_export",
        action="store_true",
    )
    parser.add_argument(
        "--no-run-capex-export",
        dest="capex_export",
        action="store_false",
    )
    parser.add_argument("--run-metrics", dest="metrics", action="store_true")
    parser.add_argument("--no-run-metrics", dest="metrics", action="store_false")
    parser.add_argument(
        "--run-four-ps-kanban",
        dest="four_ps_kanban",
        action="store_true",
    )
    parser.add_argument(
        "--no-run-four-ps-kanban",
        dest="four_ps_kanban",
        action="store_false",
    )
    parser.add_argument(
        "--four-ps-history-months",
        type=int,
        default=6,
        help="Meses de historico de entregas concluidas para o 4Ps (padrao: 6).",
    )
    parser.add_argument(
        "--run-process-mining",
        dest="process_mining",
        action="store_true",
        help="Executa process mining para W1NNR, S1NC, BF e DT (requer --run-detailed-changelog-export).",
    )
    parser.add_argument(
        "--no-run-process-mining",
        dest="process_mining",
        action="store_false",
        help="Pula o process mining.",
    )
    parser.add_argument(
        "--run-s3-upload",
        dest="s3_upload",
        action="store_true",
        help="Faz upload dos artefatos latest-upload para AWS S3 (requer aws CLI e credenciais AWS).",
    )
    parser.add_argument(
        "--no-run-s3-upload",
        dest="s3_upload",
        action="store_false",
        help="Pula o upload para S3.",
    )
    parser.add_argument(
        "--run-open-dashboard",
        "--open-dashboard",
        dest="open_dashboard",
        action="store_true",
    )
    parser.add_argument(
        "--no-run-open-dashboard",
        "--no-open-dashboard",
        dest="open_dashboard",
        action="store_false",
    )
    parser.set_defaults(
        portfolio=True,
        gmud_coverage=True,
        capex_export=True,
        metrics=True,
        four_ps_kanban=True,
        process_mining=False,
        s3_upload=True,
        open_dashboard=True,
    )
    return parser.parse_args()


def get_date_tag() -> str:
    return time.strftime("%Y%m%d")


def get_capex_window() -> tuple[str, str]:
    year = time.strftime("%Y")
    return f"{year}-01-01", time.strftime("%Y-%m-%d")


def ensure_required_env(env_file: Path) -> None:
    missing = [
        name
        for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        if not os.environ.get(name)
    ]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"Defina {names} (ou preencha o arquivo {env_file}) antes de executar."
        )


def resolve_latest_dir() -> Path:
    raw = os.environ.get("FLOW_PMO_LATEST_DIR")
    if raw:
        if IS_WINDOWS or not looks_like_windows_path(raw):
            return Path(raw)
    return DEFAULT_LATEST_DIR


def ensure_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")


def publish_latest_artifact(source_path: Path, latest_dir: Path) -> None:
    if not source_path.is_file():
        return
    latest_dir.mkdir(parents=True, exist_ok=True)
    target_path = latest_dir / source_path.name
    shutil.copy2(source_path, target_path)
    print(f"Alias latest publicado em: {target_path}")


def sync_latest_artifacts_from_out_dir(source_dir: Path, latest_dir: Path) -> None:
    for path in source_dir.iterdir():
        if path.is_file() and "latest" in path.name.lower():
            publish_latest_artifact(path, latest_dir)


def run_command(args: list[str], check: bool = True) -> int:
    completed = subprocess.run(args, cwd=str(SCRIPT_DIR))
    if check and completed.returncode != 0:
        raise RuntimeError(f"Falha ao executar: {' '.join(args)}")
    return completed.returncode


@contextmanager
def temporary_env(updates: dict[str, str | None]):
    original = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def get_project_bitbucket_repos(project_key: str) -> str:
    project_key = project_key.upper()
    if project_key in {"W1NNR", "S1NC"}:
        return "w1nner"
    if project_key == "BF":
        return (
            "be-finance-api,be-finance-web,be-finance-lambda,"
            "be-finance-diagnostic-api,be-finance-diagnostic-web,be-finance-dev"
        )
    if project_key == "DT":
        return (
            "d-a-analysis,w1-data-toolbox,automacao-rfv,apuracao-indicadores-mensais,"
            "api-resumo-e-insights,c3po-automation"
        )
    return ""


def export_downstream_projects(
    out_dir: Path,
    latest_dir: Path,
    env_file: Path,
    date_tag: str,
    workers: int,
    run_detailed_changelog_export: bool,
) -> None:
    script_path = SCRIPT_DIR / "jira_to_pipeline_csv.py"
    ensure_file(script_path)

    jira_bitbucket_commit_depth = os.environ.get("FLOW_PMO_JIRA_BB_COMMIT_DEPTH", "250")
    jira_bitbucket_min_interval_ms = os.environ.get(
        "FLOW_PMO_JIRA_BB_MIN_REQUEST_INTERVAL_MS", "750"
    )

    projects = [
        {"key": "W1NNR", "prefix": "w1nner-downstream"},
        {"key": "S1NC", "prefix": "s1nc-downstream"},
        {"key": "BF", "prefix": "befinance-downstream"},
        {"key": "DT", "prefix": "dataanalytics-downstream", "jql": DT_BOARD_JQL},
    ]

    print("Iniciando exportacao Jira -> CSV...")
    print(f"Base URL: {os.environ.get('JIRA_BASE_URL', '')}")
    print(f"Saida: {out_dir}")
    print(f"Data: {date_tag}")

    original_status_map = os.environ.get("JIRA_STATUS_MAP")
    if original_status_map:
        print(
            "Ignorando JIRA_STATUS_MAP global durante exportacao downstream "
            "(fluxo por projeto habilitado)."
        )

    env_updates = {
        "JIRA_STATUS_MAP": None,
        "JIRA_IGNORE_STATUS_MAP": "1",
        "BB_REPOS": None,
        "BB_REPO": None,
        "BB_COMMIT_DEPTH": None,
        "BB_MIN_REQUEST_INTERVAL_MS": None,
    }

    with temporary_env(env_updates):
        for project in projects:
            key = project["key"]
            prefix = project["prefix"]
            out_file = out_dir / f"{prefix}-{date_tag}-data.csv"
            detailed_changelog_out = (
                out_dir / f"{prefix}-{date_tag}-data_detailed_changelog.csv"
            )
            print()
            print(f"Projeto: {key}")
            print(f"Arquivo: {out_file}")

            project_repos = get_project_bitbucket_repos(key)
            if project_repos:
                os.environ["BB_REPOS"] = project_repos
                os.environ["BB_REPO"] = project_repos.split(",")[0]
                os.environ["BB_COMMIT_DEPTH"] = jira_bitbucket_commit_depth
                os.environ["BB_MIN_REQUEST_INTERVAL_MS"] = (
                    jira_bitbucket_min_interval_ms
                )
                print(
                    "Bitbucket escopado para o projeto: "
                    f"{os.environ['BB_REPOS']} | depth={os.environ['BB_COMMIT_DEPTH']} "
                    f"| intervalo={os.environ['BB_MIN_REQUEST_INTERVAL_MS']}ms"
                )

            export_args = [
                sys.executable,
                str(script_path),
                "--projects",
                key,
                "--out",
                str(out_file),
                "--env-file",
                str(env_file),
                "--workers",
                str(workers),
                "--skip-devexecutor-bitbucket",
            ]

            project_jql = project.get("jql")
            if project_jql:
                export_args.extend(["--jql", project_jql])
                print(f"Usando JQL dedicada do projeto: {project_jql}")

            if run_detailed_changelog_export:
                export_args.extend(
                    ["--detailed-changelog-out", str(detailed_changelog_out)]
                )
                print(f"Changelog detalhado: {detailed_changelog_out}")

            run_command(export_args)

            downstream_latest = out_dir / f"{prefix}-latest-data.csv"
            if out_file.is_file():
                shutil.copy2(out_file, downstream_latest)
                print(f"Arquivo latest atualizado: {downstream_latest}")
                publish_latest_artifact(downstream_latest, latest_dir)

            bottleneck_out = out_dir / f"{prefix}-{date_tag}-data_bottlenecks.csv"
            bottleneck_latest = out_dir / f"{prefix}-latest-data_bottlenecks.csv"
            if bottleneck_out.is_file():
                shutil.copy2(bottleneck_out, bottleneck_latest)
                print(f"Arquivo latest atualizado: {bottleneck_latest}")
                publish_latest_artifact(bottleneck_latest, latest_dir)
            else:
                print(f"Aviso: {bottleneck_out.name} ausente — bottleneck nao gerado para {prefix}.")

            if run_detailed_changelog_export and detailed_changelog_out.is_file():
                detailed_changelog_latest = (
                    out_dir / f"{prefix}-latest-data_detailed_changelog.csv"
                )
                shutil.copy2(detailed_changelog_out, detailed_changelog_latest)
                print(f"Arquivo latest atualizado: {detailed_changelog_latest}")
                publish_latest_artifact(detailed_changelog_latest, latest_dir)

    print()
    print("Exportacoes concluidas com sucesso.")


def export_portfolio(out_dir: Path, latest_dir: Path, env_file: Path, date_tag: str) -> None:
    portfolio_script = SCRIPT_DIR / "jira_portfolio_to_csv.py"
    ensure_file(portfolio_script)

    portfolio_out = out_dir / f"portfolio-bt-ns-{date_tag}-data.csv"
    portfolio_latest = out_dir / "portfolio-bt-ns-latest-data.csv"

    print()
    print("Exportando CSV de portfolio (BT/NS)...")
    print(f"Arquivo: {portfolio_out}")

    run_command(
        [
            sys.executable,
            str(portfolio_script),
            "--projects",
            "BT",
            "NS",
            "--out",
            str(portfolio_out),
            "--env-file",
            str(env_file),
        ]
    )

    shutil.copy2(portfolio_out, portfolio_latest)
    print(f"Arquivo latest atualizado: {portfolio_latest}")
    publish_latest_artifact(portfolio_latest, latest_dir)


def run_gmud_coverage(
    out_dir: Path, latest_dir: Path, env_file: Path, date_tag: str
) -> None:
    gmud_coverage_script = SCRIPT_DIR / "jira_gmud_coverage.py"
    ensure_file(gmud_coverage_script)

    gmud_summary_out = out_dir / f"gmud-coverage-index-{date_tag}.csv"
    gmud_weekly_out = out_dir / f"gmud-coverage-weekly-{date_tag}.csv"
    gmud_items_out = out_dir / f"gmud-coverage-items-{date_tag}.csv"
    gmud_summary_latest = out_dir / "gmud-coverage-index-latest.csv"
    gmud_weekly_latest = out_dir / "gmud-coverage-weekly-latest.csv"
    gmud_items_latest = out_dir / "gmud-coverage-items-latest.csv"
    downstream_latest_files = [
        out_dir / "w1nner-downstream-latest-data.csv",
        out_dir / "s1nc-downstream-latest-data.csv",
        out_dir / "befinance-downstream-latest-data.csv",
        out_dir / "dataanalytics-downstream-latest-data.csv",
    ]
    downstream_latest_files = [path for path in downstream_latest_files if path.is_file()]
    portfolio_latest = out_dir / "portfolio-bt-ns-latest-data.csv"
    gmud_chg_jql = os.environ.get(
        "FLOW_PMO_GMUD_CHG_JQL", "project = CHG ORDER BY status ASC, created DESC"
    )

    if not downstream_latest_files or not portfolio_latest.is_file():
        print(
            "Aviso: pulando cobertura GMUD porque os artefatos latest de "
            "downstream/portfolio ainda nao estao disponiveis."
        )
        return

    print()
    print("Calculando cobertura GMUD x vazao Jira...")
    print(f"JQL CHG: {gmud_chg_jql}")

    gmud_args = [
        sys.executable,
        str(gmud_coverage_script),
        "--portfolio-csv",
        str(portfolio_latest),
        "--summary-out",
        str(gmud_summary_out),
        "--weekly-out",
        str(gmud_weekly_out),
        "--items-out",
        str(gmud_items_out),
        "--chg-jql",
        gmud_chg_jql,
        "--env-file",
        str(env_file),
        "--downstream-csv",
    ] + [str(path) for path in downstream_latest_files]

    if run_command(gmud_args, check=False) != 0:
        print("Aviso: falha no calculo de cobertura GMUD. O restante do pipeline seguira sem bloquear.")
        return

    shutil.copy2(gmud_summary_out, gmud_summary_latest)
    shutil.copy2(gmud_weekly_out, gmud_weekly_latest)
    shutil.copy2(gmud_items_out, gmud_items_latest)
    print(
        "Arquivos latest atualizados: "
        f"{gmud_summary_latest} | {gmud_weekly_latest} | {gmud_items_latest}"
    )
    publish_latest_artifact(gmud_summary_latest, latest_dir)
    publish_latest_artifact(gmud_weekly_latest, latest_dir)
    publish_latest_artifact(gmud_items_latest, latest_dir)


def export_capex(out_dir: Path, latest_dir: Path, env_file: Path, workers: int) -> None:
    capex_script = SCRIPT_DIR / "jira_capex_monthly.py"
    ensure_file(capex_script)

    capex_start, capex_end = get_capex_window()
    capex_raw_latest = out_dir / "capex-raw-latest.csv"
    capex_summary_latest = out_dir / "capex-summary-latest.csv"
    capex_xlsx_latest = out_dir / "capex-latest.xlsx"

    print()
    print("Exportando CAPEX real por worklog...")
    print(f"Janela CAPEX: {capex_start} -> {capex_end}")
    print(f"Arquivos: {capex_raw_latest} | {capex_summary_latest}")

    capex_args = [
        sys.executable,
        str(capex_script),
        "--projects",
        "W1NNR",
        "S1NC",
        "BF",
        "DT",
        "BT",
        "NS",
        "--date-from",
        capex_start,
        "--date-to",
        capex_end,
        "--out",
        str(capex_raw_latest),
        "--summary-out",
        str(capex_summary_latest),
        "--xlsx-out",
        str(capex_xlsx_latest),
        "--env-file",
        str(env_file),
        "--workers",
        str(workers),
    ]

    if run_command(capex_args, check=False) != 0:
        print("Aviso: falha na exportacao CAPEX por worklog. O restante do pipeline seguira sem bloquear.")
        return

    publish_latest_artifact(capex_raw_latest, latest_dir)
    publish_latest_artifact(capex_summary_latest, latest_dir)
    publish_latest_artifact(capex_xlsx_latest, latest_dir)


def export_four_ps_kanban(
    latest_dir: Path,
    env_file: Path,
    history_months: int = 6,
) -> None:
    """Exporta boards Kanban 4Ps para CSV e publica no latest-upload."""
    kanban_script = SCRIPT_DIR / "jira" / "four_ps_kanban_export.py"
    ensure_file(kanban_script)

    kanban_out = latest_dir / "four_ps_kanban.csv"

    print()
    print("Exportando boards Kanban 4Ps (in_progress / next_steps / done)...")
    print(f"Arquivo: {kanban_out}")
    print(f"Historico de entregas: {history_months} meses")

    kanban_args = [
        sys.executable,
        str(kanban_script),
        "--out",
        str(kanban_out),
        "--env-file",
        str(env_file),
        "--history-months",
        str(history_months),
    ]

    if run_command(kanban_args, check=False) != 0:
        print(
            "Aviso: falha na exportacao dos boards Kanban 4Ps. "
            "O restante do pipeline seguira sem bloquear."
        )
        return

    publish_latest_artifact(kanban_out, latest_dir / "latest-upload")
    print(f"four_ps_kanban.csv publicado em: {latest_dir / 'latest-upload' / 'four_ps_kanban.csv'}")


def run_metrics(out_dir: Path, latest_dir: Path) -> None:
    metrics_script = SCRIPT_DIR / "dash_board_metricas.py"
    ensure_file(metrics_script)

    print()
    print("Executando processamento de metricas...")
    with temporary_env({"DATA_FOLDER": str(out_dir), "FLOW_PMO_DATA_DIR": str(out_dir)}):
        run_command([sys.executable, str(metrics_script)])
    sync_latest_artifacts_from_out_dir(out_dir, latest_dir)


_PM_PROJECTS = [
    {
        "key": "W1NNR",
        "changelog": "w1nner-downstream-latest-data_detailed_changelog.csv",
        "pm_prefix": "w1nner-process-mining",
        "project_arg": "W1NNR",
    },
    {
        "key": "S1NC",
        "changelog": "s1nc-downstream-latest-data_detailed_changelog.csv",
        "pm_prefix": "s1nc-process-mining",
        "project_arg": "S1NC",
    },
    {
        "key": "BF",
        "changelog": "befinance-downstream-latest-data_detailed_changelog.csv",
        "pm_prefix": "befinance-process-mining",
        "project_arg": "BF",
    },
    {
        "key": "DT",
        "changelog": "dataanalytics-downstream-latest-data_detailed_changelog.csv",
        "pm_prefix": "dataanalytics-process-mining",
        "project_arg": "DT",
    },
]


def run_process_mining(out_dir: Path, latest_dir: Path) -> None:
    """Executa process mining para cada projeto e publica os xlsx latest."""
    pm_script = SCRIPT_DIR / "process_mining_jira.py"
    ensure_file(pm_script)

    pm_out_dir = out_dir / "process_mining"
    pm_out_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("Executando process mining por projeto...")

    for proj in _PM_PROJECTS:
        changelog_csv = out_dir / proj["changelog"]
        if not changelog_csv.is_file():
            print(
                f"Aviso: changelog detalhado ausente para {proj['key']} "
                f"({changelog_csv.name}). Execute com --run-detailed-changelog-export. Pulando."
            )
            continue

        pm_prefix = proj["pm_prefix"]
        print()
        print(f"Process mining: {proj['key']} -> {pm_prefix}")

        rc = run_command(
            [
                sys.executable,
                str(pm_script),
                "--input", str(changelog_csv),
                "--out-dir", str(pm_out_dir),
                "--project", proj["project_arg"],
                "--prefix", pm_prefix,
            ],
            check=False,
        )

        if rc != 0:
            print(f"Aviso: falha no process mining para {proj['key']}. Continuando.")
            continue

        pm_latest_xlsx = pm_out_dir / f"{pm_prefix}-latest.xlsx"
        if pm_latest_xlsx.is_file():
            publish_latest_artifact(pm_latest_xlsx, latest_dir)
        else:
            print(f"Aviso: {pm_latest_xlsx.name} não encontrado após execução.")


def upload_to_s3(upload_dir: Path) -> None:
    """Upload all files in *upload_dir* to AWS S3 using the aws CLI.

    Credentials are resolved by the AWS credential chain:
      - env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
      - ~/.aws/credentials
      - IAM instance role

    Optional env vars
    -----------------
    AWS_S3_BUCKET       target bucket (default: w1-flow-pmo-dashboards)
    AWS_DEFAULT_REGION  bucket region  (default: us-east-1)
    """
    if not shutil.which("aws"):
        print("Aviso: aws CLI nao encontrado. Instale em https://aws.amazon.com/cli/. Upload S3 pulado.")
        return

    if not upload_dir.is_dir():
        print(f"Aviso: diretorio de upload nao encontrado: {upload_dir}. Pulando S3.")
        return

    bucket = os.environ.get("AWS_S3_BUCKET", "w1-flow-pmo-dashboards").strip()
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1").strip()

    print()
    print(f"Iniciando upload para S3 (bucket: {bucket}, regiao: {region})...")
    cmd = ["aws", "s3", "cp", str(upload_dir) + "/", f"s3://{bucket}/", "--recursive", "--region", region]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            shell=(os.name == "nt"),
        )
    except FileNotFoundError:
        print("Aviso: aws CLI nao executavel. Upload S3 pulado.")
        return
    if result.returncode != 0:
        print(f"Aviso: upload S3 falhou (exit {result.returncode}).")
    else:
        print("Upload S3 concluido.")


def update_latest_upload_package(latest_dir: Path) -> None:
    copy_latest_upload_script = SCRIPT_DIR / "copy_latest_upload.py"
    ensure_file(copy_latest_upload_script)
    run_command(
        [
            sys.executable,
            str(copy_latest_upload_script),
            "--source-dir",
            str(latest_dir),
            "--dest-dir",
            str(latest_dir / "latest-upload"),
            "--clean-dest",
        ]
    )


def open_dashboard() -> None:
    dashboard_script = SCRIPT_DIR / "dashboard_full.py"
    ensure_file(dashboard_script)

    print()
    print("Iniciando dashboard web...")

    popen_kwargs: dict[str, object] = {
        "cwd": str(SCRIPT_DIR),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if IS_WINDOWS:
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        if creationflags:
            popen_kwargs["creationflags"] = creationflags
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen([sys.executable, str(dashboard_script)], **popen_kwargs)
    time.sleep(6)
    try:
        webbrowser.open("http://127.0.0.1:8050")
    except Exception:
        pass
    print("Dashboard aberto em http://127.0.0.1:8050")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser()
    latest_dir = resolve_latest_dir().expanduser()
    env_file = Path(args.env_file).expanduser()
    date_tag = args.date_tag or get_date_tag()

    load_env_file(env_file, override_existing=True)
    ensure_required_env(env_file)

    out_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    export_downstream_projects(
        out_dir=out_dir,
        latest_dir=latest_dir,
        env_file=env_file,
        date_tag=date_tag,
        workers=args.workers,
        run_detailed_changelog_export=args.run_detailed_changelog_export,
    )

    if args.portfolio:
        export_portfolio(out_dir, latest_dir, env_file, date_tag)

    if args.gmud_coverage:
        run_gmud_coverage(out_dir, latest_dir, env_file, date_tag)

    if args.capex_export:
        export_capex(out_dir, latest_dir, env_file, args.workers)

    if args.four_ps_kanban:
        export_four_ps_kanban(
            latest_dir=latest_dir,
            env_file=env_file,
            history_months=args.four_ps_history_months,
        )

    if args.process_mining:
        run_process_mining(out_dir, latest_dir)

    if args.metrics:
        run_metrics(out_dir, latest_dir)

    update_latest_upload_package(latest_dir)

    if args.s3_upload:
        upload_to_s3(latest_dir / "latest-upload")

    if args.open_dashboard:
        open_dashboard()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
