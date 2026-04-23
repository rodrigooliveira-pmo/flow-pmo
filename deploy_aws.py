#!/usr/bin/env python3
"""Deploy completo na AWS (ECR + App Runner) com tratamento cross-platform.

Deploy voltado para o ambiente AWS (ECR + App Runner).
Fluxo:
  1. Login no ECR
  2. Build da imagem Docker
  3. Push da imagem ao ECR
  4. Atualiza o servico App Runner com a nova imagem

Pré-requisitos:
  - AWS CLI instalada e configurada (aws configure ou env vars)
  - Docker rodando localmente
  - Repositório ECR criado
  - Serviço App Runner criado e apontando para o ECR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


class DeployError(RuntimeError):
    """Erro controlado do fluxo de deploy."""


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


def require_env(env: dict[str, str], key: str) -> str:
    val = env.get(key, "").strip()
    if not val:
        raise DeployError(
            f"Variavel de ambiente obrigatoria nao definida: {key}. "
            f"Defina em .env, .env.local ou exporte no shell."
        )
    return val


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise DeployError(f"Ferramenta '{name}' nao encontrada no PATH.")
    return path


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
        raise DeployError(
            f"{step_name} falhou: executavel nao encontrado ({exc})."
        ) from exc

    if result.returncode != 0:
        details = ""
        if capture:
            details = (result.stderr or result.stdout or "").strip()
        if details:
            raise DeployError(
                f"{step_name} falhou (code {result.returncode}): {details}"
            )
        raise DeployError(f"{step_name} falhou (code {result.returncode}).")
    return result


def get_image_tag(repo_root: Path) -> str:
    """Gera tag da imagem: git short-sha ou timestamp-hash."""
    git_bin = shutil.which("git")
    if git_bin:
        try:
            result = subprocess.run(
                [git_bin, "rev-parse", "--short=10", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    # Fallback: timestamp + hash parcial do diretorio
    ts = str(int(time.time()))
    h = hashlib.sha256(str(repo_root).encode()).hexdigest()[:8]
    return f"{ts}-{h}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Deploy completo na AWS (ECR + App Runner) em um unico script Python."
        )
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Diretorio do projeto (padrao: diretorio atual).",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Tag da imagem Docker (padrao: git short SHA).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build Docker sem cache (--no-cache).",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Faz build local sem push ao ECR (para testes).",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Push ao ECR mas nao atualiza o App Runner.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra os passos sem executar.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Aguarda o App Runner concluir o deploy (poll status).",
    )
    return parser


def wait_for_service(
    aws_bin: str,
    service_arn: str,
    region: str,
    env: dict[str, str],
    repo_root: Path,
    timeout_seconds: int = 600,
    poll_interval: int = 15,
) -> None:
    """Poll App Runner service status until RUNNING or timeout."""
    print(f"\n[Aguardando deploy] Timeout: {timeout_seconds}s")
    elapsed = 0
    while elapsed < timeout_seconds:
        result = run_step(
            "Status check",
            [
                aws_bin, "apprunner", "describe-service",
                "--service-arn", service_arn,
                "--region", region,
                "--query", "Service.Status",
                "--output", "text",
            ],
            repo_root,
            env,
            capture=True,
        )
        status = (result.stdout or "").strip()
        print(f"  Status: {status} ({elapsed}s)")
        if status == "RUNNING":
            print("Servico App Runner esta RUNNING.")
            return
        if status in ("CREATE_FAILED", "DELETE_FAILED", "OPERATION_IN_PROGRESS"):
            if status.endswith("FAILED"):
                raise DeployError(f"App Runner em estado de falha: {status}")
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise DeployError(
        f"Timeout ({timeout_seconds}s) aguardando App Runner ficar RUNNING."
    )


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.cwd).resolve()
    env = os.environ.copy()

    # Carrega .env
    load_env_file(repo_root / ".env.local", env)
    load_env_file(repo_root / ".env", env)

    print(f"Sistema detectado: {platform.system()}")
    print(f"Diretorio do projeto: {repo_root}")

    # Valida pre-requisitos
    try:
        aws_bin = require_tool("aws")
        docker_bin = require_tool("docker")
        account_id = require_env(env, "AWS_ACCOUNT_ID")
        region = require_env(env, "AWS_DEFAULT_REGION")
        ecr_repo = require_env(env, "ECR_REPOSITORY")
    except DeployError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    service_arn = env.get("APP_RUNNER_SERVICE_ARN", "").strip()
    if not args.skip_deploy and not service_arn:
        print(
            "Erro: APP_RUNNER_SERVICE_ARN nao definido. "
            "Defina para atualizar o servico, ou use --skip-deploy.",
            file=sys.stderr,
        )
        return 1

    # Verifica Dockerfile
    if not (repo_root / "Dockerfile").exists():
        print("Erro: Dockerfile nao encontrado.", file=sys.stderr)
        return 1

    tag = args.tag or get_image_tag(repo_root)
    ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    image_full = f"{ecr_uri}/{ecr_repo}:{tag}"
    image_latest = f"{ecr_uri}/{ecr_repo}:latest"

    print(f"ECR Repository: {ecr_repo}")
    print(f"Imagem: {image_full}")
    print(f"Regiao: {region}")
    if service_arn:
        print(f"App Runner ARN: {service_arn}")

    if args.dry_run:
        print("\n[DRY RUN] Fluxo planejado:")
        print(f"1) ECR login em {ecr_uri}")
        print(f"2) Docker build -> {image_full}")
        if not args.skip_push:
            print(f"3) Docker push -> {image_full}")
            print(f"   Docker push -> {image_latest}")
        if not args.skip_push and not args.skip_deploy:
            print(f"4) App Runner update-service -> {service_arn}")
        if args.wait:
            print("5) Aguardar App Runner RUNNING")
        return 0

    try:
        # 1) ECR Login
        login_result = run_step(
            "ECR login (get-login-password)",
            [aws_bin, "ecr", "get-login-password", "--region", region],
            repo_root,
            env,
            capture=True,
        )
        ecr_password = (login_result.stdout or "").strip()

        # Pipe password via stdin
        print(f"\n[Docker login ECR] {docker_bin} login --username AWS --password-stdin {ecr_uri}")
        login_proc = subprocess.run(
            [docker_bin, "login", "--username", "AWS", "--password-stdin", ecr_uri],
            input=ecr_password,
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
        )
        if login_proc.returncode != 0:
            raise DeployError(
                f"Docker login ECR falhou: {login_proc.stderr or login_proc.stdout}"
            )
        print("  Login ECR OK.")

        # 2) Docker build
        build_cmd = [docker_bin, "build", "-t", image_full, "-t", image_latest]
        if args.no_cache:
            build_cmd.append("--no-cache")
        build_cmd.append(".")
        run_step("Docker build", build_cmd, repo_root, env)

        if args.skip_push:
            print("\n--skip-push: imagem construida localmente, sem push.")
            return 0

        # 3) Docker push
        run_step("Docker push (tag)", [docker_bin, "push", image_full], repo_root, env)
        run_step("Docker push (latest)", [docker_bin, "push", image_latest], repo_root, env)

        if args.skip_deploy:
            print("\n--skip-deploy: imagem no ECR, sem atualizar App Runner.")
            return 0

        # 4) App Runner update-service
        source_config = json.dumps({
            "ImageRepository": {
                "ImageIdentifier": image_full,
                "ImageRepositoryType": "ECR",
                "ImageConfiguration": {
                    "Port": "8080",
                },
            },
        })
        run_step(
            "App Runner update-service",
            [
                aws_bin, "apprunner", "update-service",
                "--service-arn", service_arn,
                "--source-configuration", source_config,
                "--region", region,
            ],
            repo_root,
            env,
        )

        # 5) Aguardar (opcional)
        if args.wait:
            wait_for_service(aws_bin, service_arn, region, env, repo_root)

    except DeployError as exc:
        print(f"\nErro de deploy: {exc}", file=sys.stderr)
        print(
            "Sugestoes:\n"
            "  - Verifique se aws configure esta correto\n"
            "  - Verifique se Docker esta rodando\n"
            "  - Verifique se o repositorio ECR existe\n"
            "  - Verifique se APP_RUNNER_SERVICE_ARN esta correto",
            file=sys.stderr,
        )
        return 1

    print("\nDeploy AWS concluido com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
