"""Contratos de dados do Flow-PMO — dataclasses e TypedDicts canônicos.

RF-028: dataclasses para WorkItem, DimProject, DimType, DimPerson.
RF-029: campos refletem o schema real do Excel model (Fato_Items + Dims).
RF-030: tipos Python precisos; Optional[X] onde o campo é nullable.
RF-033: TypedDicts documentam colunas esperadas nos DataFrames de métricas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TypedDict


# ---------------------------------------------------------------------------
# Dimension dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DimProject:
    ProjetoID: int
    NomeProjeto: str


@dataclass
class DimType:
    TipoID: int
    Tipo: str


@dataclass
class DimPerson:
    ResponsavelID: int
    Responsavel: str


# ---------------------------------------------------------------------------
# Fact dataclass
# ---------------------------------------------------------------------------

@dataclass
class WorkItem:
    """Representa uma linha de Fato_Items após merges e normalização."""
    ProjetoID: int
    TipoID: int
    Projeto: str
    Tipo: str
    # Optional dimension fields (merge may miss rows)
    Responsavel: Optional[str] = None
    Prioridade: Optional[str] = None
    ClasseServico: Optional[str] = None
    # Dates — all nullable (may not yet have occurred)
    DataBacklog: Optional[datetime] = None
    DataInProgress: Optional[datetime] = None
    DataDone: Optional[datetime] = None
    DataCriacao: Optional[datetime] = None
    # Time metrics — computed, nullable for in-progress items
    LeadTime_Dias: Optional[float] = None
    LeadTime_Selected_Dias: Optional[float] = None
    TempoExecucao_Dias: Optional[float] = None
    TempoBacklog_Dias: Optional[float] = None
    # Eligibility flags — pre-computed upstream
    ElegivelTempoConcluido: bool = False
    StatusHistoricoContemCancelamento: bool = False
    # Optional identifiers
    ItemID: Optional[str] = None
    StoryPoints: Optional[float] = None


# ---------------------------------------------------------------------------
# TypedDicts — DataFrame column contracts (RF-033)
# ---------------------------------------------------------------------------

class DeliveredItemsRow(TypedDict, total=False):
    """Columns expected by build_delivered_items_base and build_lead_time_comparable_scope."""
    ItemID: str
    Projeto: str
    DataDone: datetime
    DataCriacao: datetime
    LeadTime_Dias: float
    LeadTime_Selected_Dias: float
    ElegivelTempoConcluido: bool
    StatusHistoricoContemCancelamento: bool
    Tipo: str
    ClasseServico: str


class TimeMetricsRow(TypedDict, total=False):
    """Columns expected by time_metric_series and related functions."""
    LeadTime_Dias: float
    LeadTime_Selected_Dias: float
    TempoExecucao_Dias: float
    TempoBacklog_Dias: float
    TempoBloqueioDias: float
    TempoEsperaIntermediariaDias: float
    ElegivelTempoConcluido: bool
    StatusHistoricoContemCancelamento: bool


class ThroughputRow(TypedDict, total=False):
    """Columns expected by build_monthly_throughput_percentage_by_type."""
    DataDone: datetime
    Tipo: str
    ClasseServico: str


# ---------------------------------------------------------------------------
# Required column contracts (used by schema validation in load_model_data)
# ---------------------------------------------------------------------------

FATO_ITEMS_REQUIRED_COLUMNS: tuple[str, ...] = (
    "ProjetoID",
    "TipoID",
)

FATO_ITEMS_EXPECTED_COLUMNS: tuple[str, ...] = (
    "ProjetoID",
    "TipoID",
    "DataBacklog",
    "DataInProgress",
    "DataDone",
    "LeadTime_Dias",
    "ElegivelTempoConcluido",
)

DIM_PROJETO_REQUIRED_COLUMNS: tuple[str, ...] = ("ProjetoID", "NomeProjeto")

DIM_TIPO_REQUIRED_COLUMNS: tuple[str, ...] = ("TipoID", "Tipo")
