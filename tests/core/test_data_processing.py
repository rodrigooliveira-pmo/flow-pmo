"""Testes de regressão para dashboards/core/data_processing.py.

Foco nas funções de normalização que são núcleo crítico do sistema.
Sem dependências externas — tudo testado com dados sintéticos.
"""
import pandas as pd
import pytest

from dashboards.core.data_processing import (
    resolve_service_class,
    canonicalize_highest_label,
    is_highest_alias,
    HIGHEST_ALIAS_TOKENS,
    portfolio_type_to_demand_type,
    portfolio_project_team_aliases,
    portfolio_has_extra_onepage_tag,
    canonicalize_demand_type,
    normalize_project_filter_value,
    done_time_eligible_mask,
    TYPE_SUPPORT,
    TYPE_ISSUES,
    TYPE_DEV,
)


# ---------------------------------------------------------------------------
# is_highest_alias
# ---------------------------------------------------------------------------

class TestIsHighestAlias:
    @pytest.mark.parametrize("value", [
        "Highest", "HIGHEST", "highest",
        "Expedite", "EXPEDITE",
        "Urgent", "URGENT", "urgente",
        "Critical", "CRITICAL", "critico",
        "Blocker", "BLOCKER",
        "Fast Track", "FastTrack",
        "higest",   # typo histórico — deve ser reconhecido
    ])
    def test_recognizes_highest_aliases(self, value):
        assert is_highest_alias(value) is True, f"'{value}' deveria ser Highest alias"

    @pytest.mark.parametrize("value", [
        "Standard", "Normal", "Low", "Medium", "High",
        "Backlog", "", None, "0",
    ])
    def test_rejects_non_highest(self, value):
        assert is_highest_alias(value) is False, f"'{value}' não deveria ser Highest alias"


# ---------------------------------------------------------------------------
# canonicalize_highest_label
# ---------------------------------------------------------------------------

class TestCanonicalizeHighestLabel:
    def test_highest_alias_becomes_highest(self):
        assert canonicalize_highest_label("Expedite") == "Highest"
        assert canonicalize_highest_label("HIGHEST") == "Highest"
        assert canonicalize_highest_label("higest") == "Highest"

    def test_non_alias_preserved(self):
        assert canonicalize_highest_label("Standard") == "Standard"
        assert canonicalize_highest_label("Fixed Date") == "Fixed Date"

    def test_empty_preserved(self):
        assert canonicalize_highest_label("") == ""

    def test_nan_preserved_as_empty(self):
        import numpy as np
        result = canonicalize_highest_label(np.nan)
        assert result == ""


# ---------------------------------------------------------------------------
# resolve_service_class
# ---------------------------------------------------------------------------

class TestResolveServiceClass:
    def test_expedite_class_returns_highest(self):
        result = resolve_service_class("Expedite", "Medium")
        assert result == "Highest"

    def test_standard_fallback_to_priority(self):
        result = resolve_service_class("Standard", "Highest")
        assert result == "Highest"

    def test_standard_priority_standard_returns_standard(self):
        result = resolve_service_class("Standard", "Standard")
        assert result == "Standard"

    def test_empty_class_fallback_to_priority(self):
        result = resolve_service_class("", "Expedite")
        assert result == "Highest"

    def test_none_class_fallback_to_priority(self):
        import numpy as np
        result = resolve_service_class(np.nan, "Expedite")
        assert result == "Highest"

    def test_both_empty_returns_standard(self):
        import numpy as np
        result = resolve_service_class(np.nan, np.nan)
        assert result == "Standard"

    def test_fixed_date_class_preserved(self):
        result = resolve_service_class("Fixed Date", "Low")
        assert result == "Fixed Date"

    def test_intangible_job_preserved(self):
        result = resolve_service_class("Intangible Job", "Low")
        assert result == "Intangible Job"


# ---------------------------------------------------------------------------
# portfolio_type_to_demand_type
# ---------------------------------------------------------------------------

class TestPortfolioTypeToDemandType:
    @pytest.mark.parametrize("tipo,expected", [
        ("Epic", TYPE_DEV),
        ("Epico", TYPE_DEV),
        ("Feature", TYPE_DEV),
        ("Story", TYPE_DEV),
        ("Task", TYPE_DEV),
        ("Spike", TYPE_DEV),
        ("Support", TYPE_SUPPORT),
        ("Suporte", TYPE_SUPPORT),
        ("Bug", TYPE_ISSUES),
        ("Defeito", TYPE_ISSUES),
        ("Issue", TYPE_ISSUES),
        ("Issues", TYPE_ISSUES),
    ])
    def test_type_mapping(self, tipo, expected):
        result = portfolio_type_to_demand_type(tipo)
        assert result == expected, f"'{tipo}' → esperado '{expected}', obtido '{result}'"


