#!/usr/bin/env python3
"""
Diagnostico de cobertura do DevExecutor.

Tres frentes de analise:
  A) Cobertura por projeto Jira (W1NNR, S1NC, BF, DT...)
  B) Padrão de nomenclatura nos PRs do Bitbucket
     -- quantos PRs têm Jira key no titulo/branch
     -- quais padrões existem nos que NÃO têm
  C) Itens Done sem DevExecutor: tipo, responsavel, projeto

Uso:
  python diag_dev_executor_coverage.py
  python diag_dev_executor_coverage.py --start 2026-02-01 --end 2026-03-31
  python diag_dev_executor_coverage.py --env jira_env.txt
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
DATA_DIR    = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
DATE_START  = "2026-02-01"
DATE_END    = "2026-03-31"
ENV_FILE    = "jira_env.txt"

JIRA_KEY_RE = re.compile(r'\b([A-Z][A-Z0-9_]*-\d+)\b')
PROJECT_RE  = re.compile(r'^([A-Z][A-Z0-9_]+)-\d+')
# ---------------------------------------------------------------------------


def load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


def _find_latest_csvs(data_dir: str) -> List[str]:
    pattern = os.path.join(data_dir, "*-downstream-latest-data.csv")
    files = glob.glob(pattern)
    if not files:
        pattern = os.path.join(data_dir, "*-downstream-*-data.csv")
        files = glob.glob(pattern)
        files = sorted(files)[-4:] if files else []
    return sorted(files)


def load_csvs(paths: List[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p, dtype=str, low_memory=False)
            df["_fonte"] = Path(p).name
            frames.append(df)
            print(f"  Carregado: {Path(p).name}  ({len(df):,} linhas)")
        except Exception as e:
            print(f"  ERRO ao ler {p}: {e}", file=sys.stderr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _combine_done_date(df: pd.DataFrame) -> pd.Series:
    done_cols = [c for c in df.columns if c in ("Done", "DataDone") or "conclu" in c.lower()]
    combined = pd.Series(pd.NaT, index=df.index)
    for col in done_cols:
        parsed = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
        combined = combined.where(combined.notna(), parsed)
    return combined


def _project_prefix(issue_id: str) -> str:
    m = PROJECT_RE.match(str(issue_id or ""))
    return m.group(1) if m else "OUTROS"


# ===========================================================================
# PARTE A: analise dos CSVs
# ===========================================================================
def analyze_csv_coverage(df: pd.DataFrame, start: str, end: str) -> None:
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end) + pd.Timedelta(days=1)

    df["_DataDone"] = _combine_done_date(df)
    periodo = df[(df["_DataDone"] >= start_ts) & (df["_DataDone"] < end_ts)].copy()

    if periodo.empty:
        print("  Nenhum item Done no periodo informado.")
        return

    resp_col = next((c for c in ("Responsavel", "Responsável") if c in periodo.columns), None)
    if resp_col:
        periodo["_Responsavel"] = periodo[resp_col].fillna("").str.strip()
    else:
        periodo["_Responsavel"] = ""

    has_exec = "DevExecutor" in periodo.columns
    if has_exec:
        periodo["_DevExecutor"] = periodo["DevExecutor"].fillna("").str.strip()
    else:
        periodo["_DevExecutor"] = ""

    periodo["_Projeto"] = periodo.get("ID", pd.Series("", index=periodo.index)).apply(_project_prefix)

    total = len(periodo)
    com   = int(periodo["_DevExecutor"].ne("").sum())
    sem   = total - com

    print(f"\n  Total itens Done ({start[:7]} a {end[:7]}): {total:,}")
    print(f"  Com DevExecutor : {com:,}  ({com/total*100:.1f}%)")
    print(f"  Sem DevExecutor : {sem:,}  ({sem/total*100:.1f}%)")

    # -- por projeto
    print(f"\n  {'Projeto':<14}  {'Total':>7}  {'c/Exec':>7}  {'Cobert':>7}  Obs")
    print(f"  {'-'*14}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*30}")
    for proj, grp in sorted(periodo.groupby("_Projeto")):
        n  = len(grp)
        nc = int(grp["_DevExecutor"].ne("").sum())
        pct = nc / n * 100 if n else 0
        # pega primeiro arquivo fonte para contextualizar
        src = str(grp["_fonte"].iloc[0])[:30] if "_fonte" in grp.columns else ""
        obs = "OK" if pct >= 20 else ("sem PRs? verifique BB_REPOS" if pct == 0 else "baixa cobertura")
        print(f"  {proj:<14}  {n:>7,}  {nc:>7,}  {pct:>6.1f}%  {obs}")

    # -- por tipo de item (se coluna Issue Type existir)
    type_col = next((c for c in ("Issue Type", "IssueType", "Tipo") if c in periodo.columns), None)
    if type_col:
        print(f"\n  Cobertura por tipo de item (coluna: {type_col})")
        print(f"  {'Tipo':<28}  {'Total':>6}  {'c/Exec':>6}  {'%':>6}")
        print(f"  {'-'*28}  {'-'*6}  {'-'*6}  {'-'*6}")
        for tipo, grp in sorted(periodo.groupby(type_col)):
            n  = len(grp)
            nc = int(grp["_DevExecutor"].ne("").sum())
            pct = nc / n * 100 if n else 0
            print(f"  {str(tipo):<28}  {n:>6,}  {nc:>6,}  {pct:>5.1f}%")

    # -- amostra dos itens sem DevExecutor (20 mais recentes)
    sem_exec = periodo[periodo["_DevExecutor"].eq("")].copy()
    print(f"\n  Amostra de itens sem DevExecutor (ate 20, mais recentes):")
    print(f"  {'ID':<18}  {'Projeto':<10}  {'Responsavel':<28}  {'Done':<12}  Titulo")
    print(f"  {'-'*18}  {'-'*10}  {'-'*28}  {'-'*12}  {'-'*40}")
    for _, row in sem_exec.sort_values("_DataDone", ascending=False).head(20).iterrows():
        _id   = str(row.get("ID", ""))[:18]
        _proj = str(row.get("_Projeto", ""))[:10]
        _resp = str(row.get("_Responsavel", ""))[:28]
        _done = str(row["_DataDone"])[:10]
        _title = str(row.get("Title", row.get("Summary", "")))[:40]
        print(f"  {_id:<18}  {_proj:<10}  {_resp:<28}  {_done:<12}  {_title}")


# ===========================================================================
# PARTE B: analise dos PRs no Bitbucket
# ===========================================================================
def analyze_bitbucket_pr_patterns(
    workspace: str,
    repos: List[str],
    username: str,
    token: str,
    sample_per_repo: int = 100,
) -> None:
    auth    = (username, token)
    headers = {"Accept": "application/json"}

    print(f"\n  Analisando padroes de nomenclatura em {len(repos)} repos")
    print(f"  (amostra de ate {sample_per_repo} PRs merged por repo)\n")

    total_prs    = 0
    com_key      = 0
    sem_key      = 0
    prefixos_ok  : Counter = Counter()   # projetos encontrados
    sem_key_tits : List[str] = []        # titulos sem key (para analise)
    sem_key_brncs: List[str] = []        # branches sem key

    print(f"  {'Repo':<42}  {'PRs':>5}  {'c/Key':>6}  {'%':>6}  {'Prefixos'}")
    print(f"  {'-'*42}  {'-'*5}  {'-'*6}  {'-'*6}  {'-'*30}")

    for repo in repos:
        repo = repo.strip()
        if not repo:
            continue
        url: Optional[str] = (
            f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}"
            f"/pullrequests?state=MERGED&pagelen=50"
        )
        repo_total = 0
        repo_com   = 0
        repo_prefixos: Counter = Counter()
        pages = 0

        while url and repo_total < sample_per_repo:
            try:
                resp = requests.get(url, auth=auth, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"  ERRO {repo}: {e}")
                break

            for pr in data.get("values", []):
                if repo_total >= sample_per_repo:
                    break
                title  = pr.get("title") or ""
                branch = (pr.get("source") or {}).get("branch", {}).get("name") or ""
                keys_found: set = set()
                for text in (title, branch):
                    for m in JIRA_KEY_RE.finditer(text):
                        keys_found.add(m.group(1))
                        repo_prefixos[_project_prefix(m.group(1))] += 1
                if keys_found:
                    repo_com += 1
                    for k in keys_found:
                        prefixos_ok[_project_prefix(k)] += 1
                else:
                    if len(sem_key_tits) < 30:
                        sem_key_tits.append(f"[{repo}] titulo: {title[:70]!r}")
                    if branch and len(sem_key_brncs) < 30:
                        sem_key_brncs.append(f"[{repo}] branch: {branch[:70]!r}")
                repo_total += 1

            pages += 1
            url = data.get("next")

        pct = repo_com / repo_total * 100 if repo_total else 0
        pfx = ", ".join(f"{p}({n})" for p, n in repo_prefixos.most_common(4))
        print(f"  {repo:<42}  {repo_total:>5}  {repo_com:>6}  {pct:>5.1f}%  {pfx or '--'}")
        total_prs += repo_total
        com_key   += repo_com
        sem_key   += repo_total - repo_com

    pct_global = com_key / total_prs * 100 if total_prs else 0
    print(f"\n  TOTAL  {total_prs:,} PRs amostrados  |  {com_key:,} com Jira key ({pct_global:.1f}%)  |  {sem_key:,} sem key")

    if sem_key_tits:
        print(f"\n  -- Exemplos de PRs SEM Jira key no titulo (primeiros {len(sem_key_tits)}) --")
        for t in sem_key_tits[:15]:
            print(f"    {t}")

    if sem_key_brncs:
        print(f"\n  -- Exemplos de branches SEM Jira key (primeiros {len(sem_key_brncs)}) --")
        for b in sem_key_brncs[:15]:
            print(f"    {b}")

    # recomendacoes
    print("\n  -- Prefixos Jira encontrados nos PRs --")
    for pfx, n in prefixos_ok.most_common():
        print(f"    {pfx:<14}  {n:>5} refs")


# ===========================================================================
# PARTE C: repos sem Jira key — sugestão de padrão de branch
# ===========================================================================
def show_recommendations() -> None:
    print("\n" + "=" * 60)
    print("RECOMENDACOES PARA AMPLIAR COBERTURA")
    print("=" * 60)
    print("""
  1. NOMENCLATURA DE PRs (principal causa de cobertura baixa)
     Para que o DevExecutor seja preenchido automaticamente, o PR
     deve ter o Jira key no TITULO ou no BRANCH de origem.

     Exemplos de titulo valido:
       W1NNR-1234: Fix login timeout
       [BF-567] Corrige calculo de comissao

     Exemplos de branch valido:
       feature/W1NNR-1234-fix-login
       bugfix/BF-567-comissao

  2. REPOS ADICIONAIS
     Verifique se todos os repositorios ativos estao em BB_REPOS
     em jira_env.txt. Um repo ausente significa 0% cobertura para
     os PRs dele.

  3. TAREFAS SEM CODIGO (expectativa de cobertura realista)
     Bugs de documentacao, tarefas administrativas, descobertas
     e itens de processo raramente têm PRs. É normal que estes
     fiquem sem DevExecutor — o Responsavel do Jira é a fonte correta.

  4. HISTORICO vs NOVO (daqui pra frente)
     A cobertura de 26% é de todo o historico de PRs. Para itens
     feitos DEPOIS de implementar a convencao, a cobertura sobe.
     Alinhe o time sobre o padrao de nomenclatura de PRs.
