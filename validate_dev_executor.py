#!/usr/bin/env python3
"""
Validação do enriquecimento DevExecutor via PRs do Bitbucket.

Evidências geradas:
  1. Cobertura global -- quantos itens Done têm DevExecutor preenchido
  2. Divergências -- itens onde DevExecutor != Responsável (a virada de atribuição)
  3. Resumo por dev -- antes vs depois da nova atribuição
  4. Amostra dos 20 maiores casos de divergência no período

Uso:
  python validate_dev_executor.py
  python validate_dev_executor.py --start 2026-02-01 --end 2026-03-31
  python validate_dev_executor.py --csv "C:/Dados/w1nner-downstream-latest-data.csv"
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

import pandas as pd

# ── Configuração ──────────────────────────────────────────────────────────────
DATA_DIR   = str(Path.home() / "Documents" / "dados" / "latest")
DATE_START = "2026-02-01"
DATE_END   = "2026-03-31"
DONE_COL   = "Done"          # coluna de data Done no CSV downstream
RESP_COL   = "Responsável"   # nome original no CSV
EXEC_COL   = "DevExecutor"
ID_COL     = "ID"
TITLE_COL  = "Title"


def _parse_date(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_datetime(df[col], dayfirst=True, errors="coerce")


def _find_latest_csvs(data_dir: str) -> list[str]:
    """Retorna os CSVs downstream mais recentes (padrão *-downstream-latest-data.csv)."""
    pattern = os.path.join(data_dir, "*-downstream-latest-data.csv")
    files = glob.glob(pattern)
    if not files:
        # fallback: qualquer downstream recente
        pattern = os.path.join(data_dir, "*-downstream-*-data.csv")
        files = glob.glob(pattern)
        files = sorted(files)[-4:] if files else []
    return sorted(files)


def load_csvs(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p, dtype=str, low_memory=False)
            df["_fonte_arquivo"] = Path(p).name
            frames.append(df)
            print(f"  Carregado: {Path(p).name}  ({len(df):,} linhas)")
        except Exception as e:
            print(f"  ERRO ao ler {p}: {e}", file=sys.stderr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def normalize_name(s: str) -> str:
    return str(s or "").strip().lower()


def run_validation(df: pd.DataFrame, start: str, end: str) -> None:
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end) + pd.Timedelta(days=1)  # inclusivo

    # ── Normaliza colunas ─────────────────────────────────────────────────────
    # Suporte a "Responsável" (com acento) e "Responsavel" (sem)
    resp_col_found = next((c for c in ("Responsável", "Responsavel") if c in df.columns), None)
    if resp_col_found is None:
        print("\n[ERRO] Coluna Responsável/Responsavel não encontrada no CSV.", file=sys.stderr)
        sys.exit(1)

    # ── Evidência 1: coluna DevExecutor existe? ───────────────────────────────
    print("\n" + "=" * 60)
    print("EVIDÊNCIA 1 -- Presença da coluna DevExecutor")
    print("=" * 60)
    if EXEC_COL not in df.columns:
        print(
            f"\n  FALHA  Coluna '{EXEC_COL}' NÃO encontrada no CSV.\n"
            "     -> Execute run_all_projects.ps1 com as variáveis BITBUCKET_* configuradas\n"
            "       e volte a rodar este script."
        )
        return
    print(f"\n  OK  Coluna '{EXEC_COL}' encontrada.")

    # ── Detecta e combina colunas de Done de múltiplos projetos ──────────────
    # W1NNR/S1NC/BF usam "Itens concluídos"; DT usa "Done"; pós-processamento usa "DataDone".
    done_cols = [c for c in df.columns if c in ("Done", "DataDone") or "conclu" in c.lower()]
    if not done_cols:
        print("\n[ERRO] Nenhuma coluna Done encontrada. Colunas:", list(df.columns[:10]), file=sys.stderr)
        sys.exit(1)

    print(f"\n  Colunas Done detectadas: {done_cols}")
    # Combina: pega a primeira data não-nula entre as colunas candidatas
    combined = pd.Series(pd.NaT, index=df.index)
    for col in done_cols:
        parsed = _parse_date(df, col)
        combined = combined.where(combined.notna(), parsed)
    df["_DataDone"] = combined

    periodo = df[
        (df["_DataDone"] >= start_ts) & (df["_DataDone"] < end_ts)
    ].copy()
    print(f"  Periodo de analise: {start} -> {end}")
    print(f"  Itens Done no periodo: {len(periodo):,}")

    if periodo.empty:
        print("\n  Nenhum item Done encontrado no período informado.")
        return

    periodo["_Responsavel"] = periodo[resp_col_found].fillna("").str.strip()
    periodo["_DevExecutor"] = periodo[EXEC_COL].fillna("").str.strip()

    # ── Evidência 2: Cobertura ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EVIDÊNCIA 2 -- Cobertura do DevExecutor")
    print("=" * 60)
    total      = len(periodo)
    com_exec   = (periodo["_DevExecutor"].ne("")).sum()
    sem_exec   = total - com_exec
    cobertura  = com_exec / total * 100 if total else 0

    print(f"\n  Total de itens Done ({start[:7]} a {end[:7]}): {total:>6,}")
    print(f"  Com DevExecutor preenchido:                  {com_exec:>6,}  ({cobertura:.1f}%)")
    print(f"  Sem DevExecutor (sem PR linkado):            {sem_exec:>6,}  ({100 - cobertura:.1f}%)")

    if cobertura == 0:
        print(
            "\n  FALHA  Nenhum item com DevExecutor preenchido.\n"
            "     Verifique se BITBUCKET_REPOS aponta para os repositórios corretos\n"
            "     e se os PRs têm o Jira key no título ou no branch (ex: W1NNR-123)."
        )
        return
    print("\n  OK  Enriquecimento Bitbucket ativo.")

    # ── Evidência 3: Divergências (Responsavel != DevExecutor) ────────────────
    print("\n" + "=" * 60)
    print("EVIDÊNCIA 3 -- Divergências: DevExecutor != Responsável")
    print("=" * 60)
    diverg = periodo[
        periodo["_DevExecutor"].ne("") &
        (periodo["_DevExecutor"].str.lower() != periodo["_Responsavel"].str.lower())
    ].copy()

    n_diverg = len(diverg)
    pct_diverg = n_diverg / total * 100 if total else 0
    print(f"\n  Itens onde atribuição muda:  {n_diverg:>6,}  ({pct_diverg:.1f}% dos itens Done)")
    print(f"  Itens com atribuição igual:  {com_exec - n_diverg:>6,}")

    if n_diverg > 0:
        print(f"\n  {'ID':<14}  {'Done':<11}  {'Responsável (Jira)':<28}  {'DevExecutor (PR)':<28}  Arquivo")
        print(f"  {'-'*14}  {'-'*11}  {'-'*28}  {'-'*28}  {'-'*30}")
        amostra = diverg.sort_values("_DataDone", ascending=False).head(20)
        for _, row in amostra.iterrows():
            _id    = str(row.get(ID_COL, ""))[:14]
            _done  = str(row["_DataDone"])[:10]
            _resp  = row["_Responsavel"][:28]
            _exec  = row["_DevExecutor"][:28]
            _arq   = str(row.get("_fonte_arquivo", ""))[:30]
            print(f"  {_id:<14}  {_done:<11}  {_resp:<28}  {_exec:<28}  {_arq}")

    # ── Evidência 4: Resumo antes vs depois por dev ───────────────────────────
    print("\n" + "=" * 60)
    print("EVIDÊNCIA 4 -- Impacto por desenvolvedor (Antes vs Depois)")
    print("=" * 60)

    # "Antes" = contagem por Responsavel
    antes = (
        periodo.groupby("_Responsavel").size()
        .reset_index(name="Antes (Responsável)")
    )

    # "Depois" = contagem por DevExecutor quando preenchido, Responsavel como fallback
    periodo["_AtribFinal"] = periodo["_DevExecutor"].where(
        periodo["_DevExecutor"].ne(""), periodo["_Responsavel"]
    )
    depois = (
        periodo.groupby("_AtribFinal").size()
        .reset_index(name="Depois (DevExecutor)")
        .rename(columns={"_AtribFinal": "_Responsavel"})
    )

    comp = pd.merge(antes, depois, on="_Responsavel", how="outer").fillna(0)
    comp["Antes (Responsável)"]  = comp["Antes (Responsável)"].astype(int)
    comp["Depois (DevExecutor)"] = comp["Depois (DevExecutor)"].astype(int)
    comp["Delta"] = comp["Depois (DevExecutor)"] - comp["Antes (Responsável)"]
    comp = comp.sort_values("Delta", ascending=False)

    # Mostra só quem mudou
    mudou = comp[comp["Delta"] != 0]
    if mudou.empty:
        print("\n  Nenhuma mudança de contagem detectada (DevExecutor == Responsável em todos os casos).")
    else:
        print(f"\n  {'Desenvolvedor':<35}  {'Antes':>6}  {'Depois':>6}  {'Delta':>6}")
        print(f"  {'-'*35}  {'-'*6}  {'-'*6}  {'-'*6}")
        for _, row in mudou.iterrows():
            sinal = "+" if row["Delta"] > 0 else ""
            print(
                f"  {str(row['_Responsavel']):<35}  "
                f"{int(row['Antes (Responsável)']):>6}  "
                f"{int(row['Depois (DevExecutor)']):>6}  "
                f"{sinal}{int(row['Delta']):>5}"
            )

    print("\n" + "=" * 60)
    print("Validação concluída.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida enriquecimento DevExecutor no pipeline CSV.")
    parser.add_argument("--start", default=DATE_START, help="Data início (YYYY-MM-DD)")
    parser.add_argument("--end",   default=DATE_END,   help="Data fim (YYYY-MM-DD)")
    parser.add_argument("--csv",   default="",         help="Caminho de um CSV específico (opcional)")
    parser.add_argument("--dir",   default=DATA_DIR,   help="Diretório dos CSVs downstream")
    args = parser.parse_args()

    print("Flow-PMO · Validação DevExecutor (Bitbucket PR Author Enrichment)")
    print(f"Periodo: {args.start} a {args.end}\n")

    if args.csv:
        paths = [args.csv]
    else:
        paths = _find_latest_csvs(args.dir)
        if not paths:
            print(f"[ERRO] Nenhum CSV downstream encontrado em: {args.dir}", file=sys.stderr)
            sys.exit(1)
        print(f"CSVs encontrados ({len(paths)}):")

    df = load_csvs(paths)
    if df.empty:
        print("[ERRO] Nenhum dado carregado.", file=sys.stderr)
        sys.exit(1)

    print(f"\nTotal de linhas carregadas: {len(df):,}")
    run_validation(df, args.start, args.end)


if __name__ == "__main__":
    main()