# ---------------------------------------------------------------------------
# portfolio_project_team_aliases
# ---------------------------------------------------------------------------

class TestPortfolioProjectTeamAliases:
    def test_w1nner_aliases(self):
        aliases = portfolio_project_team_aliases("W1NNER")
        assert "W1NNER" in aliases
        assert "W1NNR" in aliases

    def test_befinance_aliases(self):
        aliases = portfolio_project_team_aliases("BEFINANCE")
        assert "BEFINANCE" in aliases
        assert "BF" in aliases

    def test_empty_returns_empty(self):
        assert portfolio_project_team_aliases("") == []

    def test_no_duplicates(self):
        aliases = portfolio_project_team_aliases("S1NC")
        # normalize_text deduplication deve evitar duplicatas
        from shared.text_utils import normalize_text
        norms = [normalize_text(a) for a in aliases]
        assert len(norms) == len(set(norms))


# ---------------------------------------------------------------------------
# portfolio_has_extra_onepage_tag
# ---------------------------------------------------------------------------

class TestPortfolioHasExtraOnepageTag:
    def test_detects_tag(self):
        from dashboards.core.data_processing import PORTFOLIO_EXTRA_ONEPAGE_TAG
        assert portfolio_has_extra_onepage_tag(PORTFOLIO_EXTRA_ONEPAGE_TAG) is True

    def test_missing_tag(self):
        assert portfolio_has_extra_onepage_tag("normal label") is False

    def test_empty_returns_false(self):
        assert portfolio_has_extra_onepage_tag("") is False

    def test_none_returns_false(self):
        assert portfolio_has_extra_onepage_tag(None) is False


# ---------------------------------------------------------------------------
# normalize_project_filter_value
# ---------------------------------------------------------------------------

class TestNormalizeProjectFilterValue:
    def test_none_returns_none_or_empty(self):
        result = normalize_project_filter_value(None)
        assert result is None or result == ""

    def test_strips_whitespace(self):
        result = normalize_project_filter_value("  W1NNER  ")
        assert result == result.strip() if result else True


# ---------------------------------------------------------------------------
# done_time_eligible_mask
# ---------------------------------------------------------------------------

class TestDoneTimeEligibleMask:
    def test_eligible_items_pass(self):
        df = pd.DataFrame({
            "ElegivelTempoConcluido": [True, True, False],
            "StatusHistoricoContemCancelamento": [False, False, True],
        })
        mask = done_time_eligible_mask(df)
        assert mask.sum() == 2

    def test_all_cancelled_excluded(self):
        df = pd.DataFrame({
            "ElegivelTempoConcluido": [True, True],
            "StatusHistoricoContemCancelamento": [True, True],
        })
        mask = done_time_eligible_mask(df)
        assert mask.sum() == 0

    def test_empty_df_returns_empty_mask(self):
        df = pd.DataFrame(columns=["ElegivelTempoConcluido", "StatusHistoricoContemCancelamento"])
        mask = done_time_eligible_mask(df)
        assert len(mask) == 0

    def test_missing_column_falls_back_gracefully(self):
        df = pd.DataFrame({"SomeOtherCol": [1, 2, 3]})
        mask = done_time_eligible_mask(df)
        # Deve retornar série booleana sem lançar exceção
        assert hasattr(mask, "__len__")


# ---------------------------------------------------------------------------
# HIGHEST_ALIAS_TOKENS — verificação de qualidade
# ---------------------------------------------------------------------------

class TestHighestAliasTokensQuality:
    def test_no_empty_tokens(self):
        for token in HIGHEST_ALIAS_TOKENS:
            assert token.strip(), f"Token vazio encontrado em HIGHEST_ALIAS_TOKENS: {repr(token)}"

    def test_no_duplicate_tokens(self):
        seen = set()
        for token in HIGHEST_ALIAS_TOKENS:
            assert token not in seen, f"Token duplicado: {repr(token)}"
            seen.add(token)

    def test_higest_typo_corrected(self):
        # O typo "higest" deve ser reconhecido via is_highest_alias
        assert is_highest_alias("higest") is True, "Typo 'higest' deve ainda ser reconhecido"
