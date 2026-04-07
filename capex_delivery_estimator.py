#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

try:
    import pandas as pd
except Exception:
    pd = None  # type: ignore


WINDOWS_DEFAULT_DATA_DIR = Path(r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados")
DEFAULT_OUTPUT_DIR = Path("artifacts") / "capex"
DEFAULT_BT_FILE = "portfolio-bt-ns-latest-data.csv"
DEFAULT_DOWNSTREAM_FILES = {
    "BF": "befinance-downstream-latest-data.csv",
    "DT": "dataanalytics-downstream-latest-data.csv",
    "S1NC": "s1nc-downstream-latest-data.csv",
    "W1NNR": "w1nner-downstream-latest-data.csv",
}
DONE_COLUMN_CANDIDATES = ("itens concluidos", "itens concluídos", "done")
BU_PROJECT_MAP = {
    "befinance": "BF",
    "dados": "DT",
    "sistemas s1nc": "S1NC",
    "sistemas w1nner": "W1NNR",
    "sistemas w1nnner": "W1NNR",
}
PROJECT_PRODUCT_MAP = {
    "BF": "BeFinance",
    "DT": "Data&Analytics",
    "S1NC": "Sync",
    "W1NNR": "W1nner",
}
PEOPLE_COLUMN_ALIASES = {
    "name": {"nome"},
    "work_office": {"office de trabalho"},
    "admission": {"admissao", "admissão"},
    "offboarding": {"offboarding"},
    "department": {"departamento"},
    "role": {"cargo"},
    "employment_type": {"interno"},
    "bu": {"bu"},
    "allocation_type": {"tipo desenvolvimento ou sustentacao", "tipo desenvolvimento ou sustentação"},
    "evolution_hours": {"horas trabalhadas evolucao", "horas trabalhadas evolução"},
    "sustaining_hours": {
        "horas trabalhadas sustentacao e outras",
        "horas trabalhadas sustentação e outras",
    },
    "monthly_total_hours": {"total horas mensal"},
}
PEOPLE_REQUIRED_COLUMNS = {"name", "bu", "evolution_hours"}
TSHIRT_FACTORS = {
    "xs": 0.8,
    "s": 1.0,
    "m": 1.2,
    "l": 1.4,
    "xl": 1.6,
    "xxl": 1.8,
}
RAW_COLUMNS = [
    "MesCompetencia",
    "ProjetoOperacional",
    "IssueKey",
    "IssueTitle",
    "TipoEntrega",
    "ConcluidoEm",
    "Responsavel",
    "StoryPoints",
    "EffortTShirtSize",
    "PesoBase",
    "FatorComplexidade",
    "FatorVinculo",
    "PesoEntrega",
    "ShareProjeto",
    "HorasProjetoEstimadas",
    "AtivoID",
    "Descricao do Ativo",
    "Tipo do Ativo",
    "OrigemVinculo",
    "RegraVinculo",
    "AssetLookupKey",
    "ParentID",
    "FeatureLinkID",
    "EpicLinkID",
    "ParentTitle",
    "EpicLinkName",
]
ASSET_COLUMNS = [
    "MesCompetencia",
    "ProjetoOperacional",
    "AtivoID",
    "Descricao do Ativo",
    "Tipo do Ativo",
    "OrigemVinculo",
    "RegraVinculo",
    "QtdEntregas",
    "QtdEntregasBT",
    "PesoTotalAtivo",
    "ShareProjeto",
    "HorasEvolucaoProjeto",
    "HorasCapexEstimadas",
    "ColaboradoresAlocados",
]
PERSON_COLUMNS = [
    "MesCompetencia",
    "ProjetoOperacional",
    "Nome",
    "BU",
    "Cargo",
    "TipoVinculo",
    "HorasEvolucaoBolsa",
    "ShareProjeto",
    "HorasCapexAlocadas",
    "AtivoID",
    "Descricao do Ativo",
    "Tipo do Ativo",
    "OrigemVinculo",
    "RegraVinculo",
]
PROJECT_COLUMNS = [
    "MesCompetencia",
    "ProjetoOperacional",
    "HorasEvolucaoEntrada",
    "HorasEvolucaoDistribuidas",
    "QtdColaboradores",
    "QtdEntregas",
    "QtdAtivos",
    "QtdEntregasBT",
    "QtdEntregasProjetoLocal",
    "QtdEntregasNaoVinculado",
    "QtdEntregasSemEntregaMes",
]
FINAL_LAYOUT_COLUMNS = [
    "ID do Projeto",
    "Descrição do Ativo",
    "Colaborador",
    "Data do Apontamento das Horas",
    "Horas",
    "Atividade Desenvolvida",
]
FINAL_LAYOUT_V2_COLUMNS = [
    "ID do Projeto",
    "Descrição do Ativo",
    "Colaborador",
    "Data do Apontamento das Horas",
    "Horas",
    "Atividade Desenvolvida",
    "Produto",
]


def normalize_text(value: Any) -> str:
    raw = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_accents.replace("_", " ").replace("-", " ").split())


