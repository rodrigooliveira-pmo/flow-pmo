#!/usr/bin/env python3
"""Deploy completo na Vercel com tratamento cross-platform (Windows/macOS)."""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


class DeployError(RuntimeError):
    """Erro controlado do fluxo de deploy."""


VERCEL_TOKEN_ALLOWED_RE = re.compile(r"^[A-Za-z0-9_]+$")


def load_env_file(path: Path, env: dict[str, str]) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in env:
            env[key] = value


def resolve_vercel_bin(repo_root: Path) -> list[str]:
    local_bin = repo_root / "node_modules" / ".bin" / (
        "vercel.cmd" if os.name == "nt" else "vercel"
    )
    if local_bin.exists():
        return [str(local_bin)]

    # Fallback robusto quando o link em node_modules/.bin nao existe,
    # mas o pacote vercel esta instalado localmente.
    local_js_cli = repo_root / "node_modules" / "vercel" / "dist" / "index.js"
    node_bin = shutil.which("node")
    if local_js_cli.exists() and node_bin:
        return [node_bin, str(local_js_cli)]

    global_bin = shutil.which("vercel")
    if global_bin:
        return [global_bin]

    npx_bin = shutil.which("npx")
    if npx_bin:
        return [npx_bin, "--yes", "vercel"]

    raise DeployError(
        "Vercel CLI nao encontrada. Rode `npm i` (local) ou `npm i -g vercel`."
    )


def run_step(
    step_name: str,
    cmd: list[str],
    repo_root: Path,
    env: dict[str, str],
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(f"\n[{step_name}] {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=capture,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DeployError(f"{step_name} falhou: executavel nao encontrado ({exc}).") from exc

    if result.returncode != 0:
        details = ""
        if capture:
            details = (result.stderr or result.stdout or "").strip()
        if details:
            raise DeployError(f"{step_name} falhou (code {result.returncode}): {details}")
        raise DeployError(f"{step_name} falhou (code {result.returncode}).")

    return result


def ensure_project_files(repo_root: Path) -> None:
    has_vercel_json = (repo_root / "vercel.json").exists()
    has_api_entrypoint = (repo_root / "api" / "index.py").exists()
    if not has_vercel_json and not has_api_entrypoint:
        raise DeployError(
            "Projeto nao parece pronto para Vercel: faltam `vercel.json` e `api/index.py`."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Deploy completo na Vercel em um unico script Python "
            "(Windows e macOS)."
        )
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("prod", "preview"),
        default="prod",
        help="Tipo de deploy: prod (padrao) ou preview.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Diretorio do projeto (padrao: diretorio atual).",
    )
    parser.add_argument(
        "--no-link",
        action="store_true",
        help="Pula etapa de `vercel link` quando ja estiver tudo configurado.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Executa Vercel CLI sem prompts interativos (`--yes`).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra os passos sem executar comandos de deploy.",
    )
    return parser


def normalize_vercel_token(env: dict[str, str]) -> tuple[bool, str]:
    token = env.get("VERCEL_TOKEN", "").strip()
    if not token:
        if env.get("VERCEL_OIDC_TOKEN"):
            return False, (
                "VERCEL_OIDC_TOKEN detectado, mas ele nao e usado como VERCEL_TOKEN "
                "(formato incompativel com a CLI)."
            )
        return False, "Nenhum VERCEL_TOKEN detectado; usando sessao local (vercel login)."

    if not VERCEL_TOKEN_ALLOWED_RE.fullmatch(token):
        env.pop("VERCEL_TOKEN", None)
        return False, (
            "VERCEL_TOKEN invalido para a CLI (caracteres nao permitidos). "
            "Token removido da execucao atual; usando sessao local."
        )
    return True, "VERCEL_TOKEN valido detectado."


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.cwd).resolve()
    env = os.environ.copy()

    load_env_file(repo_root / ".env.local", env)
    load_env_file(repo_root / ".env", env)
    has_usable_token, token_message = normalize_vercel_token(env)

    try:
        ensure_project_files(repo_root)
        vercel_cmd = resolve_vercel_bin(repo_root)
    except DeployError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    environment = "production" if args.mode == "prod" else "preview"
    deploy_cmd = [*vercel_cmd, "deploy"]
    if args.mode == "prod":
        deploy_cmd.append("--prod")
    if args.yes:
        deploy_cmd.append("--yes")

    link_cmd = [*vercel_cmd, "link"]
    pull_cmd = [*vercel_cmd, "pull", "--environment", environment]
    whoami_cmd = [*vercel_cmd, "whoami"]
    if args.yes:
        link_cmd.append("--yes")
        pull_cmd.append("--yes")

    print(f"Sistema detectado: {platform.system()}")
    print(f"Diretorio do projeto: {repo_root}")
    print(f"Modo de deploy: {args.mode}")
    print(f"Token detectado: {'sim' if has_usable_token else 'nao'}")
    print(f"Auth: {token_message}")

    if args.dry_run:
        print("\n[DRY RUN] Fluxo planejado:")
        print("1) whoami")
        if not args.no_link:
            print("2) link")
            print("3) pull")
            print("4) deploy")
        else:
            print("2) pull")
            print("3) deploy")
        return 0

    try:
        run_step("Autenticacao (whoami)", whoami_cmd, repo_root, env, capture=True)
        if not args.no_link:
            run_step("Vinculo de projeto (link)", link_cmd, repo_root, env)
        run_step("Sincronizacao de ambiente (pull)", pull_cmd, repo_root, env)
        run_step("Deploy", deploy_cmd, repo_root, env)
    except DeployError as exc:
        print(f"\nErro de deploy: {exc}", file=sys.stderr)
        print(
            "Sugestao: rode `vercel login` (ou configure VERCEL_TOKEN) e tente novamente.",
            file=sys.stderr,
        )
        return 1

    print("\nDeploy concluido com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
