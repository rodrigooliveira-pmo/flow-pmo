"""Testes de regressão para dashboards/domain/schema.py (RF-028–RF-030, RF-033)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from dashboards.domain.schema import (
    WorkItem,
    DimProject,
    DimType,
    DimPerson,
    DeliveredItemsRow,
    TimeMetricsRow,
    ThroughputRow,
    FATO_ITEMS_REQUIRED_COLUMNS,
    FATO_ITEMS_EXPECTED_COLUMNS,
    DIM_PROJETO_REQUIRED_COLUMNS,
    DIM_TIPO_REQUIRED_COLUMNS,
)


# ---------------------------------------------------------------------------
# Dataclass instantiation — RF-028/RF-029/RF-030
# ---------------------------------------------------------------------------

class TestDimProject:
    def test_create_minimal(self):
        p = DimProject(ProjetoID=1, NomeProjeto="W1NNER")
        assert p.ProjetoID == 1
        assert p.NomeProjeto == "W1NNER"

    def test_fields_types(self):
        p = DimProject(ProjetoID=42, NomeProjeto="S1NC")
        assert isinstance(p.ProjetoID, int)
        assert isinstance(p.NomeProjeto, str)


class TestDimType:
    def test_create(self):
        t = DimType(TipoID=3, Tipo="Epic")
        assert t.TipoID == 3
        assert t.Tipo == "Epic"


class TestDimPerson:
    def test_create(self):
        p = DimPerson(ResponsavelID=7, Responsavel="Alice")
        assert p.Responsavel == "Alice"


class TestWorkItem:
    def test_create_minimal(self):
        w = WorkItem(ProjetoID=1, TipoID=2, Projeto="W1NNER", Tipo="Epic")
        assert w.Projeto == "W1NNER"
        assert w.LeadTime_Dias is None
        assert w.ElegivelTempoConcluido is False

    def test_create_full(self):
        now = datetime.now()
        w = WorkItem(
            ProjetoID=1,
            TipoID=2,
            Projeto="W1NNER",
            Tipo="Epic",
            Responsavel="Alice",
            Prioridade="Standard",
            ClasseServico="Standard",
            DataBacklog=now,
            DataInProgress=now,
            DataDone=now,
            LeadTime_Dias=5.0,
            LeadTime_Selected_Dias=5.0,
            ElegivelTempoConcluido=True,
            StatusHistoricoContemCancelamento=False,
            ItemID="PROJ-001",
            StoryPoints=3.0,
        )
        assert w.LeadTime_Dias == 5.0
        assert w.ElegivelTempoConcluido is True
        assert isinstance(w.DataDone, datetime)

    def test_optional_fields_default_none(self):
        w = WorkItem(ProjetoID=1, TipoID=1, Projeto="X", Tipo="Task")
        assert w.Responsavel is None
        assert w.DataDone is None
        assert w.ItemID is None
        assert w.StoryPoints is None


# ---------------------------------------------------------------------------
# Required column constants — RF-029
# ---------------------------------------------------------------------------

class TestRequiredColumnConstants:
    def test_fato_required_columns_not_empty(self):
        assert len(FATO_ITEMS_REQUIRED_COLUMNS) > 0

    def test_fato_required_subset_of_expected(self):
        for col in FATO_ITEMS_REQUIRED_COLUMNS:
            assert col in FATO_ITEMS_EXPECTED_COLUMNS

    def test_dim_projeto_has_id_and_name(self):
        assert "ProjetoID" in DIM_PROJETO_REQUIRED_COLUMNS
        assert "NomeProjeto" in DIM_PROJETO_REQUIRED_COLUMNS

    def test_dim_tipo_has_id_and_type(self):
        assert "TipoID" in DIM_TIPO_REQUIRED_COLUMNS
        assert "Tipo" in DIM_TIPO_REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# TypedDicts are usable as dict annotations — RF-033
# ---------------------------------------------------------------------------

class TestTypedDicts:
    def test_delivered_items_row_keys(self):
        row: DeliveredItemsRow = {
            "ItemID": "PROJ-001",
            "Projeto": "W1NNER",
            "LeadTime_Dias": 5.0,
            "ElegivelTempoConcluido": True,
        }
        assert row["ItemID"] == "PROJ-001"

    def test_time_metrics_row_keys(self):
        row: TimeMetricsRow = {
            "LeadTime_Selected_Dias": 3.0,
            "ElegivelTempoConcluido": True,
        }
        assert row["LeadTime_Selected_Dias"] == 3.0

    def test_throughput_row_keys(self):
        row: ThroughputRow = {"Tipo": "Dev"}
        assert row["Tipo"] == "Dev"
