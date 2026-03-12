#!/usr/bin/env python3
"""
extract_dev_productivity_data.py
─────────────────────────────────────────────────────────────────────────────
Script único para extrair os dados Bitbucket necessários para a aba
"Produtividade Dev" do dashboard.

Projetos extraídos
──────────────────
  W1NNER     → repo w1nner   (filtro W1NNR / W1NNER)
  S1NC       → repo w1nner   (mesmo repo, filtro S1NC / W1SFT)
  BeFinance  → repo befinance
  Dados/DA   → repo dataanalytics

Credenciais (lidas de jira_env.txt ou variáveis de ambiente)
────────────────────────────────────────────────────────────
  BB_EMAIL      e-mail Atlassian
  BB_TOKEN      App Password ou API token do Bitbucket
  BB_WORKSPACE  slug do workspace (ex: w1consultoria)

  Os repos individuais são resolvidos automaticamente a partir do --project.
  Você pode sobrescrever com FLOW_PMO_BITBUCKET_REPO_MAP no jira_env.txt.

Saída
─────
  CSVs gravados em --out-dir (padrão: mesma pasta do PowerBI_Model / OneDrive).
  Prefixos gerados:
    w1nner_commits.csv, w1nner_pullrequests.csv, w1nner_pipelines.csv
    s1nc_commits.csv,   s1nc_pullrequests.csv,   s1nc_pipelines.csv
    befinance_commits.csv ...
    dataanalytics_commits.csv ...

Uso
───
  python extract_dev_productivity_data.py
  python extract_dev_productivity_data.py --since-days 90
  python extract_dev_productivity_data.py --out-dir /caminho/personalizado
  python extract_dev_productivity_data.py --projects W1NNR S1NC
  python extract_dev_productivity_data.py --skip-pipelines --workers 2
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

from shared.env_utils import load_env_file

# ── Constantes ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE_DEFAULT = str(SCRIPT_DIR / "jira_env.txt")
BITBUCKET_EXPORT_SCRIPT = str(SCRIPT_DIR / "bitbucket_export.py")

# Pasta padrão de saída dos dados (mesma usada pelo dashboard)
if platform.system() == "Windows":
    _DEFAULT_OUT_DIR = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
else:
    _DEFAULT_OUT_DIR = str(
        Path.home() / "Library" / "CloudStorage" / "OneDrive-W1" / "Documentos" / "Dados"
    )

# Projetos disponíveis para extração
# Cada entry: chave CLI → configuração passada ao bitbucket_export.py
_ALL_PROJECTS: dict[str, dict] = {
    "W1NNR": {
        "label": "Sistemas W1NNER",
        "project_arg": "W1NNR",
        # W1NNER e S1NC compartilham o mesmo repo; a separação é feita por
        # issue_key_prefixes (issue keys no título/branch do commit/PR).
    },
    "S1NC": {
        "label": "Sistemas S1NC",
        "project_arg": "S1NC",
    },
    "BF": {
        "label": "BeFinance",
        "project_arg": "BF",
    },
    "DT": {
        "label": "Dados / Data & Analytics",
        "project_arg": "DT",
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_out_dir(out_dir_arg: str) -> Path:
    """Determina e cria a pasta de saída."""
    # Prioridade: argumento CLI > FLOW_PMO_DATA_DIR > FLOW_PMO_LATEST_DIR > DATA_FOLDER > padrão OneDrive
    candidate = (
        out_dir_arg
        or os.getenv("FLOW_PMO_DATA_DIR", "").strip()
        or os.getenv("FLOW_PMO_LATEST_DIR", "").strip()
        or os.getenv("DATA_FOLDER", "").strip()
        or _DEFAULT_OUT_DIR
    )
    out = Path(candidate)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _check_credentials() -> list[str]:
    """Verifica variáveis obrigatórias. Retorna lista de ausentes."""
    required = ["BB_EMAIL", "BB_TOKEN", "BB_WORKSPACE"]
    return [v for v in required if not os.getenv(v, "").strip()]


def _run_project(
    project_key: str,
    config: dict,
    *,
    out_dir: Path,
    since_days: int,
    pagelen: int,
    workers: int,
    skip_pipelines: bool,
    skip_pr_volume: bool,
    dry_run: bool,
    verbose: bool,
) -> bool:
    """Executa bitbucket_export.py para um projeto. Retorna True se ok."""
    label = config["label"]
    project_arg = config["project_arg"]

    cmd = [
        sys.executable,
        BITBUCKET_EXPORT_SCRIPT,
        "--env-file", ENV_FILE_DEFAULT,
        "--project", project_arg,
        "--out-dir", str(out_dir),
        "--pagelen", str(pagelen),
        "--workers", str(workers),
    ]

    if since_days > 0:
        cmd += ["--since-days", str(since_days)]
    if skip_pipelines:
        cmd.append("--skip-pipelines")
    if skip_pr_volume:
        cmd.append("--skip-pr-volume")
    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'─'*60}")
    print(f"  Projeto : {label} ({project_arg})")
    print(f"  Saída   : {out_dir}")
    if since_days > 0:
        print(f"  Janela  : últimos {since_days} dias")
    else:
        print("  Janela  : histórico completo")
    print(f"{'─'*60}")

    if verbose:
        print("  CMD:", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=not verbose)

    if result.returncode == 0:
        if not verbose and result.stdout:
            for line in result.stdout.decode("utf-8", errors="replace").splitlines():
                print(f"  {line}")
        print(f"  [OK] {label}")
        return True
    else:
        print(f"  [ERRO] {label} — código {result.returncode}")
        if result.stderr:
            for line in result.stderr.decode("utf-8", errors="replace").splitlines():
                print(f"  ERR: {line}", file=sys.stderr)
        if not verbose and result.stdout:
            for line in result.stdout.decode("utf-8", errors="replace").splitlines():
                print(f"  OUT: {line}", file=sys.stderr)
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai dados Bitbucket (commits, PRs, pipelines) de todos os projetos "
            "necessários para a aba 'Produtividade Dev' do dashboard flow-pmo."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Extração completa (todos os projetos, histórico completo)
  python extract_dev_productivity_data.py

  # Só os últimos 60 dias
  python extract_dev_productivity_data.py --since-days 60

  # Só W1NNER e S1NC
  python extract_dev_productivity_data.py --projects W1NNR S1NC

  # Pasta personalizada de saída
  python extract_dev_productivity_data.py --out-dir ~/dados/flow

  # Sem volume de PRs (mais rápido, sem linhas adicionadas/removidas)
  python extract_dev_productivity_data.py --skip-pr-volume

  # Verificar configuração sem chamar a API
  python extract_dev_productivity_data.py --dry-run
        """,
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        default=list(_ALL_PROJECTS.keys()),
        metavar="PROJ",
        help=(
            "Projetos a extrair (default: todos). "
            "Opções: W1NNR S1NC BF DT"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help=(
            "Pasta de saída dos CSVs. "
            f"Default: FLOW_PMO_DATA_DIR ou {_DEFAULT_OUT_DIR}"
        ),
    )
    parser.add_argument(
        "--env-file",
        default=ENV_FILE_DEFAULT,
        help=f"Arquivo de credenciais (default: {ENV_FILE_DEFAULT})",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=0,
        help="Extrai apenas itens dos últimos N dias (0 = histórico completo)",
    )
    parser.add_argument(
        "--pagelen",
        type=int,
        default=50,
        help="Itens por página da API Bitbucket (max 50, default 50)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Workers paralelos por projeto (default 1 = sequencial)",
    )
    parser.add_argument(
        "--skip-pipelines",
        action="store_true",
        help="Não extrai pipelines (mais rápido; commits e PRs são suficientes para Produtividade Dev)",
    )
    parser.add_argument(
        "--skip-pr-volume",
        action="store_true",
        help="Não consulta diffstat por PR (mais rápido; dispensa métricas de linhas adicionadas/removidas)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida configuração sem fazer chamadas à API",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Exibe saída completa dos subprocessos",
    )
    return parser.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()

    # Carrega credenciais
    load_env_file(args.env_file, overwrite=False)

    missing = _check_credentials()
    if missing:
        print(
            f"\n[ERRO] Variáveis obrigatórias ausentes: {', '.join(missing)}\n"
            f"  Adicione-as em: {args.env_file}\n"
            f"  Exemplo:\n"
            f"    BB_EMAIL=seu.email@empresa.com\n"
            f"    BB_TOKEN=seu_app_password_bitbucket\n"
            f"    BB_WORKSPACE=seu_workspace_slug\n",
            file=sys.stderr,
        )
        return 2

    out_dir = _resolve_out_dir(args.out_dir)

    # Normaliza lista de projetos
    projects_requested = [p.strip().upper() for p in args.projects]
    projects_to_run = {}
    unknown = []
    for key in projects_requested:
        if key in _ALL_PROJECTS:
            projects_to_run[key] = _ALL_PROJECTS[key]
        else:
            unknown.append(key)

    if unknown:
        print(
            f"[AVISO] Projetos desconhecidos ignorados: {', '.join(unknown)}\n"
            f"  Projetos válidos: {', '.join(_ALL_PROJECTS.keys())}",
            file=sys.stderr,
        )

    if not projects_to_run:
        print("[ERRO] Nenhum projeto válido selecionado.", file=sys.stderr)
        return 2

    # Verifica se bitbucket_export.py existe
    if not Path(BITBUCKET_EXPORT_SCRIPT).exists():
        print(
            f"[ERRO] Script não encontrado: {BITBUCKET_EXPORT_SCRIPT}",
            file=sys.stderr,
        )
        return 2

    print("\n" + "═" * 60)
    print("  Extração Bitbucket — Produtividade Dev")
    print("═" * 60)
    print(f"  Projetos   : {', '.join(projects_to_run.keys())}")
    print(f"  Saída      : {out_dir}")
    print(f"  Env file   : {args.env_file}")
    print(f"  Histórico  : {'últimos ' + str(args.since_days) + ' dias' if args.since_days else 'completo'}")
    print(f"  Pipelines  : {'NÃO' if args.skip_pipelines else 'SIM'}")
    print(f"  PR volume  : {'NÃO' if args.skip_pr_volume else 'SIM'}")
    if args.dry_run:
        print("  MODO       : DRY-RUN (sem chamadas à API)")
    print("═" * 60)

    # NOTA IMPORTANTE sobre W1NNER + S1NC
    if "W1NNR" in projects_to_run and "S1NC" in projects_to_run:
        print(
            "\n  [INFO] W1NNER e S1NC compartilham o mesmo repositório Bitbucket.\n"
            "  Serão feitas duas extrações do mesmo repo com filtros diferentes\n"
            "  (W1NNR/W1NNER para W1NNER; S1NC/W1SFT para S1NC).\n"
            "  A separação final por BU acontece via people_config.json no dashboard.\n"
        )

    results: dict[str, bool] = {}
    for key, config in projects_to_run.items():
        ok = _run_project(
            key,
            config,
            out_dir=out_dir,
            since_days=args.since_days,
            pagelen=min(max(args.pagelen, 1), 50),
            workers=max(args.workers, 1),
            skip_pipelines=args.skip_pipelines,
            skip_pr_volume=args.skip_pr_volume,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        results[key] = ok

    # Sumário
    ok_list = [k for k, v in results.items() if v]
    err_list = [k for k, v in results.items() if not v]

    print("\n" + "═" * 60)
    print("  SUMÁRIO")
    print("═" * 60)
    for key in ok_list:
        print(f"  ✓ {key:12s}  {_ALL_PROJECTS[key]['label']}")
    for key in err_list:
        print(f"  ✗ {key:12s}  {_ALL_PROJECTS[key]['label']}  ← FALHOU")

    if err_list:
        print(
            f"\n  {len(err_list)} projeto(s) com erro. "
            "Verifique credenciais, repo slugs e conectividade.",
            file=sys.stderr,
        )

    print()
    if not args.dry_run and ok_list:
        print(
            "  Próximo passo: reinicie (ou recarregue) o dashboard para\n"
            "  que os CSVs gerados sejam detectados pela aba Produtividade Dev.\n"
        )

    return 0 if not err_list else 1


if __name__ == "__main__":
    raise SystemExit(main())