def parse_decimal(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    text = text.replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def parse_br_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_month(month_value: str) -> tuple[date, date]:
    start = datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, next_month - timedelta(days=1)


def format_br_date(value: Any) -> str:
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    parsed = parse_br_date(value)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return text


def choose_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        return str(dialect.delimiter)
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def default_data_dir() -> Path:
    if WINDOWS_DEFAULT_DATA_DIR.exists():
        return WINDOWS_DEFAULT_DATA_DIR
    return Path.cwd()


def find_existing_path(primary: Path, fallbacks: Iterable[Path]) -> Path:
    if primary.exists():
        return primary
    for fallback in fallbacks:
        if fallback.exists():
            return fallback
    return primary


def load_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = choose_delimiter(sample)
        return list(csv.DictReader(handle, delimiter=delimiter))


def load_table_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        if pd is None:
            raise RuntimeError("Leitura de XLSX requer pandas/openpyxl neste ambiente.")
        dataframe = pd.read_excel(path)
        dataframe = dataframe.fillna("")
        return [
            {str(column): row[column] for column in dataframe.columns}
            for _, row in dataframe.iterrows()
        ]
    return load_csv_rows(path)


def resolve_people_headers(raw_rows: list[dict[str, Any]]) -> dict[str, str]:
    if not raw_rows:
        return {}
    normalized_headers = {normalize_text(header): header for header in raw_rows[0].keys()}
    resolved: dict[str, str] = {}
    for canonical, aliases in PEOPLE_COLUMN_ALIASES.items():
        for alias in aliases:
            original = normalized_headers.get(normalize_text(alias))
            if original:
                resolved[canonical] = original
                break
    missing = sorted(PEOPLE_REQUIRED_COLUMNS - set(resolved))
    if missing:
        raise RuntimeError(
            "Tabela de pessoas sem colunas obrigatorias: " + ", ".join(missing)
        )
    return resolved


def map_bu_to_project(bu_value: str) -> str:
    normalized = normalize_text(bu_value)
    if normalized in BU_PROJECT_MAP:
        return BU_PROJECT_MAP[normalized]
    if normalized.startswith("sistemas ") and "w1nner" in normalized:
        return "W1NNR"
    return ""


def load_people_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_rows = load_table_rows(path)
    header_map = resolve_people_headers(raw_rows)
    people_rows: list[dict[str, Any]] = []
    unmapped_bus = Counter()

    for raw_row in raw_rows:
        row = {canonical: str(raw_row.get(source, "")).strip() for canonical, source in header_map.items()}
        project_code = map_bu_to_project(row.get("bu", ""))
        if not project_code:
            unmapped_bus[row.get("bu", "")] += 1
        people_rows.append(
            {
                "name": row.get("name", ""),
                "work_office": row.get("work_office", ""),
                "admission": row.get("admission", ""),
                "offboarding": row.get("offboarding", ""),
                "department": row.get("department", ""),
                "role": row.get("role", ""),
                "employment_type": row.get("employment_type", ""),
                "bu": row.get("bu", ""),
                "allocation_type": row.get("allocation_type", ""),
                "project_code": project_code,
                "evolution_hours": round(parse_decimal(row.get("evolution_hours")), 2),
                "sustaining_hours": round(parse_decimal(row.get("sustaining_hours")), 2),
                "monthly_total_hours": round(parse_decimal(row.get("monthly_total_hours")), 2),
            }
        )

    diagnostics = {
        "input_rows": len(raw_rows),
        "mapped_rows": sum(1 for row in people_rows if row["project_code"]),
        "unmapped_bus": dict(unmapped_bus),
    }
    return people_rows, diagnostics


def build_bt_lookup(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = load_csv_rows(path)
    by_id = {str(row.get("ID") or "").strip(): row for row in rows if str(row.get("ID") or "").strip()}
    by_title: dict[str, dict[str, Any]] = {}
    for row in rows:
        title_key = normalize_text(row.get("Titulo"))
        if title_key and title_key not in by_title:
            by_title[title_key] = row
    return by_id, by_title


def detect_done_column(rows: list[dict[str, Any]]) -> str:
    if not rows:
        raise RuntimeError("Arquivo downstream sem linhas para detectar a coluna de conclusao.")
    for column in rows[0].keys():
        if normalize_text(column) in DONE_COLUMN_CANDIDATES:
            return column
    raise RuntimeError("Nao encontrei coluna de conclusao (Done/Itens concluidos) no downstream.")


def resolve_local_asset(row: dict[str, Any], project_code: str) -> dict[str, str]:
    candidates = [
        {
            "lookup_field": "FeatureLinkID",
            "id": first_non_empty(row.get("FeatureLinkID")),
            "type": first_non_empty(row.get("FeatureLinkTipo"), "Feature"),
            "title": first_non_empty(row.get("ParentTitle"), row.get("EpicLinkName")),
        },
        {
            "lookup_field": "EpicLinkID",
            "id": first_non_empty(row.get("EpicLinkID")),
            "type": first_non_empty(row.get("EpicLinkTipo"), "Epico"),
            "title": first_non_empty(row.get("EpicLinkName"), row.get("ParentTitle")),
        },
        {
            "lookup_field": "ParentID",
            "id": first_non_empty(row.get("ParentID")),
            "type": first_non_empty(row.get("ParentTipo"), "Parent"),
            "title": first_non_empty(row.get("ParentTitle"), row.get("EpicLinkName")),
        },
    ]
    for candidate in candidates:
        if candidate["id"] or candidate["title"]:
            local_id = candidate["id"] or f"{project_code}-TITLE-{normalize_text(candidate['title'])[:60]}"
            return {
                "AtivoID": local_id,
                "Descricao do Ativo": candidate["title"] or local_id,
                "Tipo do Ativo": candidate["type"] or "ProjetoLocal",
                "OrigemVinculo": "ProjetoLocal",
                "RegraVinculo": candidate["lookup_field"],
                "AssetLookupKey": candidate["id"] or normalize_text(candidate["title"]),
            }
    return {
        "AtivoID": f"{project_code}-NAO-VINCULADO",
        "Descricao do Ativo": f"{project_code} | Nao vinculado",
        "Tipo do Ativo": "Nao Vinculado",
        "OrigemVinculo": "NaoVinculado",
        "RegraVinculo": "fallback_sem_link",
        "AssetLookupKey": "",
    }


def resolve_asset(
    row: dict[str, Any],
    project_code: str,
    bt_by_id: dict[str, dict[str, Any]],
    bt_by_title: dict[str, dict[str, Any]],
) -> dict[str, str]:
    id_candidates = [
        ("FeatureLinkID", first_non_empty(row.get("FeatureLinkID"))),
        ("EpicLinkID", first_non_empty(row.get("EpicLinkID"))),
        ("ParentID", first_non_empty(row.get("ParentID"))),
    ]
    for source_field, candidate_id in id_candidates:
        bt_row = bt_by_id.get(candidate_id)
        if bt_row:
            return {
                "AtivoID": str(bt_row.get("ID") or "").strip(),
                "Descricao do Ativo": str(bt_row.get("Titulo") or "").strip(),
                "Tipo do Ativo": str(bt_row.get("Tipo") or "").strip(),
                "OrigemVinculo": "BT",
                "RegraVinculo": source_field,
                "AssetLookupKey": candidate_id,
            }

    title_candidates = [
        ("EpicLinkName", first_non_empty(row.get("EpicLinkName"))),
        ("ParentTitle", first_non_empty(row.get("ParentTitle"))),
    ]
    for source_field, candidate_title in title_candidates:
        bt_row = bt_by_title.get(normalize_text(candidate_title))
        if bt_row:
            return {
                "AtivoID": str(bt_row.get("ID") or "").strip(),
                "Descricao do Ativo": str(bt_row.get("Titulo") or "").strip(),
                "Tipo do Ativo": str(bt_row.get("Tipo") or "").strip(),
                "OrigemVinculo": "BT",
                "RegraVinculo": f"{source_field}_title_match",
                "AssetLookupKey": normalize_text(candidate_title),
            }

    return resolve_local_asset(row, project_code)


def base_weight_for_issue_type(issue_type: str) -> float:
    normalized = normalize_text(issue_type)
    if normalized in {"feature", "historia", "story", "user story"}:
        return 1.0
    if normalized in {"tarefa", "task", "tech", "tech task"}:
        return 0.7
    if "bug" in normalized or normalized in {"problema", "problem", "incident"}:
        return 0.5
    if normalized in {"support", "ad hoc", "adhoc", "subtarefa", "subtask"}:
        return 0.3
    return 0.4


def complexity_factor(row: dict[str, Any]) -> tuple[float, float]:
    story_points = parse_decimal(first_non_empty(row.get("Story Points"), row.get("Story point estimate")))
    if story_points > 0:
        if story_points <= 2:
            return 0.8, story_points
        if story_points <= 5:
            return 1.0, story_points
        if story_points <= 8:
            return 1.2, story_points
        if story_points <= 13:
            return 1.5, story_points
        return 1.8, story_points

    tshirt = normalize_text(row.get("EffortTShirtSize"))
    if tshirt in TSHIRT_FACTORS:
        return TSHIRT_FACTORS[tshirt], 0.0
    return 1.0, 0.0


def link_factor(origin: str) -> float:
    if origin == "BT":
        return 1.0
    if origin == "ProjetoLocal":
        return 0.95
    if origin == "SemEntregaMes":
        return 1.0
    return 0.75


def allocate_total(total: float, weighted_items: list[tuple[str, float]]) -> dict[str, float]:
    total = round(float(total), 2)
    if total <= 0:
        return {key: 0.0 for key, _ in weighted_items}

    positive_items = [(key, float(weight)) for key, weight in weighted_items if float(weight) > 0]
    if not positive_items:
        return {key: 0.0 for key, _ in weighted_items}

    weight_sum = sum(weight for _, weight in positive_items)
    raw_cents = [(key, (total * 100.0) * weight / weight_sum) for key, weight in positive_items]
    floor_cents = {key: int(math.floor(raw_value)) for key, raw_value in raw_cents}
    remaining = int(round(total * 100.0)) - sum(floor_cents.values())

    remainders = sorted(
        ((key, raw_value - floor_cents[key]) for key, raw_value in raw_cents),
        key=lambda item: (-item[1], item[0]),
    )
    for index in range(remaining):
        floor_cents[remainders[index][0]] += 1

    allocation = {key: 0.0 for key, _ in weighted_items}
    for key, cents in floor_cents.items():
        allocation[key] = cents / 100.0
    return allocation


def load_completed_deliveries(
    project_code: str,
    path: Path,
    start_date: date,
    end_date: date,
    bt_by_id: dict[str, dict[str, Any]],
    bt_by_title: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = load_csv_rows(path)
    done_column = detect_done_column(rows)
    deliveries: list[dict[str, Any]] = []

    for row in rows:
        completed_on = parse_br_date(row.get(done_column))
        if not completed_on or completed_on < start_date or completed_on > end_date:
            continue

        asset = resolve_asset(row, project_code, bt_by_id, bt_by_title)
        base_weight = base_weight_for_issue_type(first_non_empty(row.get("Tipo de Problema")))
        factor_complexity, story_points = complexity_factor(row)
        factor_link = link_factor(asset["OrigemVinculo"])
        weight = round(base_weight * factor_complexity * factor_link, 6)

        deliveries.append(
            {
                "MesCompetencia": start_date.strftime("%Y-%m"),
                "ProjetoOperacional": project_code,
                "IssueKey": first_non_empty(row.get("ID")),
                "IssueTitle": first_non_empty(row.get("Title")),
                "TipoEntrega": first_non_empty(row.get("Tipo de Problema")),
                "ConcluidoEm": completed_on.isoformat(),
                "Responsavel": first_non_empty(row.get("Responsável"), row.get("DevExecutor")),
                "StoryPoints": story_points,
                "EffortTShirtSize": first_non_empty(row.get("EffortTShirtSize")),
                "PesoBase": round(base_weight, 4),
                "FatorComplexidade": round(factor_complexity, 4),
                "FatorVinculo": round(factor_link, 4),
                "PesoEntrega": weight,
                "ShareProjeto": 0.0,
                "HorasProjetoEstimadas": 0.0,
                "AtivoID": asset["AtivoID"],
                "Descricao do Ativo": asset["Descricao do Ativo"],
                "Tipo do Ativo": asset["Tipo do Ativo"],
                "OrigemVinculo": asset["OrigemVinculo"],
                "RegraVinculo": asset["RegraVinculo"],
                "AssetLookupKey": asset["AssetLookupKey"],
                "ParentID": first_non_empty(row.get("ParentID")),
                "FeatureLinkID": first_non_empty(row.get("FeatureLinkID")),
                "EpicLinkID": first_non_empty(row.get("EpicLinkID")),
                "ParentTitle": first_non_empty(row.get("ParentTitle")),
                "EpicLinkName": first_non_empty(row.get("EpicLinkName")),
            }
        )

    return deliveries


def synthesize_no_delivery_asset(project_code: str, month_label: str) -> dict[str, Any]:
    return {
        "MesCompetencia": month_label,
        "ProjetoOperacional": project_code,
        "AtivoID": f"{project_code}-SEM-ENTREGA",
        "Descricao do Ativo": f"{project_code} | Sem entrega no mes",
        "Tipo do Ativo": "Sem Entrega",
        "OrigemVinculo": "SemEntregaMes",
        "RegraVinculo": "bucket_sem_entrega",
        "QtdEntregas": 0,
        "QtdEntregasBT": 0,
        "PesoTotalAtivo": 1.0,
        "ShareProjeto": 1.0,
        "HorasEvolucaoProjeto": 0.0,
    }


def summarize_assets(
    deliveries: list[dict[str, Any]],
    project_hours: dict[str, float],
    month_label: str,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    project_asset_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    issue_weights_by_project: dict[str, list[tuple[str, float]]] = defaultdict(list)
    issue_weight_sum: dict[str, float] = defaultdict(float)

    for delivery in deliveries:
        project_code = delivery["ProjetoOperacional"]
        asset_id = delivery["AtivoID"]
        asset_entry = project_asset_map[project_code].setdefault(
            asset_id,
            {
                "MesCompetencia": month_label,
                "ProjetoOperacional": project_code,
                "AtivoID": asset_id,
                "Descricao do Ativo": delivery["Descricao do Ativo"],
                "Tipo do Ativo": delivery["Tipo do Ativo"],
                "OrigemVinculo": delivery["OrigemVinculo"],
                "RegraVinculo": delivery["RegraVinculo"],
                "QtdEntregas": 0,
                "QtdEntregasBT": 0,
                "PesoTotalAtivo": 0.0,
                "ShareProjeto": 0.0,
                "HorasEvolucaoProjeto": round(project_hours.get(project_code, 0.0), 2),
            },
        )
        asset_entry["QtdEntregas"] += 1
        if delivery["OrigemVinculo"] == "BT":
            asset_entry["QtdEntregasBT"] += 1
        asset_entry["PesoTotalAtivo"] += float(delivery["PesoEntrega"])
        issue_weights_by_project[project_code].append((delivery["IssueKey"], float(delivery["PesoEntrega"])))
        issue_weight_sum[project_code] += float(delivery["PesoEntrega"])

    project_asset_shares: dict[str, list[dict[str, Any]]] = {}
    for project_code, hours in project_hours.items():
        asset_entries = list(project_asset_map.get(project_code, {}).values())
        if not asset_entries:
            asset_entries = [synthesize_no_delivery_asset(project_code, month_label)]
        weight_sum = sum(float(asset["PesoTotalAtivo"]) for asset in asset_entries)
        if weight_sum <= 0:
            for asset in asset_entries:
                asset["PesoTotalAtivo"] = 1.0
            weight_sum = float(len(asset_entries))
        for asset in asset_entries:
            asset["ShareProjeto"] = round(float(asset["PesoTotalAtivo"]) / weight_sum, 6)
        project_asset_shares[project_code] = asset_entries

        if issue_weights_by_project.get(project_code):
            issue_hours = allocate_total(hours, issue_weights_by_project[project_code])
            total_issue_weight = issue_weight_sum[project_code]
            for delivery in deliveries:
                if delivery["ProjetoOperacional"] != project_code:
                    continue
                delivery["ShareProjeto"] = round(float(delivery["PesoEntrega"]) / total_issue_weight, 6)
                delivery["HorasProjetoEstimadas"] = round(issue_hours.get(delivery["IssueKey"], 0.0), 2)

    asset_rows: list[dict[str, Any]] = []
    for project_code, assets in project_asset_shares.items():
        for asset in assets:
            asset_rows.append(asset)
    return asset_rows, project_asset_shares, deliveries


def build_project_capacity_rows(
    people_rows: list[dict[str, Any]],
    month_label: str,
    project_asset_shares: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    people_allocations: list[dict[str, Any]] = []
    asset_hours_rollup: dict[tuple[str, str, str], float] = defaultdict(float)
    asset_people: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for person in people_rows:
        project_code = person["project_code"]
        if not project_code or person["evolution_hours"] <= 0:
            continue
        assets = project_asset_shares.get(project_code, [])
        weighted_assets = [(asset["AtivoID"], asset["PesoTotalAtivo"]) for asset in assets]
        allocation_by_asset = allocate_total(person["evolution_hours"], weighted_assets)
        asset_map = {asset["AtivoID"]: asset for asset in assets}

        for asset_id, allocated_hours in allocation_by_asset.items():
            asset = asset_map[asset_id]
            people_allocations.append(
                {
                    "MesCompetencia": month_label,
                    "ProjetoOperacional": project_code,
                    "Nome": person["name"],
                    "BU": person["bu"],
                    "Cargo": person["role"],
                    "TipoVinculo": person["employment_type"],
                    "HorasEvolucaoBolsa": round(float(person["evolution_hours"]), 2),
                    "ShareProjeto": round(float(asset.get("ShareProjeto") or 0.0), 6),
                    "HorasCapexAlocadas": round(float(allocated_hours), 2),
                    "AtivoID": asset["AtivoID"],
                    "Descricao do Ativo": asset["Descricao do Ativo"],
                    "Tipo do Ativo": asset["Tipo do Ativo"],
                    "OrigemVinculo": asset["OrigemVinculo"],
                    "RegraVinculo": asset["RegraVinculo"],
                }
            )
            rollup_key = (month_label, project_code, asset["AtivoID"])
            asset_hours_rollup[rollup_key] += float(allocated_hours)
            if allocated_hours > 0:
                asset_people[rollup_key].add(person["name"])

    asset_allocation_rows = [
        {
            "MesCompetencia": key[0],
            "ProjetoOperacional": key[1],
            "AtivoID": key[2],
            "HorasCapexEstimadas": round(hours, 2),
            "ColaboradoresAlocados": len(asset_people.get(key, set())),
        }
        for key, hours in asset_hours_rollup.items()
    ]
    return people_allocations, asset_allocation_rows


def merge_asset_hours(
    asset_rows: list[dict[str, Any]],
    asset_allocation_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allocation_lookup = {
        (row["MesCompetencia"], row["ProjetoOperacional"], row["AtivoID"]): row
        for row in asset_allocation_rows
    }
    merged_rows: list[dict[str, Any]] = []
    for asset in asset_rows:
        lookup_key = (asset["MesCompetencia"], asset["ProjetoOperacional"], asset["AtivoID"])
        allocation = allocation_lookup.get(lookup_key, {})
        merged = dict(asset)
        merged["HorasCapexEstimadas"] = round(float(allocation.get("HorasCapexEstimadas") or 0.0), 2)
        merged["ColaboradoresAlocados"] = int(allocation.get("ColaboradoresAlocados") or 0)
        merged["PesoTotalAtivo"] = round(float(merged.get("PesoTotalAtivo") or 0.0), 6)
        merged_rows.append(merged)
    return merged_rows


def build_project_summary(
    month_label: str,
    project_hours: dict[str, float],
    people_rows: list[dict[str, Any]],
    deliveries: list[dict[str, Any]],
    asset_rows: list[dict[str, Any]],
    people_allocations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    deliveries_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    assets_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    people_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    allocations_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for delivery in deliveries:
        deliveries_by_project[delivery["ProjetoOperacional"]].append(delivery)
    for asset in asset_rows:
        assets_by_project[asset["ProjetoOperacional"]].append(asset)
    for person in people_rows:
        if person["project_code"]:
            people_by_project[person["project_code"]].append(person)
    for allocation in people_allocations:
        allocations_by_project[allocation["ProjetoOperacional"]].append(allocation)

    summary_rows: list[dict[str, Any]] = []
    for project_code, input_hours in sorted(project_hours.items()):
        project_deliveries = deliveries_by_project.get(project_code, [])
        counts = Counter(delivery["OrigemVinculo"] for delivery in project_deliveries)
        asset_origin_counts = Counter(asset["OrigemVinculo"] for asset in assets_by_project.get(project_code, []))
        summary_rows.append(
            {
                "MesCompetencia": month_label,
                "ProjetoOperacional": project_code,
                "HorasEvolucaoEntrada": round(float(input_hours), 2),
                "HorasEvolucaoDistribuidas": round(
                    sum(float(row["HorasCapexAlocadas"]) for row in allocations_by_project.get(project_code, [])),
                    2,
                ),
                "QtdColaboradores": len(people_by_project.get(project_code, [])),
                "QtdEntregas": len(project_deliveries),
                "QtdAtivos": len(assets_by_project.get(project_code, [])),
                "QtdEntregasBT": counts.get("BT", 0),
                "QtdEntregasProjetoLocal": counts.get("ProjetoLocal", 0),
                "QtdEntregasNaoVinculado": counts.get("NaoVinculado", 0),
                "QtdEntregasSemEntregaMes": asset_origin_counts.get("SemEntregaMes", 0),
            }
        )
    return summary_rows


def build_activity_description(delivery: dict[str, Any]) -> str:
    issue_type = first_non_empty(delivery.get("TipoEntrega"))
    issue_title = first_non_empty(delivery.get("IssueTitle"))
    if issue_type and issue_title:
        return f"{issue_type} | {issue_title}"
    return issue_title or issue_type or "Entrega estimada"


def product_label_for_project(project_code: str) -> str:
    return PROJECT_PRODUCT_MAP.get(str(project_code or "").strip().upper(), str(project_code or "").strip().upper())


def is_improvement_delivery(delivery: dict[str, Any]) -> bool:
    issue_type = normalize_text(delivery.get("TipoEntrega"))
    asset_type = normalize_text(delivery.get("Tipo do Ativo"))
    improvement_issue_types = {"epico", "epic", "feature", "historia", "story", "user story"}
    improvement_asset_types = {"epico", "epic", "feature"}
    return issue_type in improvement_issue_types or asset_type in improvement_asset_types


def resolve_improvement_reference(delivery: dict[str, Any]) -> dict[str, str]:
    asset_type = normalize_text(delivery.get("Tipo do Ativo"))
    issue_type = normalize_text(delivery.get("TipoEntrega"))
    if asset_type in {"epico", "epic", "feature"}:
        return {
            "id": first_non_empty(delivery.get("AtivoID")),
            "description": first_non_empty(delivery.get("Descricao do Ativo")),
            "activity": first_non_empty(delivery.get("Tipo do Ativo"), "Melhoria"),
        }
    if issue_type in {"epico", "epic", "feature", "historia", "story", "user story"}:
        return {
            "id": first_non_empty(delivery.get("IssueKey")),
            "description": first_non_empty(delivery.get("IssueTitle"), delivery.get("Descricao do Ativo")),
            "activity": first_non_empty(delivery.get("TipoEntrega"), "Melhoria"),
        }
    return {
        "id": first_non_empty(delivery.get("AtivoID"), delivery.get("IssueKey")),
        "description": first_non_empty(delivery.get("Descricao do Ativo"), delivery.get("IssueTitle")),
        "activity": "Melhoria",
    }


def build_final_layout_rows(
    people_rows: list[dict[str, Any]],
    deliveries: list[dict[str, Any]],
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    deliveries_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for delivery in deliveries:
        deliveries_by_project[delivery["ProjetoOperacional"]].append(delivery)

    final_rows: list[dict[str, Any]] = []
    fallback_date = format_br_date(end_date)

    for person in people_rows:
        project_code = person["project_code"]
        evolution_hours = round(float(person["evolution_hours"]), 2)
        if not project_code or evolution_hours <= 0:
            continue

        project_deliveries = deliveries_by_project.get(project_code, [])
        if not project_deliveries:
            final_rows.append(
                {
                    "ID do Projeto": f"{project_code}-SEM-ENTREGA",
                    "Descrição do Ativo": f"{project_code} | Sem entrega no mes",
                    "Colaborador": person["name"],
                    "Data do Apontamento das Horas": fallback_date,
                    "Horas": evolution_hours,
                    "Atividade Desenvolvida": "Sem entrega mapeada no periodo",
                }
            )
            continue

        weights = [(delivery["IssueKey"], float(delivery["PesoEntrega"])) for delivery in project_deliveries]
        allocation_by_issue = allocate_total(evolution_hours, weights)
        for delivery in project_deliveries:
            allocated_hours = round(float(allocation_by_issue.get(delivery["IssueKey"], 0.0)), 2)
            if allocated_hours <= 0:
                continue
            final_rows.append(
                {
                    "ID do Projeto": delivery["AtivoID"],
                    "Descrição do Ativo": delivery["Descricao do Ativo"],
                    "Colaborador": person["name"],
                    "Data do Apontamento das Horas": format_br_date(delivery["ConcluidoEm"]),
                    "Horas": allocated_hours,
                    "Atividade Desenvolvida": build_activity_description(delivery),
                }
            )

    return final_rows


def build_final_layout_v2_rows(
    people_rows: list[dict[str, Any]],
    deliveries: list[dict[str, Any]],
    end_date: date,
) -> list[dict[str, Any]]:
    deliveries_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for delivery in deliveries:
        deliveries_by_project[delivery["ProjetoOperacional"]].append(delivery)

    final_rows: list[dict[str, Any]] = []
    competency_date = format_br_date(end_date)

    for person in people_rows:
        project_code = person["project_code"]
        evolution_hours = round(float(person["evolution_hours"]), 2)
        if not project_code or evolution_hours <= 0:
            continue

        project_deliveries = deliveries_by_project.get(project_code, [])
        if not project_deliveries:
            continue

        weights = [(delivery["IssueKey"], float(delivery["PesoEntrega"])) for delivery in project_deliveries]
        allocation_by_issue = allocate_total(evolution_hours, weights)
        grouped_hours: dict[tuple[str, str, str, str], float] = defaultdict(float)
        for delivery in project_deliveries:
            if not is_improvement_delivery(delivery):
                continue
            allocated_hours = float(allocation_by_issue.get(delivery["IssueKey"], 0.0))
            if allocated_hours <= 0:
                continue
            reference = resolve_improvement_reference(delivery)
            group_key = (
                reference["id"],
                reference["description"],
                reference["activity"],
                product_label_for_project(project_code),
            )
            grouped_hours[group_key] += allocated_hours

        for group_key, grouped_hours_value in sorted(grouped_hours.items(), key=lambda item: (-item[1], item[0][0], item[0][1])):
            if round(grouped_hours_value, 2) <= 0:
                continue
            final_rows.append(
                {
                    "ID do Projeto": group_key[0],
                    "Descrição do Ativo": group_key[1],
                    "Colaborador": person["name"],
                    "Data do Apontamento das Horas": competency_date,
                    "Horas": round(grouped_hours_value, 2),
                    "Atividade Desenvolvida": f"{group_key[2]} | Melhorias do mês",
                    "Produto": group_key[3],
                }
            )

    return final_rows


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx_if_possible(
    path: Path,
    raw_rows: list[dict[str, Any]],
    asset_rows: list[dict[str, Any]],
    people_rows: list[dict[str, Any]],
    project_rows: list[dict[str, Any]],
    final_layout_rows: list[dict[str, Any]],
    final_layout_v2_rows: list[dict[str, Any]],
) -> bool:
    if pd is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame(raw_rows, columns=RAW_COLUMNS).to_excel(writer, sheet_name="Entregas", index=False)
            pd.DataFrame(asset_rows, columns=ASSET_COLUMNS).to_excel(writer, sheet_name="ResumoAtivos", index=False)
            pd.DataFrame(people_rows, columns=PERSON_COLUMNS).to_excel(writer, sheet_name="AlocacaoPessoas", index=False)
            pd.DataFrame(project_rows, columns=PROJECT_COLUMNS).to_excel(writer, sheet_name="ResumoProjetos", index=False)
            pd.DataFrame(final_layout_rows, columns=FINAL_LAYOUT_COLUMNS).to_excel(writer, sheet_name="LayoutFinal", index=False)
            pd.DataFrame(final_layout_v2_rows, columns=FINAL_LAYOUT_V2_COLUMNS).to_excel(writer, sheet_name="LayoutFinalV2", index=False)
        return True
    except PermissionError:
        print(
            f"Workbook XLSX nao gerado por permissao negada: {path}. "
            "Feche o arquivo se ele estiver aberto e tente novamente se precisar do XLSX."
        )
        return False


def build_output_prefix(projects: list[str], start_date: date, end_date: date) -> str:
    project_label = "-".join(sorted(project.lower() for project in projects))
    return f"capex-simplificado-{project_label}-{start_date:%Y%m%d}-{end_date:%Y%m%d}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estima CAPEX mensal por ativo usando tabela de pessoas, hierarquia BT e entregas concluidas."
    )
    parser.add_argument("--people-file", required=True, help="CSV ou XLSX com a tabela mensal de pessoas/capacidade.")
    parser.add_argument("--month", help="Mes de competencia no formato YYYY-MM.")
    parser.add_argument("--date-from", help="Data inicial no formato YYYY-MM-DD.")
    parser.add_argument("--date-to", help="Data final no formato YYYY-MM-DD.")
    parser.add_argument("--data-dir", help="Diretorio com os arquivos latest exportados do Jira.")
    parser.add_argument("--out-dir", help="Diretorio de saida para CSV/XLSX.")
    parser.add_argument(
        "--projects",
        nargs="+",
        default=["BF", "DT", "S1NC", "W1NNR"],
        help="Projetos operacionais usados para consolidar entregas.",
    )
    parser.add_argument("--no-xlsx", action="store_true", help="Nao gerar workbook XLSX.")
    args = parser.parse_args()

    if args.month:
        start_date, end_date = parse_month(args.month)
    else:
        if not args.date_from or not args.date_to:
            raise SystemExit("Informe --month ou o par --date-from/--date-to.")
        start_date = datetime.strptime(args.date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.date_to, "%Y-%m-%d").date()
    month_label = start_date.strftime("%Y-%m")

    data_dir = Path(args.data_dir) if args.data_dir else default_data_dir()
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUTPUT_DIR
    people_path = Path(args.people_file)
    if not people_path.exists():
        raise SystemExit(f"Arquivo de pessoas nao encontrado: {people_path}")

    bt_path = find_existing_path(data_dir / DEFAULT_BT_FILE, [Path.cwd() / DEFAULT_BT_FILE])
    if not bt_path.exists():
        raise SystemExit(f"Arquivo BT nao encontrado: {bt_path}")

    project_files: dict[str, Path] = {}
    for project_code in args.projects:
        filename = DEFAULT_DOWNSTREAM_FILES.get(project_code.upper())
        if not filename:
            raise SystemExit(f"Projeto sem arquivo downstream configurado: {project_code}")
        project_path = data_dir / filename
        if not project_path.exists():
            raise SystemExit(f"Arquivo downstream nao encontrado para {project_code}: {project_path}")
        project_files[project_code.upper()] = project_path

    print(f"Janela CAPEX simplificada: {start_date.isoformat()} ate {end_date.isoformat()}")
    print(f"Tabela de pessoas: {people_path}")
    print(f"Diretorio de dados: {data_dir}")

    people_rows, people_diagnostics = load_people_rows(people_path)
    bt_by_id, bt_by_title = build_bt_lookup(bt_path)

    deliveries: list[dict[str, Any]] = []
    for project_code, project_path in project_files.items():
        project_deliveries = load_completed_deliveries(
            project_code=project_code,
            path=project_path,
            start_date=start_date,
            end_date=end_date,
            bt_by_id=bt_by_id,
            bt_by_title=bt_by_title,
        )
        deliveries.extend(project_deliveries)
        bt_count = sum(1 for row in project_deliveries if row["OrigemVinculo"] == "BT")
        local_count = sum(1 for row in project_deliveries if row["OrigemVinculo"] == "ProjetoLocal")
        unlinked_count = sum(1 for row in project_deliveries if row["OrigemVinculo"] == "NaoVinculado")
        print(
            f"Entregas {project_code}: {len(project_deliveries)} | BT={bt_count} | "
            f"ProjetoLocal={local_count} | NaoVinculado={unlinked_count}"
        )

    project_hours: dict[str, float] = defaultdict(float)
    for person in people_rows:
        if person["project_code"]:
            project_hours[person["project_code"]] += float(person["evolution_hours"])

    asset_rows, project_asset_shares, deliveries = summarize_assets(deliveries, project_hours, month_label)
    people_allocations, asset_allocation_rows = build_project_capacity_rows(
        people_rows=people_rows,
        month_label=month_label,
        project_asset_shares=project_asset_shares,
    )
    merged_asset_rows = merge_asset_hours(asset_rows, asset_allocation_rows)
    project_rows = build_project_summary(
        month_label=month_label,
        project_hours=project_hours,
        people_rows=people_rows,
        deliveries=deliveries,
        asset_rows=merged_asset_rows,
        people_allocations=people_allocations,
    )
    final_layout_rows = build_final_layout_rows(
        people_rows=people_rows,
        deliveries=deliveries,
        start_date=start_date,
        end_date=end_date,
    )
    final_layout_v2_rows = build_final_layout_v2_rows(
        people_rows=people_rows,
        deliveries=deliveries,
        end_date=end_date,
    )

    prefix = build_output_prefix(list(project_files.keys()), start_date, end_date)
    raw_out = out_dir / f"{prefix}-entregas.csv"
    asset_out = out_dir / f"{prefix}-ativos.csv"
    people_out = out_dir / f"{prefix}-pessoas.csv"
    project_out = out_dir / f"{prefix}-projetos.csv"
    final_layout_out = out_dir / f"{prefix}-layout-final.csv"
    final_layout_v2_out = out_dir / f"{prefix}-layout-final-v2.csv"
    xlsx_out = out_dir / f"{prefix}.xlsx"

    write_csv(raw_out, deliveries, RAW_COLUMNS)
    write_csv(asset_out, merged_asset_rows, ASSET_COLUMNS)
    write_csv(people_out, people_allocations, PERSON_COLUMNS)
    write_csv(project_out, project_rows, PROJECT_COLUMNS)
    write_csv(final_layout_out, final_layout_rows, FINAL_LAYOUT_COLUMNS)
    write_csv(final_layout_v2_out, final_layout_v2_rows, FINAL_LAYOUT_V2_COLUMNS)

    workbook_written = False
    if not args.no_xlsx:
        workbook_written = write_xlsx_if_possible(
            xlsx_out,
            raw_rows=deliveries,
            asset_rows=merged_asset_rows,
            people_rows=people_allocations,
            project_rows=project_rows,
            final_layout_rows=final_layout_rows,
            final_layout_v2_rows=final_layout_v2_rows,
        )

    total_input_hours = round(sum(float(row["evolution_hours"]) for row in people_rows if row["project_code"]), 2)
    total_distributed_hours = round(sum(float(row["HorasCapexAlocadas"]) for row in people_allocations), 2)
    total_final_layout_hours = round(sum(float(row["Horas"]) for row in final_layout_rows), 2)
    total_final_layout_v2_hours = round(sum(float(row["Horas"]) for row in final_layout_v2_rows), 2)
    origin_counts = Counter(row["OrigemVinculo"] for row in deliveries)

    print(f"Linhas de pessoas: {people_diagnostics['input_rows']} | mapeadas em BU/projeto: {people_diagnostics['mapped_rows']}")
    if people_diagnostics["unmapped_bus"]:
        print(f"BUs nao mapeadas: {people_diagnostics['unmapped_bus']}")
    print(
        f"Resumo CAPEX simplificado: {len(deliveries)} entrega(s), {len(merged_asset_rows)} ativo(s), "
        f"{len(people_allocations)} alocacao(oes) de pessoa."
    )
    print(f"Horas de evolucao: entrada={total_input_hours:.2f} | distribuidas={total_distributed_hours:.2f}")
    print(f"Layout final executivo: {len(final_layout_rows)} linha(s) | horas={total_final_layout_hours:.2f}")
    print(f"Layout final V2 melhorias: {len(final_layout_v2_rows)} linha(s) | horas={total_final_layout_v2_hours:.2f}")
    print(
        f"Cobertura de vinculo: BT={origin_counts.get('BT', 0)} | "
        f"ProjetoLocal={origin_counts.get('ProjetoLocal', 0)} | "
        f"NaoVinculado={origin_counts.get('NaoVinculado', 0)}"
    )
    print(f"CSV entregas: {raw_out}")
    print(f"CSV ativos: {asset_out}")
    print(f"CSV pessoas: {people_out}")
    print(f"CSV projetos: {project_out}")
    print(f"CSV layout final: {final_layout_out}")
    print(f"CSV layout final V2: {final_layout_v2_out}")
    if workbook_written:
        print(f"Workbook XLSX: {xlsx_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
