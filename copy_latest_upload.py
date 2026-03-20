#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactRule:
    pattern: str
    required: bool = True


REQUIRED_RULES = (
    ArtifactRule("PowerBI_Model_latest.xlsx"),
    ArtifactRule("portfolio-bt-ns-latest-data.csv"),
    ArtifactRule("w1nner-process-mining-latest.xlsx"),
    ArtifactRule("s1nc-process-mining-latest.xlsx"),
    ArtifactRule("befinance-process-mining-latest.xlsx"),
    ArtifactRule("dataanalytics-process-mining-latest.xlsx"),
    ArtifactRule("w1nner-downstream-latest-data.csv"),
    ArtifactRule("s1nc-downstream-latest-data.csv"),
    ArtifactRule("befinance-downstream-latest-data.csv"),
    ArtifactRule("dataanalytics-downstream-latest-data.csv"),
    ArtifactRule("w1nner-downstream-latest-data_bottlenecks.csv"),
    ArtifactRule("s1nc-downstream-latest-data_bottlenecks.csv"),
    ArtifactRule("befinance-downstream-latest-data_bottlenecks.csv"),
    ArtifactRule("dataanalytics-downstream-latest-data_bottlenecks.csv"),
    ArtifactRule("w1nner_commits.csv"),
    ArtifactRule("w1nner_pullrequests.csv"),
    ArtifactRule("w1nner_pipelines.csv"),
    ArtifactRule("befinance_commits.csv"),
    ArtifactRule("befinance_pullrequests.csv"),
    ArtifactRule("befinance_pipelines.csv"),
    ArtifactRule("dataanalytics_commits.csv"),
    ArtifactRule("dataanalytics_pullrequests.csv"),
    ArtifactRule("dataanalytics_pipelines.csv"),
)

OPTIONAL_RULES = (
    ArtifactRule("s1nc_commits.csv", required=False),
    ArtifactRule("s1nc_pullrequests.csv", required=False),
    ArtifactRule("s1nc_pipelines.csv", required=False),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copia os artefatos latest esperados para uma subpasta pronta para upload."
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Pasta central que contem os arquivos latest.",
    )
    parser.add_argument(
        "--dest-dir",
        help="Destino final. Padrao: <source-dir>/latest-upload",
    )
    parser.add_argument(
        "--clean-dest",
        action="store_true",
        help="Remove arquivos existentes no destino antes de copiar.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falha se algum artefato obrigatorio estiver ausente.",
    )
    return parser.parse_args()


def resolve_single_match(source_dir: Path, pattern: str) -> Path | None:
    matches = sorted(path for path in source_dir.glob(pattern) if path.is_file())
    if not matches:
        return None
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise RuntimeError(f"Padrao ambiguo '{pattern}' encontrou multiplos arquivos: {names}")
    return matches[0]


def clean_destination(dest_dir: Path) -> None:
    if not dest_dir.exists():
        return
    for child in dest_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_rule(source_dir: Path, dest_dir: Path, rule: ArtifactRule) -> tuple[str, Path | None]:
    match = resolve_single_match(source_dir, rule.pattern)
    if match is None:
        if rule.required:
            return ("required-missing", None)
        return ("optional-missing", None)

    target = dest_dir / match.name
    shutil.copy2(match, target)
    return ("copied", target)


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir).expanduser().resolve()
    dest_dir = (
        Path(args.dest_dir).expanduser().resolve()
        if args.dest_dir
        else source_dir / "latest-upload"
    )

    if not source_dir.is_dir():
        print(f"Pasta de origem nao encontrada: {source_dir}", file=sys.stderr)
        return 1

    dest_dir.mkdir(parents=True, exist_ok=True)
    if args.clean_dest:
        clean_destination(dest_dir)

    copied_count = 0
    required_missing: list[str] = []
    optional_missing: list[str] = []
    for rule in (*REQUIRED_RULES, *OPTIONAL_RULES):
        status, target = copy_rule(source_dir, dest_dir, rule)
        if status == "copied" and target is not None:
            copied_count += 1
            print(f"Copiado: {target.name}")
        elif status == "required-missing":
            required_missing.append(rule.pattern)
            print(f"Obrigatorio ausente: {rule.pattern}")
        elif status == "optional-missing":
            optional_missing.append(rule.pattern)
            print(f"Opcional ausente: {rule.pattern}")

    print(f"Pacote latest-upload atualizado em: {dest_dir}")
    print(f"Arquivos copiados: {copied_count}")
    if required_missing:
        joined = ", ".join(required_missing)
        print(f"Obrigatorios ausentes: {joined}", file=sys.stderr)
        if args.strict:
            return 1
    if optional_missing:
        joined = ", ".join(optional_missing)
        print(f"Opcionais ausentes: {joined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
