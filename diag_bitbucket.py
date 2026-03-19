#!/usr/bin/env python3
"""
Diagnostico rapido da conexao Bitbucket para validar DevExecutor.
Testa credenciais, lista PRs de cada repo e mostra quais Jira keys encontra.

Uso:
  python diag_bitbucket.py
  python diag_bitbucket.py --env jira_env.txt --repo w1nner --limit 10
"""
import argparse
import os
import re
import sys

import requests

ENV_FILE   = "jira_env.txt"
JIRA_KEY_RE = re.compile(r'\b([A-Z][A-Z0-9_]*-\d+)\b')


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


def check_repo(workspace: str, repo: str, auth: tuple, limit: int) -> dict:
    url = (
        f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}"
        f"/pullrequests?state=MERGED&pagelen={min(limit, 50)}"
        f"&fields=values.id,values.title,values.author.display_name,values.source.branch.name"
    )
    try:
        resp = requests.get(url, auth=auth, headers={"Accept": "application/json"}, timeout=15)
    except Exception as e:
        return {"status": "ERRO_CONEXAO", "erro": str(e), "prs": 0, "keys": []}

    if resp.status_code == 401:
        return {"status": "ERRO_AUTH", "erro": "Credenciais invalidas (401)", "prs": 0, "keys": []}
    if resp.status_code == 404:
        return {"status": "REPO_NAO_ENCONTRADO", "erro": f"404 - repo '{repo}' nao encontrado", "prs": 0, "keys": []}
    if not resp.ok:
        return {"status": f"ERRO_HTTP_{resp.status_code}", "erro": resp.text[:120], "prs": 0, "keys": []}

    data  = resp.json()
    prs   = data.get("values", [])
    total = data.get("size", len(prs))
    keys_found = []
    for pr in prs:
        author = (pr.get("author") or {}).get("display_name", "")
        title  = pr.get("title") or ""
        branch = (pr.get("source") or {}).get("branch", {}).get("name") or ""
        for text in (title, branch):
            for m in JIRA_KEY_RE.finditer(text):
                keys_found.append((m.group(1), author, title[:60]))

    return {"status": "OK", "prs": total, "sample": prs[:3], "keys": keys_found[:20]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env",   default=ENV_FILE)
    parser.add_argument("--repo",  default="",  help="Testar apenas este repo (opcional)")
    parser.add_argument("--limit", default=20,  type=int, help="PRs por repo para amostra")
    args = parser.parse_args()

    load_env_file(args.env)

    workspace = os.getenv("BB_WORKSPACE", "").strip()
    username  = os.getenv("BB_EMAIL",     "").strip()
    token     = os.getenv("BB_TOKEN",     "").strip()
    repos_raw = (os.getenv("BB_REPOS", "") or os.getenv("BB_REPO", "")).strip()
    repos     = [r.strip() for r in repos_raw.split(",") if r.strip()]

    if args.repo:
        repos = [args.repo]

    print("=" * 60)
    print("DIAGNOSTICO BITBUCKET — DevExecutor")
    print("=" * 60)
    print(f"  Workspace : {workspace or '(nao definido)'}")
    print(f"  Usuario   : {username  or '(nao definido)'}")
    print(f"  Token     : {'OK (' + token[:8] + '...)' if token else '(nao definido)'}")
    print(f"  BB_REPOS  : {repos_raw or '(nao definido)'}")
    print(f"  Repos     : {len(repos)} repo(s)")

    if not workspace or not username or not token:
        print("\n  FALHA: BB_WORKSPACE, BB_EMAIL ou BB_TOKEN nao definidos em", args.env)
        sys.exit(1)
    if not repos:
        print("\n  FALHA: BB_REPOS ou BB_REPO nao definidos em", args.env)
        sys.exit(1)

    auth = (username, token)

    # Testa autenticacao generica
    print("\n[1] Testando autenticacao...")
    try:
        r = requests.get(
            f"https://api.bitbucket.org/2.0/workspaces/{workspace}",
            auth=auth, timeout=10
        )
        if r.status_code == 200:
            print(f"    OK — workspace '{workspace}' acessivel.")
        elif r.status_code == 401:
            print("    FALHA — Credenciais invalidas (401). Verifique BB_EMAIL e BB_TOKEN.")
            sys.exit(1)
        elif r.status_code == 403:
            print("    FALHA — Sem permissao para o workspace (403).")
            sys.exit(1)
        else:
            print(f"    AVISO — Status {r.status_code}: {r.text[:80]}")
    except Exception as e:
        print(f"    FALHA — Erro de conexao: {e}")
        sys.exit(1)

    # Testa cada repo
    print(f"\n[2] Testando {len(repos)} repo(s) — buscando ate {args.limit} PRs cada...")
    all_keys = {}
    ok_count = 0
    for repo in repos:
        result = check_repo(workspace, repo, auth, args.limit)
        status = result["status"]
        if status == "OK":
            ok_count += 1
            n_keys = len(result["keys"])
            print(f"    OK   {repo:<40} {result['prs']:>5} PRs merged  |  {n_keys} Jira keys na amostra")
            for jira_key, author, title in result["keys"]:
                all_keys[jira_key] = author
        else:
            print(f"    ERRO {repo:<40} {result['erro']}")

    print(f"\n[3] Resumo das Jira keys encontradas nos PRs (amostra de {args.limit} PRs/repo):")
    if not all_keys:
        print("    ATENCAO: nenhuma Jira key encontrada nos titulos/branches dos PRs.")
        print("    Verifique se os PRs seguem o padrao 'W1NNR-123: descricao' ou branch 'feature/W1NNR-123-...'")
    else:
        print(f"    {len(all_keys)} issue(s) encontrada(s). Amostra:")
        for jira_key, author in list(all_keys.items())[:20]:
            print(f"      {jira_key:<18} -> {author}")

    print(f"\n[4] Conclusao: {ok_count}/{len(repos)} repos acessiveis.")
    if ok_count == len(repos) and all_keys:
        print("    PRONTO para rodar .\\run_all_projects.ps1")
    elif ok_count == len(repos) and not all_keys:
        print("    Conexao OK mas PRs sem Jira key no titulo/branch.")
        print("    O DevExecutor ficara vazio para os PRs sem padrao de nomenclatura.")
    else:
        print("    Corrija os erros acima antes de rodar a extracao.")


if __name__ == "__main__":
    main()
