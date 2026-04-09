#!/usr/bin/env python3
"""
Builds a GMUD coverage index by correlating delivery items with CHG tickets.

Outputs:
  - detailed item-level base with evidence
  - executive summary index
  - weekly historical series
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import pandas as pd

from jira.client import JiraClient
from shared.env_utils import load_env_file
from shared.text_utils import normalize_text


ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9_]*-\d+\b")
DONE_STATUS_HINTS = {
    "done",
    "concluido",
    "concluida",
    "closed",
    "resolved",
    "finalizado",
    "finalizada",
}
BUG_TYPE_HINTS = {"bug", "incident", "incidente", "problem", "problema", "bug incident", "bug/incident"}
FEATURE_TYPE_HINTS = {"feature", "funcionalidade"}
EPIC_TYPE_HINTS = {"epic", "epico", "epico de portfolio", "epico portfolio"}
SIMILARITY_STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "em", "para", "com", "sem", "na", "no", "nas", "nos",
    "a", "o", "as", "os", "por", "que", "ao", "aos", "ou", "via", "uma", "um", "mais", "menos",
    "web", "front", "back", "mobile", "feature", "implantacao", "implantacao", "correcao", "correcoes",
    "ajuste", "ajustes", "script", "pagina", "tela", "novo", "nova", "novas", "novos",
}
SIMILARITY_WEAK_TOKENS = {
    "erro", "erros", "dados", "layout", "cliente", "clientes", "admin", "perfil", "tela",
    "ajuste", "ajustes", "correcao", "correcoes", "mudancas", "mudanca", "problema", "problemas",
    "status", "front", "back", "mobile", "logs", "log", "query",
}
STORY_TYPE_HINTS = {"story", "user story", "historia", "historia de usuario"}
TASK_TYPE_HINTS = {"task", "tarefa", "sub task", "subtarefa", "tech task", "task de produto", "ad hoc", "adhoc"}
PRODUCTION_DATE_COLUMNS = [
    "Ready for production",
    "Ready For Production",
    "ready for production",
]
DONE_DATE_COLUMNS = [
    "Done",
    "Itens concluídos",
    "Itens Concluidos",
    "Concluído",
    "Concluido",
    "Closed",
    "Resolved",
]
COMMENT_SIGNAL_HINTS = [
    "producao",
    "production",
    "deploy",
    "release",
    "rollback",
    "janela",
    "gmud",
    "mudanca",
    "change",
]
GMUD_ROLLBACK_FIELD = "customfield_10798"
GMUD_CONFIG_ITEMS_FIELD = "customfield_10802"
GMUD_RELATED_CARDS_FIELD = "customfield_11366"


def safe_get(mapping: Any, *keys: str) -> Any:
    current = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def format_list(values: Iterable[str]) -> str:
    cleaned = [str(v).strip() for v in values if str(v).strip()]
    return ", ".join(cleaned)


def split_csv_tokens(value: Any) -> List[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def sorted_join(values: Iterable[str]) -> str:
    return ", ".join(sorted({str(v).strip() for v in values if str(v).strip()}))


def adf_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [adf_to_text(item) for item in value]
        return "\n".join([part for part in parts if part.strip()]).strip()
    if not isinstance(value, dict):
        return str(value).strip()

    node_type = str(value.get("type") or "").strip()
    if node_type == "text":
        text = str(value.get("text") or "")
        marks = value.get("marks") if isinstance(value.get("marks"), list) else []
        link_targets: List[str] = []
        for mark in marks:
            if not isinstance(mark, dict):
                continue
            if str(mark.get("type") or "").strip() != "link":
                continue
            href = str(safe_get(mark, "attrs", "href") or "").strip()
            if href and href not in link_targets and href not in text:
                link_targets.append(href)
        if link_targets:
            extra = " ".join(link_targets)
            return f"{text} {extra}".strip()
        return text
    if node_type in {"mention", "emoji"}:
        attrs = value.get("attrs") or {}
        return str(attrs.get("text") or attrs.get("shortName") or attrs.get("id") or "").strip()
    if node_type in {"inlineCard", "blockCard", "embedCard"}:
        attrs = value.get("attrs") or {}
        return str(attrs.get("url") or attrs.get("data") or "").strip()
    if node_type == "hardBreak":
        return "\n"

    content = value.get("content")
    if isinstance(content, list):
        parts = [adf_to_text(item) for item in content]
        if node_type in {"paragraph", "heading", "blockquote", "listItem"}:
            return " ".join([part for part in parts if part.strip()]).strip()
        return "\n".join([part for part in parts if part.strip()]).strip()

    return str(value.get("text") or "").strip()


def build_issue_links_summary(issue_links: Any) -> Dict[str, str]:
    if not isinstance(issue_links, list):
        return {
            "IssueLinkKeys": "",
            "IssueLinkTypes": "",
            "IssueLinkDetails": "",
        }

    keys: List[str] = []
    types: List[str] = []
    details: List[str] = []
    for link in issue_links:
        if not isinstance(link, dict):
            continue
        link_type = link.get("type") or {}
        outward_issue = link.get("outwardIssue") or {}
        inward_issue = link.get("inwardIssue") or {}
        direction = ""
        issue_ref = {}
        relation_name = ""
        if outward_issue:
            direction = "outward"
            issue_ref = outward_issue
            relation_name = str(link_type.get("outward") or link_type.get("name") or "").strip()
        elif inward_issue:
            direction = "inward"
            issue_ref = inward_issue
            relation_name = str(link_type.get("inward") or link_type.get("name") or "").strip()
        else:
            continue

        linked_key = str(issue_ref.get("key") or "").strip()
        linked_summary = str(safe_get(issue_ref, "fields", "summary") or "").strip()
        linked_type = str(safe_get(issue_ref, "fields", "issuetype", "name") or "").strip()
        link_type_name = str(link_type.get("name") or "").strip()
        if linked_key:
            keys.append(linked_key)
        if relation_name:
            types.append(relation_name)
        elif link_type_name:
            types.append(link_type_name)
        detail_parts = [part for part in [direction, relation_name or link_type_name, linked_key, linked_type, linked_summary] if part]
        if detail_parts:
            details.append(" | ".join(detail_parts))

    return {
        "IssueLinkKeys": format_list(keys),
        "IssueLinkTypes": format_list(types),
        "IssueLinkDetails": " || ".join(details),
    }


def extract_issue_keys_from_text(*parts: Any) -> List[str]:
    tokens: Set[str] = set()
    for part in parts:
        text = str(part or "")
        for match in ISSUE_KEY_RE.findall(text.upper()):
            tokens.add(match.strip())
    return sorted(tokens)


def normalize_type_bucket(issue_type: Any, hierarchy_level: str, feature_link: str, epic_link: str) -> str:
    norm = normalize_text(issue_type)
    if norm in BUG_TYPE_HINTS:
        return "Bug"
    if hierarchy_level in {"Epic", "Feature"} or norm in STORY_TYPE_HINTS or feature_link or epic_link:
        return "Melhoria"
    if norm in TASK_TYPE_HINTS or "task" in norm or "adhoc" in norm:
        return "Manutencao"
    return "Melhoria"


def infer_hierarchy_level(issue_type: Any) -> str:
    norm = normalize_text(issue_type)
    if norm in EPIC_TYPE_HINTS:
        return "Epic"
    if norm in FEATURE_TYPE_HINTS:
        return "Feature"
    return "Item"


def parse_datetime_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True, utc=True)
    if getattr(parsed.dt, "tz", None) is not None:
        parsed = parsed.dt.tz_convert(None)
    return parsed


def first_available_date(df: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    result = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    for col in columns:
        if col not in df.columns:
            continue
        parsed = parse_datetime_series(df[col])
        result = result.where(result.notna(), parsed)
    return result


def infer_project_from_key(value: Any) -> str:
    key = str(value or "").strip()
    if "-" not in key:
        return ""
    return key.split("-", 1)[0].upper()


def normalize_service_team(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    aliases = {
        "W1NNR": "W1NNR",
        "W1NNER": "W1NNR",
        "S1NC": "S1NC",
        "SYNC": "S1NC",
        "BF": "BF",
        "BEFINANCE": "BF",
        "DT": "DT",
        "DATA&ANALYTICS": "DT",
        "DATA ANALYTICS": "DT",
        "TECH W1NNER": "W1NNR",
        "SQUAD | W1NNER": "W1NNR",
        "TECH S1NC": "S1NC",
        "SQUAD | S1NC": "S1NC",
        "TECH BEFINANCE": "BF",
        "TECH DATA": "DT",
    }
    norm = normalize_text(text).upper()
    return aliases.get(norm, text.upper())


def text_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column].astype(str)
    return pd.Series("", index=df.index, dtype=str)


def build_reference_keys(row: pd.Series) -> List[str]:
    refs: List[str] = []
    for col in ["ItemKey", "ParentID", "FeatureLinkID", "EpicLinkID"]:
        value = str(row.get(col) or "").strip().upper()
        if value and value not in refs:
            refs.append(value)
    return refs


def load_operational_items(paths: Sequence[str]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for path in paths:
        csv_path = str(path or "").strip()
        if not csv_path:
            continue
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        if df.empty:
            continue
        out = pd.DataFrame()
        out["ItemKey"] = text_series(df, "ID").str.strip().str.upper()
        out["Projeto"] = text_series(df, "Space").str.strip().replace("", pd.NA)
        out["Projeto"] = out["Projeto"].fillna(out["ItemKey"].apply(infer_project_from_key))
        out["ServiceTeam"] = out["Projeto"].fillna("").astype(str).apply(normalize_service_team)
        out["Titulo"] = text_series(df, "Title")
        out["Tipo"] = text_series(df, "Tipo de Problema")
        out["HierarchyLevel"] = out["Tipo"].apply(infer_hierarchy_level)
        out["ParentID"] = text_series(df, "ParentID").str.strip().str.upper()
        out["FeatureLinkID"] = text_series(df, "FeatureLinkID").str.strip().str.upper()
        out["EpicLinkID"] = text_series(df, "EpicLinkID").str.strip().str.upper()
        out["IssueLinkKeys"] = text_series(df, "IssueLinkKeys")
        out["IssueLinkTypes"] = text_series(df, "IssueLinkTypes")
        out["IssueLinkDetails"] = text_series(df, "IssueLinkDetails")
        out["ReadyForProductionDate"] = first_available_date(df, PRODUCTION_DATE_COLUMNS)
        out["DoneDate"] = first_available_date(df, DONE_DATE_COLUMNS)
        out["ReferenceDate"] = out["ReadyForProductionDate"].where(out["ReadyForProductionDate"].notna(), out["DoneDate"])
        out["Status"] = ""
        out["StatusChangedAt"] = pd.NaT
        out["EligibleForGMUD"] = out["ReferenceDate"].notna()
        out["DeliveryBucket"] = out.apply(
            lambda row: normalize_type_bucket(
                row.get("Tipo"),
                str(row.get("HierarchyLevel") or ""),
                str(row.get("FeatureLinkID") or ""),
                str(row.get("EpicLinkID") or ""),
            ),
            axis=1,
        )
        out["Source"] = "downstream"
        out["SourceFile"] = csv_path
        frames.append(out)
    if not frames:
        return pd.DataFrame()
    base = pd.concat(frames, ignore_index=True)
    base = base[base["ItemKey"].ne("")].copy()
    base["ReferenceKeys"] = base.apply(build_reference_keys, axis=1)
    base["DirectLinkedCHGKeys"] = base["IssueLinkKeys"].apply(
        lambda value: sorted_join(token for token in split_csv_tokens(value.upper()) if token.startswith("CHG-"))
    )
    return base


def load_portfolio_items(path: str) -> pd.DataFrame:
    if not str(path or "").strip():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["ItemKey"] = text_series(df, "ID").str.strip().str.upper()
    out["Projeto"] = text_series(df, "Projeto").str.strip()
    team_series = text_series(df, "Team").str.strip()
    out["ServiceTeam"] = team_series.where(team_series.ne(""), out["Projeto"]).apply(normalize_service_team)
    out["Titulo"] = text_series(df, "Titulo")
    out["Tipo"] = text_series(df, "Tipo")
    out["HierarchyLevel"] = out["Tipo"].apply(infer_hierarchy_level)
    out["ParentID"] = text_series(df, "ParentID").str.strip().str.upper()
    out["FeatureLinkID"] = text_series(df, "FeatureLinkID").str.strip().str.upper()
    out["EpicLinkID"] = text_series(df, "EpicLinkID").str.strip().str.upper()
    out["IssueLinkKeys"] = text_series(df, "IssueLinkKeys")
    out["IssueLinkTypes"] = text_series(df, "IssueLinkTypes")
    out["IssueLinkDetails"] = text_series(df, "IssueLinkDetails")
    out["Status"] = text_series(df, "Status")
    out["StatusChangedAt"] = parse_datetime_series(text_series(df, "StatusChangedAt"))
    out["ReadyForProductionDate"] = pd.NaT
    done_mask = out["Status"].apply(lambda value: normalize_text(value) in DONE_STATUS_HINTS)
    out["DoneDate"] = out["StatusChangedAt"].where(done_mask, pd.NaT)
    out["ReferenceDate"] = out["DoneDate"]
    out["EligibleForGMUD"] = out["ReferenceDate"].notna()
    out["DeliveryBucket"] = out.apply(
        lambda row: normalize_type_bucket(
            row.get("Tipo"),
            str(row.get("HierarchyLevel") or ""),
            str(row.get("FeatureLinkID") or ""),
            str(row.get("EpicLinkID") or ""),
        ),
        axis=1,
    )
    out["Source"] = "portfolio"
    out["SourceFile"] = str(path)
    out = out[out["ItemKey"].ne("")].copy()
    out["ReferenceKeys"] = out.apply(build_reference_keys, axis=1)
    out["DirectLinkedCHGKeys"] = out["IssueLinkKeys"].apply(
        lambda value: sorted_join(token for token in split_csv_tokens(value.upper()) if token.startswith("CHG-"))
    )
    return out


def build_delivery_base(downstream_csvs: Sequence[str], portfolio_csv: str) -> pd.DataFrame:
    frames = []
    downstream = load_operational_items(downstream_csvs)
    if not downstream.empty:
        frames.append(downstream)
    portfolio = load_portfolio_items(portfolio_csv)
    if not portfolio.empty:
        frames.append(portfolio)
    if not frames:
        return pd.DataFrame()

    base = pd.concat(frames, ignore_index=True)
    base = base.drop_duplicates(subset=["ItemKey"], keep="first").reset_index(drop=True)
    return base


def comment_signal_count(text: str) -> int:
    normalized = normalize_text(text)
    return sum(1 for token in COMMENT_SIGNAL_HINTS if token in normalized)


def extract_customfield_rich_text(fields_data: Dict[str, Any]) -> str:
    texts: List[str] = []
    for key, value in (fields_data or {}).items():
        if not str(key or "").startswith("customfield_"):
            continue
        text = adf_to_text(value)
        if text and text not in texts:
            texts.append(text)
    return "\n".join(texts).strip()


def gmud_structured_field_texts(fields_data: Dict[str, Any]) -> Dict[str, str]:
    return {
        "RollbackFieldText": adf_to_text((fields_data or {}).get(GMUD_ROLLBACK_FIELD)),
        "ConfigItemsFieldText": adf_to_text((fields_data or {}).get(GMUD_CONFIG_ITEMS_FIELD)),
        "RelatedCardsFieldText": str((fields_data or {}).get(GMUD_RELATED_CARDS_FIELD) or "").strip(),
    }


def similarity_tokens(text: str) -> Set[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]{3,}", normalized)
    return {
        token for token in tokens
        if token not in SIMILARITY_STOPWORDS
    }


def infer_text_team_hints(text: str) -> Set[str]:
    normalized = normalize_text(text)
    hints: Set[str] = set()
    if "s1nc" in normalized or "sync" in normalized:
        hints.add("S1NC")
    if "w1nner" in normalized or "winner" in normalized:
        hints.add("W1NNR")
    if "befinance" in normalized or "be finance" in normalized:
        hints.add("BF")
    if "data analytics" in normalized or "data&analytics" in normalized or "dataanalytics" in normalized:
        hints.add("DT")
    return hints


def is_strong_text_similarity(item_tokens: Set[str], chg_tokens: Set[str]) -> bool:
    if not item_tokens or not chg_tokens:
        return False
    overlap = item_tokens & chg_tokens
    if len(overlap) < 2:
        return False
    distinctive_overlap = {
        token for token in overlap
        if token not in SIMILARITY_WEAK_TOKENS and len(token) >= 5
    }
    min_size = max(1, min(len(item_tokens), len(chg_tokens)))
    overlap_ratio = len(overlap) / float(min_size)
    if len(distinctive_overlap) >= 4:
        return True
    if len(distinctive_overlap) >= 3 and len(overlap) >= 3:
        return True
    if len(distinctive_overlap) >= 2 and len(overlap) >= 3 and overlap_ratio >= 0.6:
        return True
    if len(distinctive_overlap) >= 2 and len(overlap) >= 2 and overlap_ratio >= 0.95:
        return True
    return False


def fetch_chg_issues(
    client: JiraClient,
    base_url: str,
    jql: str,
    fetch_comments: bool,
) -> pd.DataFrame:
    fields = [
        "summary",
        "description",
        "issuetype",
        "status",
        "created",
        "updated",
        "resolutiondate",
        "project",
        "labels",
        "components",
        "fixVersions",
        "issuelinks",
        "comment",
    ]
    issues = client.search_issues(jql=jql, fields=fields)
    rows: List[Dict[str, Any]] = []
    for issue in issues:
        issue_key = str(issue.get("key") or "").strip().upper()
        fields_data = issue.get("fields", {}) or {}
        if issue_key:
            try:
                detailed_issue = client.get_issue(issue_key)
                detailed_fields = detailed_issue.get("fields", {}) if isinstance(detailed_issue, dict) else {}
                if isinstance(detailed_fields, dict) and detailed_fields:
                    fields_data = detailed_fields
            except Exception:
                pass
        comment_payload = fields_data.get("comment") or {}
        initial_comments = comment_payload.get("comments") if isinstance(comment_payload, dict) else []
        initial_comments = initial_comments if isinstance(initial_comments, list) else []
        total_comments = int(comment_payload.get("total", len(initial_comments) or 0)) if isinstance(comment_payload, dict) else len(initial_comments)
        comments = list(initial_comments)
        if fetch_comments and issue_key and (not comments or len(comments) < total_comments):
            comments = client.get_issue_comments(
                issue_key,
                start_at=len(initial_comments),
                initial_comments=initial_comments,
                total_hint=total_comments,
            )

        description_text = adf_to_text(fields_data.get("description"))
        customfield_text = extract_customfield_rich_text(fields_data)
        structured_field_texts = gmud_structured_field_texts(fields_data)
        comment_texts = [adf_to_text((comment or {}).get("body")) for comment in comments]
        full_comment_text = "\n".join([text for text in comment_texts if text.strip()]).strip()
        text_corpus = " ".join(
            segment for segment in [
                str(fields_data.get("summary") or "").strip(),
                description_text,
                customfield_text,
                full_comment_text,
            ]
            if str(segment or "").strip()
        ).strip()
        similarity_corpus = " ".join(
            segment for segment in [
                str(fields_data.get("summary") or "").strip(),
                description_text,
                customfield_text,
            ]
            if str(segment or "").strip()
        ).strip()
        issue_links_summary = build_issue_links_summary(fields_data.get("issuelinks"))
        linked_keys = [token.strip().upper() for token in split_csv_tokens(issue_links_summary.get("IssueLinkKeys", ""))]
        structured_keys = extract_issue_keys_from_text(
            structured_field_texts.get("RollbackFieldText"),
            structured_field_texts.get("ConfigItemsFieldText"),
            structured_field_texts.get("RelatedCardsFieldText"),
        )
        mentioned_keys = extract_issue_keys_from_text(fields_data.get("summary"), description_text, customfield_text, full_comment_text)
        comment_keys = extract_issue_keys_from_text(full_comment_text)

        rows.append(
            {
                "CHGKey": issue_key,
                "CHGLink": f"{base_url}/browse/{issue_key}" if issue_key else "",
                "Projeto": str(safe_get(fields_data, "project", "key") or "").strip(),
                "Summary": str(fields_data.get("summary") or "").strip(),
                "IssueType": str(safe_get(fields_data, "issuetype", "name") or "").strip(),
                "Status": str(safe_get(fields_data, "status", "name") or "").strip(),
                "CreatedAt": pd.to_datetime(fields_data.get("created"), errors="coerce", utc=True),
                "UpdatedAt": pd.to_datetime(fields_data.get("updated"), errors="coerce", utc=True),
                "ResolutionDate": pd.to_datetime(fields_data.get("resolutiondate"), errors="coerce", utc=True),
                "IssueLinkKeys": sorted_join(linked_keys),
                "IssueLinkTypes": issue_links_summary.get("IssueLinkTypes", ""),
                "IssueLinkDetails": issue_links_summary.get("IssueLinkDetails", ""),
                "StructuredIssueKeys": sorted_join(structured_keys),
                "RollbackFieldText": structured_field_texts.get("RollbackFieldText", ""),
                "ConfigItemsFieldText": structured_field_texts.get("ConfigItemsFieldText", ""),
                "RelatedCardsFieldText": structured_field_texts.get("RelatedCardsFieldText", ""),
                "MentionedIssueKeys": sorted_join(mentioned_keys),
                "CommentMentionedIssueKeys": sorted_join(comment_keys),
                "TextCorpus": text_corpus,
                "SimilarityCorpus": similarity_corpus,
                "CommentCount": len(comments),
                "CommentSignalCount": comment_signal_count(full_comment_text),
            }
        )
    chg_df = pd.DataFrame(rows)
    if chg_df.empty:
        return chg_df
    for col in ["CreatedAt", "UpdatedAt", "ResolutionDate"]:
        if col in chg_df.columns:
            series = chg_df[col]
            if getattr(series.dt, "tz", None) is not None:
                chg_df[col] = series.dt.tz_convert(None)
    return chg_df


def pick_primary_evidence(row: pd.Series) -> str:
    if str(row.get("DirectLinkedCHGKeys") or "").strip():
        return "Link explicito no item"
    if str(row.get("DirectExplicitCHGKeys") or "").strip():
        return "Link explicito na GMUD"
    if str(row.get("DirectStructuredCHGKeys") or "").strip():
        return "Campo estruturado da GMUD"
    if str(row.get("HierarchyExplicitCHGKeys") or "").strip():
        return "Link explicito via hierarquia"
    if str(row.get("HierarchyStructuredCHGKeys") or "").strip():
        return "Campo estruturado via hierarquia"
    if str(row.get("DirectCommentCHGKeys") or "").strip():
        return "Mencao em comentario da GMUD"
    if str(row.get("DirectTextCHGKeys") or "").strip():
        return "Mencao em resumo/descricao da GMUD"
    if str(row.get("DirectTitleMatchCHGKeys") or "").strip():
        return "Similaridade forte de titulo"
    if str(row.get("HierarchyCommentCHGKeys") or "").strip():
        return "Mencao em comentario via hierarquia"
    if str(row.get("HierarchyTextCHGKeys") or "").strip():
        return "Mencao em texto via hierarquia"
    if str(row.get("HierarchyTitleMatchCHGKeys") or "").strip():
        return "Similaridade forte via hierarquia"
    return "Sem GMUD"


def map_primary_bucket(evidence: str) -> str:
    if evidence.startswith("Link explicito") or evidence.startswith("Campo estruturado"):
        return "Explicita"
    if "comentario" in normalize_text(evidence):
        return "Comentario"
    normalized = normalize_text(evidence)
    if "texto" in normalized or "resumo" in normalized or "titulo" in normalized or "similaridade" in normalized:
        return "Texto"
    return "Sem GMUD"


def compute_gmud_coverage(items_df: pd.DataFrame, chg_df: pd.DataFrame) -> pd.DataFrame:
    explicit_ref_map: Dict[str, Set[str]] = defaultdict(set)
    structured_ref_map: Dict[str, Set[str]] = defaultdict(set)
    text_ref_map: Dict[str, Set[str]] = defaultdict(set)
    comment_ref_map: Dict[str, Set[str]] = defaultdict(set)
    title_match_ref_map: Dict[str, Set[str]] = defaultdict(set)
    chg_signal_map: Dict[str, int] = {}

    item_rows = items_df.to_dict(orient="records")
    item_title_token_map: Dict[str, Set[str]] = {
        str(row.get("ItemKey") or "").strip().upper(): similarity_tokens(row.get("Titulo"))
        for row in item_rows
        if str(row.get("ItemKey") or "").strip()
    }
    item_team_map: Dict[str, str] = {
        str(row.get("ItemKey") or "").strip().upper(): normalize_service_team(row.get("ServiceTeam") or row.get("Projeto"))
        for row in item_rows
        if str(row.get("ItemKey") or "").strip()
    }

    for row in chg_df.to_dict(orient="records"):
        chg_key = str(row.get("CHGKey") or "").strip().upper()
        if not chg_key:
            continue
        chg_signal_map[chg_key] = int(row.get("CommentSignalCount") or 0)

        explicit_refs = {token.strip().upper() for token in split_csv_tokens(row.get("IssueLinkKeys")) if token.strip()}
        explicit_refs.discard(chg_key)
        for ref in explicit_refs:
            explicit_ref_map[ref].add(chg_key)

        structured_refs = {token.strip().upper() for token in split_csv_tokens(row.get("StructuredIssueKeys")) if token.strip()}
        structured_refs.discard(chg_key)
        for ref in structured_refs:
            structured_ref_map[ref].add(chg_key)

        text_refs = {token.strip().upper() for token in split_csv_tokens(row.get("MentionedIssueKeys")) if token.strip()}
        text_refs.discard(chg_key)
        for ref in text_refs:
            text_ref_map[ref].add(chg_key)

        comment_refs = {token.strip().upper() for token in split_csv_tokens(row.get("CommentMentionedIssueKeys")) if token.strip()}
        comment_refs.discard(chg_key)
        for ref in comment_refs:
            comment_ref_map[ref].add(chg_key)

        chg_tokens = similarity_tokens(row.get("SimilarityCorpus") or row.get("Summary"))
        team_hints = infer_text_team_hints(row.get("SimilarityCorpus") or row.get("Summary"))
        if chg_tokens:
            for item_key, item_tokens in item_title_token_map.items():
                if team_hints:
                    item_team = item_team_map.get(item_key, "")
                    if item_team and item_team not in team_hints:
                        continue
                if is_strong_text_similarity(item_tokens, chg_tokens):
                    title_match_ref_map[item_key].add(chg_key)

    enriched = items_df.copy()
    direct_explicit_values: List[str] = []
    hierarchy_explicit_values: List[str] = []
    direct_structured_values: List[str] = []
    hierarchy_structured_values: List[str] = []
    direct_text_values: List[str] = []
    hierarchy_text_values: List[str] = []
    direct_comment_values: List[str] = []
    hierarchy_comment_values: List[str] = []
    direct_title_values: List[str] = []
    hierarchy_title_values: List[str] = []
    all_chg_values: List[str] = []
    matched_signal_counts: List[int] = []

    for _, row in enriched.iterrows():
        item_key = str(row.get("ItemKey") or "").strip().upper()
        refs = [str(ref).strip().upper() for ref in (row.get("ReferenceKeys") or []) if str(ref).strip()]
        ancestor_refs = [ref for ref in refs if ref != item_key]

        direct_linked = {token.strip().upper() for token in split_csv_tokens(row.get("DirectLinkedCHGKeys")) if token.strip()}
        direct_explicit = set(direct_linked) | explicit_ref_map.get(item_key, set())
        direct_structured = set(structured_ref_map.get(item_key, set()))
        hierarchy_explicit = set()
        hierarchy_structured = set()
        hierarchy_text = set()
        hierarchy_comment = set()
        hierarchy_title = set()
        for ref in ancestor_refs:
            hierarchy_explicit.update(explicit_ref_map.get(ref, set()))
            hierarchy_structured.update(structured_ref_map.get(ref, set()))
            hierarchy_text.update(text_ref_map.get(ref, set()))
            hierarchy_comment.update(comment_ref_map.get(ref, set()))
            hierarchy_title.update(title_match_ref_map.get(ref, set()))

        direct_text = set(text_ref_map.get(item_key, set()))
        direct_comment = set(comment_ref_map.get(item_key, set()))
        direct_title = set(title_match_ref_map.get(item_key, set()))
        all_chg = direct_explicit | hierarchy_explicit | direct_structured | hierarchy_structured | direct_text | hierarchy_text | direct_comment | hierarchy_comment | direct_title | hierarchy_title
        signal_count = sum(chg_signal_map.get(chg_key, 0) for chg_key in all_chg)

        direct_explicit_values.append(sorted_join(direct_explicit))
        hierarchy_explicit_values.append(sorted_join(hierarchy_explicit))
        direct_structured_values.append(sorted_join(direct_structured))
        hierarchy_structured_values.append(sorted_join(hierarchy_structured))
        direct_text_values.append(sorted_join(direct_text))
        hierarchy_text_values.append(sorted_join(hierarchy_text))
        direct_comment_values.append(sorted_join(direct_comment))
        hierarchy_comment_values.append(sorted_join(hierarchy_comment))
        direct_title_values.append(sorted_join(direct_title))
        hierarchy_title_values.append(sorted_join(hierarchy_title))
        all_chg_values.append(sorted_join(all_chg))
        matched_signal_counts.append(signal_count)

    enriched["DirectExplicitCHGKeys"] = direct_explicit_values
    enriched["HierarchyExplicitCHGKeys"] = hierarchy_explicit_values
    enriched["DirectStructuredCHGKeys"] = direct_structured_values
    enriched["HierarchyStructuredCHGKeys"] = hierarchy_structured_values
    enriched["DirectTextCHGKeys"] = direct_text_values
    enriched["HierarchyTextCHGKeys"] = hierarchy_text_values
    enriched["DirectCommentCHGKeys"] = direct_comment_values
    enriched["HierarchyCommentCHGKeys"] = hierarchy_comment_values
    enriched["DirectTitleMatchCHGKeys"] = direct_title_values
    enriched["HierarchyTitleMatchCHGKeys"] = hierarchy_title_values
    enriched["MatchedCHGKeys"] = all_chg_values
    enriched["MatchedCommentSignalCount"] = matched_signal_counts
    enriched["HasGMUD"] = enriched["MatchedCHGKeys"].astype(str).str.strip().ne("")
    enriched["PrimaryEvidence"] = enriched.apply(pick_primary_evidence, axis=1)
    enriched["PrimaryEvidenceBucket"] = enriched["PrimaryEvidence"].apply(map_primary_bucket)
    enriched["UsedCommentEvidence"] = (
        enriched["DirectCommentCHGKeys"].astype(str).str.strip().ne("")
        | enriched["HierarchyCommentCHGKeys"].astype(str).str.strip().ne("")
    )
    return enriched


def _safe_pct(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100.0, 1) if denominator else 0.0


def add_summary_row(rows: List[Dict[str, Any]], scope: str, value: str, df: pd.DataFrame) -> None:
    eligible = df[df["EligibleForGMUD"] == True].copy()
    total = int(len(eligible))
    covered = int(eligible["HasGMUD"].sum()) if total else 0
    explicit = int((eligible["PrimaryEvidenceBucket"] == "Explicita").sum()) if total else 0
    comment = int(eligible["UsedCommentEvidence"].sum()) if total else 0
    text_only = int(((eligible["PrimaryEvidenceBucket"] == "Texto") | (eligible["PrimaryEvidenceBucket"] == "Comentario")).sum()) if total else 0
    rows.append(
        {
            "Escopo": scope,
            "Valor": value,
            "ItensElegiveis": total,
            "ItensComGMUD": covered,
            "ItensSemGMUD": max(total - covered, 0),
            "IndiceCoberturaGMUDPct": _safe_pct(covered, total),
            "ItensComEvidenciaExplicita": explicit,
            "ItensComEvidenciaTextoOuComentario": text_only,
            "ItensComEvidenciaComentario": comment,
            "CoberturaExplicitaPct": _safe_pct(explicit, total),
            "CoberturaTextoOuComentarioPct": _safe_pct(text_only, total),
            "CoberturaComentarioPct": _safe_pct(comment, total),
        }
    )


def build_summary_index(items_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    add_summary_row(rows, "Geral", "Total", items_df)
    for project, group in items_df.groupby("Projeto", dropna=False):
        add_summary_row(rows, "Projeto", str(project or "Sem projeto"), group)
    for team, group in items_df.groupby("ServiceTeam", dropna=False):
        add_summary_row(rows, "Time", str(team or "Sem time"), group)
    for bucket, group in items_df.groupby("DeliveryBucket", dropna=False):
        add_summary_row(rows, "CategoriaEntrega", str(bucket or "Sem categoria"), group)
    for level, group in items_df.groupby("HierarchyLevel", dropna=False):
        add_summary_row(rows, "Nivel", str(level or "Sem nivel"), group)
    return pd.DataFrame(rows).sort_values(["Escopo", "Valor"], ignore_index=True)


def build_weekly_history(items_df: pd.DataFrame) -> pd.DataFrame:
    base = items_df[(items_df["EligibleForGMUD"] == True) & items_df["ReferenceDate"].notna()].copy()
    if base.empty:
        return pd.DataFrame(
            columns=[
                "Semana",
                "Escopo",
                "Valor",
                "ItensElegiveis",
                "ItensComGMUD",
                "ItensSemGMUD",
                "IndiceCoberturaGMUDPct",
                "ItensComEvidenciaExplicita",
                "ItensComEvidenciaComentario",
                "ItensMelhoria",
                "MelhoriaComGMUD",
                "PctMelhoria",
                "ItensManutencao",
                "ManutencaoComGMUD",
                "PctManutencao",
                "ItensBug",
                "BugComGMUD",
                "PctBug",
            ]
        )

    base["Semana"] = pd.to_datetime(base["ReferenceDate"], errors="coerce").dt.to_period("W-SUN").dt.start_time
    rows: List[Dict[str, Any]] = []
    grouped_frames = [("Geral", "Total", base)]
    for team, group in base.groupby("ServiceTeam", dropna=False):
        grouped_frames.append(("Time", str(team or "Sem time"), group.copy()))

    for scope, value, scope_df in grouped_frames:
        for week, group in scope_df.groupby("Semana", dropna=False):
            total = int(len(group))
            covered = int(group["HasGMUD"].sum())
            explicit = int((group["PrimaryEvidenceBucket"] == "Explicita").sum())
            comment = int(group["UsedCommentEvidence"].sum())
            row: Dict[str, Any] = {
                "Semana": week,
                "Escopo": scope,
                "Valor": value,
                "ItensElegiveis": total,
                "ItensComGMUD": covered,
                "ItensSemGMUD": max(total - covered, 0),
                "IndiceCoberturaGMUDPct": _safe_pct(covered, total),
                "ItensComEvidenciaExplicita": explicit,
                "ItensComEvidenciaComentario": comment,
            }
            for bucket in ["Melhoria", "Manutencao", "Bug"]:
                bucket_df = group[group["DeliveryBucket"] == bucket]
                bucket_total = int(len(bucket_df))
                bucket_covered = int(bucket_df["HasGMUD"].sum()) if bucket_total else 0
                row[f"Itens{bucket}"] = bucket_total
                row[f"{bucket}ComGMUD"] = bucket_covered
                row[f"Pct{bucket}"] = _safe_pct(bucket_covered, bucket_total)
            rows.append(row)
    weekly = pd.DataFrame(rows).sort_values("Semana", ignore_index=True)
    if "Semana" in weekly.columns:
        weekly["Semana"] = pd.to_datetime(weekly["Semana"], errors="coerce").dt.strftime("%Y-%m-%d")
    return weekly


def ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def infer_projects_from_jql(jql: str) -> List[str]:
    text = str(jql or "").strip()
    if not text:
        return []
    found: List[str] = []
    for match in re.finditer(r"\bproject\s*=\s*([A-Za-z][A-Za-z0-9_-]*)", text, flags=re.IGNORECASE):
        key = str(match.group(1) or "").strip().upper()
        if key and key not in found:
            found.append(key)
    for match in re.finditer(r"\bproject\s+in\s*\(([^)]*)\)", text, flags=re.IGNORECASE):
        raw_values = str(match.group(1) or "")
        for token in raw_values.split(","):
            key = str(token or "").strip().strip("'\"").upper()
            if key and key not in found:
                found.append(key)
    return found


def validate_chg_query_access(client: JiraClient, jql: str, chg_df: pd.DataFrame) -> None:
    if not chg_df.empty:
        return

    try:
        myself = client.get_myself()
    except Exception as exc:
        raise RuntimeError(
            "Falha ao autenticar no Jira antes de consultar as GMUDs. "
            "Revise JIRA_EMAIL/JIRA_API_TOKEN e confirme que a conta usada pelo pipeline consegue acessar a API."
        ) from exc

    project_keys = infer_projects_from_jql(jql)
    invisible_projects: List[str] = []
    for project_key in project_keys:
        try:
            visible_projects = client.search_projects(project_key)
        except Exception:
            visible_projects = []
        visible = any(str(project.get("key") or "").strip().upper() == project_key for project in visible_projects)
        if not visible:
            invisible_projects.append(project_key)

    if invisible_projects:
        display_name = str(myself.get("displayName") or "").strip()
        email = str(myself.get("emailAddress") or "").strip()
        actor = display_name or email or "conta autenticada"
        raise RuntimeError(
            "Nenhum ticket retornado pela JQL de GMUD e a conta autenticada "
            f"({actor}) nao enxerga o(s) projeto(s): {', '.join(invisible_projects)}. "
            "Conceda acesso ao projeto CHG ou use uma credencial com permissao de Browse Projects."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Calcula cobertura GMUD a partir de itens Jira e tickets CHG.")
    parser.add_argument(
        "--downstream-csv",
        nargs="+",
        required=True,
        help="Lista de CSVs downstream operacionais (um ou mais).",
    )
    parser.add_argument(
        "--portfolio-csv",
        required=True,
        help="CSV de portfolio BT/NS usado para incluir epicos/features na cobertura.",
    )
    parser.add_argument("--summary-out", required=True, help="CSV de saida com o indice consolidado.")
    parser.add_argument("--weekly-out", required=True, help="CSV de saida com a serie historica semanal.")
    parser.add_argument("--items-out", required=True, help="CSV de saida detalhado por item.")
    parser.add_argument(
        "--chg-jql",
        default="project = CHG ORDER BY status ASC, created DESC",
        help="JQL usada para buscar as GMUDs do projeto CHG.",
    )
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).with_name("jira_env.txt")),
        help="Arquivo com variaveis JIRA_* (default: jira_env.txt ao lado do script).",
    )
    parser.add_argument(
        "--skip-comments",
        action="store_true",
        help="Desabilita a busca completa de comentarios das GMUDs.",
    )
    args = parser.parse_args()

    load_env_file(args.env_file, overwrite=True)
    base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("JIRA_EMAIL", "").strip()
    token = os.getenv("JIRA_API_TOKEN", "").strip()
    if not base_url or not email or not token:
        print("Erro: defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN.", file=sys.stderr)
        return 2

    items_df = build_delivery_base(args.downstream_csv, args.portfolio_csv)
    if items_df.empty:
        print("Erro: base de itens elegiveis vazia; revise os CSVs informados.", file=sys.stderr)
        return 2

    client = JiraClient(base_url=base_url, email=email, api_token=token)
    try:
        chg_df = fetch_chg_issues(
            client=client,
            base_url=base_url,
            jql=str(args.chg_jql or "").strip(),
            fetch_comments=not args.skip_comments,
        )
        validate_chg_query_access(client, str(args.chg_jql or "").strip(), chg_df)
    except RuntimeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    covered_items_df = compute_gmud_coverage(items_df, chg_df)
    summary_df = build_summary_index(covered_items_df)
    weekly_df = build_weekly_history(covered_items_df)

    for out_path in [args.summary_out, args.weekly_out, args.items_out]:
        ensure_parent_dir(out_path)

    summary_df.to_csv(args.summary_out, index=False, encoding="utf-8-sig")
    weekly_df.to_csv(args.weekly_out, index=False, encoding="utf-8-sig")

    items_export = covered_items_df.copy()
    if "ReferenceDate" in items_export.columns:
        items_export["ReferenceDate"] = pd.to_datetime(items_export["ReferenceDate"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "DoneDate" in items_export.columns:
        items_export["DoneDate"] = pd.to_datetime(items_export["DoneDate"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "ReadyForProductionDate" in items_export.columns:
        items_export["ReadyForProductionDate"] = pd.to_datetime(items_export["ReadyForProductionDate"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "StatusChangedAt" in items_export.columns:
        items_export["StatusChangedAt"] = pd.to_datetime(items_export["StatusChangedAt"], errors="coerce").dt.strftime("%Y-%m-%d")
    items_export["ReferenceKeys"] = items_export["ReferenceKeys"].apply(sorted_join)
    items_export.to_csv(args.items_out, index=False, encoding="utf-8-sig")

    eligible_total = int((covered_items_df["EligibleForGMUD"] == True).sum())
    covered_total = int(((covered_items_df["EligibleForGMUD"] == True) & (covered_items_df["HasGMUD"] == True)).sum())
    print(
        "Indice GMUD calculado: "
        f"{covered_total}/{eligible_total} itens com evidencias de GMUD "
        f"({_safe_pct(covered_total, eligible_total):.1f}%)."
    )
    print(f"Resumo salvo em: {args.summary_out}")
    print(f"Historico semanal salvo em: {args.weekly_out}")
    print(f"Base detalhada salva em: {args.items_out}")
    if not chg_df.empty:
        print(f"Tickets CHG analisados: {len(chg_df)}")
    else:
        print("Aviso: nenhum ticket CHG retornado pela JQL informada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
