#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
import time
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
    ArtifactRule("capex-raw-latest.csv", required=False),
    ArtifactRule("capex-summary-latest.csv", required=False),
    ArtifactRule("capex-latest.xlsx", required=False),
    ArtifactRule("dashboard_output_latest.xlsx", required=False),
    ArtifactRule("bottlenecks_consolidado_latest.xlsx", required=False),
)

DEFAULT_COPY_RETRIES = 6
DEFAULT_COPY_RETRY_DELAY_MS = 1000


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
    parser.add_argument(
        "--copy-retries",
        type=int,
        default=DEFAULT_COPY_RETRIES,
        help=f"Tentativas extras ao encontrar arquivo em uso. Padrao: {DEFAULT_COPY_RETRIES}.",
    )
    parser.add_argument(
        "--copy-retry-delay-ms",
        type=int,
        default=DEFAULT_COPY_RETRY_DELAY_MS,
        help=(
            "Espera entre tentativas ao encontrar arquivo em uso, em milissegundos. "
            f"Padrao: {DEFAULT_COPY_RETRY_DELAY_MS}."
        ),
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


def is_locked_file_error(exc: OSError) -> bool:
    winerror = getattr(exc, "winerror", None)
    if winerror == 32:
        return True
    message = str(exc).lower()
    return isinstance(exc, PermissionError) and "used by another process" in message


def run_with_lock_retries(
    operation,
    *,
    description: str,
    retries: int,
    retry_delay_ms: int,
) -> OSError | None:
    for attempt in range(retries + 1):
        try:
            operation()
            return None
        except FileNotFoundError:
            return None
        except OSError as exc:
            if (not is_locked_file_error(exc)) or attempt >= retries:
                return exc

            remaining = retries - attempt
            print(
                f"Aviso: {description} em uso por outro processo. "
                f"Nova tentativa em {retry_delay_ms} ms ({remaining} restante(s))."
            )
            time.sleep(retry_delay_ms / 1000)
    return None


def clean_destination(dest_dir: Path, *, retries: int, retry_delay_ms: int) -> list[Path]:
    if not dest_dir.exists():
        return []

    locked_paths: list[Path] = []
    for child in dest_dir.iterdir():
        error = run_with_lock_retries(
            (lambda path=child: shutil.rmtree(path))
            if child.is_dir()
            else (lambda path=child: path.unlink()),
            description=f"limpeza de {child.name}",
            retries=retries,
            retry_delay_ms=retry_delay_ms,
        )
        if error is None:
            continue
        if is_locked_file_error(error):
            locked_paths.append(child)
            print(f"Aviso: mantendo {child.name} no destino porque o arquivo está bloqueado.")
            continue
        raise error
    return locked_paths


def copy_rule(
    source_dir: Path,
    dest_dir: Path,
    rule: ArtifactRule,
    *,
    retries: int,
    retry_delay_ms: int,
) -> tuple[str, Path | None]:
    match = resolve_single_match(source_dir, rule.pattern)
    if match is None:
        if rule.required:
            return ("required-missing", None)
        return ("optional-missing", None)

    target = dest_dir / match.name
    error = run_with_lock_retries(
        lambda: shutil.copy2(match, target),
        description=f"copia de {match.name}",
        retries=retries,
        retry_delay_ms=retry_delay_ms,
    )
    if error is None:
        return ("copied", target)
    if is_locked_file_error(error):
        return ("locked", target)
    raise error


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
        clean_destination(
            dest_dir,
            retries=max(0, args.copy_retries),
            retry_delay_ms=max(0, args.copy_retry_delay_ms),
        )

    copied_count = 0
    required_missing: list[str] = []
    optional_missing: list[str] = []
    locked_artifacts: list[str] = []
    for rule in (*REQUIRED_RULES, *OPTIONAL_RULES):
        status, target = copy_rule(
            source_dir,
            dest_dir,
            rule,
            retries=max(0, args.copy_retries),
            retry_delay_ms=max(0, args.copy_retry_delay_ms),
        )
        if status == "copied" and target is not None:
            copied_count += 1
            print(f"Copiado: {target.name}")
        elif status == "required-missing":
            required_missing.append(rule.pattern)
            print(f"Obrigatorio ausente: {rule.pattern}")
        elif status == "optional-missing":
            optional_missing.append(rule.pattern)
            print(f"Opcional ausente: {rule.pattern}")
        elif status == "locked" and target is not None:
            locked_artifacts.append(target.name)
            print(f"Aviso: mantendo versao atual de {target.name} porque o destino esta em uso.")

    print(f"Pacote latest-upload atualizado em: {dest_dir}")
    print(f"Arquivos copiados: {copied_count}")
    if required_missing:
        joined = ", ".join(required_missing)
        print(f"Obrigatorios ausentes: {joined}", file=sys.stderr)
        if args.strict:
            return 1
    if locked_artifacts:
        joined = ", ".join(locked_artifacts)
        print(f"Arquivos bloqueados no destino: {joined}", file=sys.stderr)
        if args.strict:
            return 1
    if optional_missing:
        joined = ", ".join(optional_missing)
        print(f"Opcionais ausentes: {joined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