""")


# ===========================================================================
# main
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostico de cobertura DevExecutor")
    parser.add_argument("--start", default=DATE_START)
    parser.add_argument("--end",   default=DATE_END)
    parser.add_argument("--env",   default=ENV_FILE)
    parser.add_argument("--dir",   default=DATA_DIR)
    parser.add_argument("--csv",   default="", help="CSV especifico (opcional)")
    parser.add_argument("--sample", default=100, type=int, help="PRs por repo na analise de padroes (padrao 100)")
    parser.add_argument("--skip-bitbucket", action="store_true", help="Pula analise de PRs (somente CSV)")
    args = parser.parse_args()

    load_env_file(args.env)

    print("=" * 60)
    print("DIAGNOSTICO DE COBERTURA DEVEXECUTOR")
    print("=" * 60)

    # ── PARTE A: CSV ──────────────────────────────────────────────────────────
    print("\n[A] ANALISE DOS CSVs DOWNSTREAM")
    print("-" * 60)

    if args.csv:
        paths = [args.csv]
    else:
        paths = _find_latest_csvs(args.dir)
        if not paths:
            print(f"  [ERRO] Nenhum CSV encontrado em: {args.dir}")
            sys.exit(1)
        print(f"  CSVs encontrados: {len(paths)}")

    df = load_csvs(paths)
    if df.empty:
        print("  [ERRO] Nenhum dado carregado.")
        sys.exit(1)

    print(f"  Total de linhas: {len(df):,}")
    analyze_csv_coverage(df, args.start, args.end)

    # ── PARTE B: Bitbucket ────────────────────────────────────────────────────
    if not args.skip_bitbucket:
        print("\n[B] ANALISE DE PADROES DE NOMENCLATURA NOS PRs BITBUCKET")
        print("-" * 60)

        workspace = os.getenv("BB_WORKSPACE", "").strip()
        username  = os.getenv("BB_EMAIL",     "").strip()
        token     = os.getenv("BB_TOKEN",     "").strip()
        repos_raw = (os.getenv("BB_REPOS", "") or os.getenv("BB_REPO", "")).strip()
        repos     = [r.strip() for r in repos_raw.split(",") if r.strip()]

        if not workspace or not username or not token or not repos:
            print("  BB_WORKSPACE / BB_EMAIL / BB_TOKEN / BB_REPOS nao configurados.")
            print("  Rode com --skip-bitbucket para pular esta secao.")
        else:
            analyze_bitbucket_pr_patterns(workspace, repos, username, token, args.sample)

    # ── PARTE C: recomendacoes ────────────────────────────────────────────────
    show_recommendations()

    print("=" * 60)
    print("Diagnostico concluido.")
    print("=" * 60)


if __name__ == "__main__":
    main()
