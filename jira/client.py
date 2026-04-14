"""Cliente HTTP compartilhado para a API Jira Cloud.

Utilizado por jira_to_pipeline_csv.py e jira_portfolio_to_csv.py.

Estratégia de busca (3 tentativas em ordem):
  1. POST  /rest/api/3/search/jql  — API enhanced (Jira Cloud moderno)
  2. GET   /rest/api/3/search/jql  — API enhanced, variante GET
  3. GET   /rest/api/3/search      — fallback legado (→ /rest/api/2/search se 4xx)

Retry com exponential backoff em 429/5xx.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests


class JiraClient:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout: int = 60,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        pool_maxsize: int = 32,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=pool_maxsize,
            pool_maxsize=pool_maxsize,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _retry_delay(self, attempt: int, retry_after_header: Optional[str]) -> float:
        if retry_after_header:
            try:
                return max(0.0, float(retry_after_header))
            except ValueError:
                pass
        return self.backoff_factor * (2 ** attempt)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"

        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self._retry_delay(attempt, retry_after_header=None))
                continue

            if resp.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                delay = self._retry_delay(attempt, retry_after_header=resp.headers.get("Retry-After"))
                time.sleep(delay)
                continue

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"Falha inesperada ao consultar Jira: {method} {url}")

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path=path, params=params)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", path=path, payload=payload)

    def get_myself(self) -> Dict[str, Any]:
        try:
            return self._get("/rest/api/3/myself")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in {400, 401, 404, 405, 410}:
                return self._get("/rest/api/2/myself")
            raise

    def search_projects(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"query": str(query or "").strip(), "maxResults": max_results}
        payload = self._get("/rest/api/3/project/search", params=params)
        values = payload.get("values", []) if isinstance(payload, dict) else []
        return values if isinstance(values, list) else []

    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        try:
            return self._get(f"/rest/api/3/issue/{issue_key}", params=params or None)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in {400, 404, 405, 410}:
                return self._get(f"/rest/api/2/issue/{issue_key}", params=params or None)
            raise

    def search_issues(
        self,
        jql: str,
        fields: List[str],
        page_size: int = 100,
        expand: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Busca issues via JQL com fallback automático entre endpoints.

        Tenta enhanced POST → enhanced GET → legacy, retornando ao primeiro
        que retornar resultados ou lançando RuntimeError se todos falharem.
        """
        errors: List[str] = []
        empty_attempts: List[str] = []

        # Preferred endpoint (new enhanced search API) - POST.
        try:
            issues = self._search_issues_enhanced_post(jql=jql, fields=fields, page_size=page_size, expand=expand)
            if issues:
                return issues
            empty_attempts.append("enhanced_post")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            errors.append(f"enhanced_post:{status}")

        # Enhanced search API - GET variant.
        try:
            issues = self._search_issues_enhanced_get(jql=jql, fields=fields, page_size=page_size, expand=expand)
            if issues:
                return issues
            empty_attempts.append("enhanced_get")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            errors.append(f"enhanced_get:{status}")

        # If enhanced endpoints worked and simply returned zero issues, do not
        # fallback to legacy search. Zero results are valid responses.
        if empty_attempts and not errors:
            return []

        # Fallback for tenants still on legacy behavior.
        try:
            issues = self._search_issues_legacy(jql=jql, fields=fields, page_size=page_size, expand=expand)
            if issues:
                if empty_attempts:
                    print(
                        "Aviso: endpoints enhanced retornaram 0 issues; "
                        f"fallback legacy retornou {len(issues)} issue(s)."
                    )
                return issues
            if empty_attempts or errors:
                print(
                    "Aviso: endpoints enhanced e legacy retornaram 0 issues para a JQL informada. "
                    f"Tentativas vazias: {', '.join(empty_attempts)}."
                )
            return issues
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            errors.append(f"legacy:{status}")
            if empty_attempts and status == 410:
                print(
                    "Aviso: endpoint legacy de busca retornou 410 (Gone) nesta instância Jira Cloud. "
                    "Mantendo resultado vazio dos endpoints enhanced."
                )
                print(
                    "Aviso: endpoints enhanced retornaram 0 issues para a JQL informada. "
                    f"Tentativas vazias: {', '.join(empty_attempts)}."
                )
                return []
            msg = ", ".join(errors)
            raise RuntimeError(
                "Falha ao consultar issues no Jira. "
                f"Status por tentativa: {msg}. "
                "Verifique permissões/scopes do token e disponibilidade dos endpoints de busca."
            ) from exc

    def _search_issues_enhanced_post(
        self,
        jql: str,
        fields: List[str],
        page_size: int = 100,
        expand: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        seen_tokens: set[str] = set()

        while True:
            body: Dict[str, Any] = {
                "jql": jql,
                "maxResults": page_size,
                "fields": fields,
            }
            if expand:
                body["expand"] = expand
            if next_page_token:
                body["nextPageToken"] = next_page_token

            payload = self._post("/rest/api/3/search/jql", payload=body)
            if payload.get("warningMessages"):
                print(f"Aviso Jira (enhanced POST): {payload.get('warningMessages')}")
            if payload.get("errorMessages"):
                print(f"Erro Jira (enhanced POST): {payload.get('errorMessages')}")
            page_issues = payload.get("issues", [])
            issues.extend(page_issues)

            is_last = payload.get("isLast")
            next_page_token = payload.get("nextPageToken")

            if is_last is True:
                break
            if not next_page_token:
                if not page_issues or len(page_issues) < page_size:
                    break
                break
            if next_page_token in seen_tokens:
                break
            seen_tokens.add(next_page_token)

        return issues

    def _search_issues_enhanced_get(
        self,
        jql: str,
        fields: List[str],
        page_size: int = 100,
        expand: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        seen_tokens: set[str] = set()

        while True:
            params: Dict[str, Any] = {
                "jql": jql,
                "maxResults": page_size,
                "fields": ",".join(fields),
            }
            if expand:
                params["expand"] = ",".join(expand)
            if next_page_token:
                params["nextPageToken"] = next_page_token

            payload = self._get("/rest/api/3/search/jql", params=params)
            if payload.get("warningMessages"):
                print(f"Aviso Jira (enhanced GET): {payload.get('warningMessages')}")
            if payload.get("errorMessages"):
                print(f"Erro Jira (enhanced GET): {payload.get('errorMessages')}")
            page_issues = payload.get("issues", [])
            issues.extend(page_issues)

            is_last = payload.get("isLast")
            next_page_token = payload.get("nextPageToken")

            if is_last is True:
                break
            if not next_page_token:
                if not page_issues or len(page_issues) < page_size:
                    break
                break
            if next_page_token in seen_tokens:
                break
            seen_tokens.add(next_page_token)

        return issues

    def _search_issues_legacy(
        self,
        jql: str,
        fields: List[str],
        page_size: int = 100,
        expand: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        start_at = 0

        while True:
            params: Dict[str, Any] = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": page_size,
                "fields": ",".join(fields),
            }
            if expand:
                params["expand"] = ",".join(expand)
            try:
                payload = self._get("/rest/api/3/search", params=params)
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in {400, 404, 405, 410}:
                    payload = self._get("/rest/api/2/search", params=params)
                else:
                    raise
            page_issues = payload.get("issues", [])
            issues.extend(page_issues)

            total = int(payload.get("total", 0))
            start_at += len(page_issues)
            if not page_issues or start_at >= total:
                break

        return issues

    def get_issue_changelog(
        self,
        issue_key: str,
        page_size: int = 100,
        start_at: int = 0,
        initial_histories: Optional[List[Dict[str, Any]]] = None,
        total_hint: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retorna o changelog completo de uma issue, paginando automaticamente."""
        histories: List[Dict[str, Any]] = list(initial_histories or [])
        cursor = max(0, int(start_at))
        total = int(total_hint) if total_hint is not None else 0

        while True:
            payload = self._get(
                f"/rest/api/3/issue/{issue_key}/changelog",
                params={"startAt": cursor, "maxResults": page_size},
            )
            page_histories = payload.get("values", [])
            histories.extend(page_histories)

            if not total:
                total = int(payload.get("total", 0))
            cursor += len(page_histories)
            if not page_histories or (total > 0 and cursor >= total):
                break

        return histories

    def get_issue_worklogs(
        self,
        issue_key: str,
        page_size: int = 100,
        start_at: int = 0,
        initial_worklogs: Optional[List[Dict[str, Any]]] = None,
        total_hint: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retorna os worklogs completos de uma issue, paginando automaticamente."""
        worklogs: List[Dict[str, Any]] = list(initial_worklogs or [])
        cursor = max(0, int(start_at))
        total = int(total_hint) if total_hint is not None else 0

        while True:
            payload = self._get(
                f"/rest/api/3/issue/{issue_key}/worklog",
                params={"startAt": cursor, "maxResults": page_size},
            )
            page_worklogs = payload.get("worklogs", [])
            worklogs.extend(page_worklogs)

            if not total:
                total = int(payload.get("total", 0))
            cursor += len(page_worklogs)
            if not page_worklogs or (total > 0 and cursor >= total):
                break

        return worklogs

    def get_issue_comments(
        self,
        issue_key: str,
        page_size: int = 100,
        start_at: int = 0,
        initial_comments: Optional[List[Dict[str, Any]]] = None,
        total_hint: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retorna os comentários completos de uma issue, paginando automaticamente."""
        comments: List[Dict[str, Any]] = list(initial_comments or [])
        cursor = max(0, int(start_at))
        total = int(total_hint) if total_hint is not None else 0

        while True:
            payload = self._get(
                f"/rest/api/3/issue/{issue_key}/comment",
                params={"startAt": cursor, "maxResults": page_size},
            )
            page_comments = payload.get("comments", [])
            comments.extend(page_comments)

            if not total:
                total = int(payload.get("total", 0))
            cursor += len(page_comments)
            if not page_comments or (total > 0 and cursor >= total):
                break

        return comments

    def get_updated_worklog_ids(self, since_ms: int) -> List[Dict[str, Any]]:
        """Lista IDs de worklogs atualizados desde um timestamp em ms."""
        values: List[Dict[str, Any]] = []
        cursor = int(since_ms)

        while True:
            payload = self._get("/rest/api/3/worklog/updated", params={"since": cursor})
            page_values = payload.get("values", [])
            if isinstance(page_values, list):
                values.extend(page_values)

            if payload.get("lastPage") is True:
                break

            next_cursor = payload.get("until")
            try:
                next_cursor_int = int(next_cursor)
            except (TypeError, ValueError):
                break
            if next_cursor_int <= cursor:
                break
            cursor = next_cursor_int

        return values

    def get_worklogs_by_ids(self, worklog_ids: List[int | str]) -> List[Dict[str, Any]]:
        """Busca detalhes de worklogs por ID via endpoint global."""
        cleaned_ids: List[int] = []
        for worklog_id in worklog_ids:
            try:
                cleaned_ids.append(int(worklog_id))
            except (TypeError, ValueError):
                continue

        if not cleaned_ids:
            return []

        worklogs: List[Dict[str, Any]] = []
        for start in range(0, len(cleaned_ids), 1000):
            chunk = cleaned_ids[start : start + 1000]
            payload = self._post("/rest/api/3/worklog/list", payload={"ids": chunk})
            if isinstance(payload, list):
                worklogs.extend(payload)
        return worklogs

    def list_visible_projects(self, page_size: int = 50) -> List[Dict[str, Any]]:
        """Lista projetos visíveis para o token autenticado."""
        payload = self._get("/rest/api/3/project/search", params={"maxResults": page_size})
        return payload.get("values", [])
