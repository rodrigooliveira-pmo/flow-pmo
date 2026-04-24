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
    apply_portfolio_module_filters,
    canonicalize_demand_type,
    normalize_project_filter_value,
    done_time_eligible_mask,
    process_fato_data,
    unique_sorted,
    TYPE_SUPPORT,
    TYPE_ISSUES,
    TYPE_DEV,
    TYPE_OTHER,
    PROJECT_FILTER_ALL_VALUE,
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

    def test_non_standard_class_with_empty_priority(self):
        import numpy as np
        result = resolve_service_class("Fixed Date", np.nan)
        assert result == "Fixed Date"

    def test_standard_class_nan_priority_returns_standard(self):
        import numpy as np
        result = resolve_service_class("Standard", np.nan)
        assert result == "Standard"


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

    def test_fallback_to_canonicalize(self):
        result = portfolio_type_to_demand_type("Desenvolvimento")
        assert result == TYPE_DEV


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

    def test_non_special_value_returned_as_is(self):
        result = normalize_project_filter_value("W1NNER")
        assert result == "W1NNER"


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
            "ElegivelTempoConcluido": [False, False],
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


# ---------------------------------------------------------------------------
# canonicalize_demand_type
# ---------------------------------------------------------------------------

class TestCanonicalizeDemandType:
    @pytest.mark.parametrize("tipo,expected", [
        ("Desenvolvimento", TYPE_DEV),
        ("Development", TYPE_DEV),
        ("Support", TYPE_SUPPORT),
        ("Suporte", TYPE_SUPPORT),
        ("Bug", TYPE_ISSUES),
        ("issue", TYPE_ISSUES),
        ("Ad Hoc", TYPE_DEV),
        ("Outro", TYPE_OTHER),
        ("Other", TYPE_OTHER),
    ])
    def test_type_mapping(self, tipo, expected):
        assert canonicalize_demand_type(tipo) == expected

    def test_none_returns_other_or_raw(self):
        result = canonicalize_demand_type(None)
        assert result is not None

    def test_type_issues_normalized_value_matches(self):
        # Cover line 288: tipo_norm == normalize_text(TYPE_ISSUES)
        result = canonicalize_demand_type(TYPE_ISSUES)
        assert result == TYPE_ISSUES


# ---------------------------------------------------------------------------
# normalize_project_filter_value — extended
# ---------------------------------------------------------------------------

class TestNormalizeProjectFilterValueExtended:
    def test_all_projects_sentinel_returns_none(self):
        result = normalize_project_filter_value(PROJECT_FILTER_ALL_VALUE)
        assert result is None

    def test_empty_string_returns_none(self):
        result = normalize_project_filter_value("")
        assert result is None

    def test_valid_project_returned_unchanged(self):
        assert normalize_project_filter_value("S1NC") == "S1NC"


# ---------------------------------------------------------------------------
# process_fato_data
# ---------------------------------------------------------------------------

class TestProcessFatoData:
    def test_adds_classe_servico_if_missing(self):
        df = pd.DataFrame({"NomeProjeto": ["W1NNER"], "TipoID": [1]})
        result = process_fato_data(df)
        assert "ClasseServico" in result.columns

    def test_adds_prioridade_if_missing(self):
        df = pd.DataFrame({"NomeProjeto": ["W1NNER"]})
        result = process_fato_data(df)
        assert "Prioridade" in result.columns

    def test_renames_nome_projeto_to_projeto(self):
        df = pd.DataFrame({"NomeProjeto": ["W1NNER"], "Prioridade": ["Standard"]})
        result = process_fato_data(df)
        assert "Projeto" in result.columns

    def test_canonicalizes_prioridade(self):
        df = pd.DataFrame({"Prioridade": ["Expedite", "Standard"]})
        result = process_fato_data(df)
        assert result["Prioridade"].iloc[0] == "Highest"
        assert result["Prioridade"].iloc[1] == "Standard"

    def test_resolves_classe_servico(self):
        df = pd.DataFrame({
            "ClasseServico": ["", "Fixed Date"],
            "Prioridade": ["Urgent", "Low"],
        })
        result = process_fato_data(df)
        assert result["ClasseServico"].iloc[0] == "Highest"
        assert result["ClasseServico"].iloc[1] == "Fixed Date"


# ---------------------------------------------------------------------------
# unique_sorted
# ---------------------------------------------------------------------------

class TestUniqueSorted:
    def test_returns_sorted_unique(self):
        s = pd.Series(["B", "A", "C", "A", None])
        result = unique_sorted(s)
        assert result == ["A", "B", "C"]

    def test_empty_series(self):
        result = unique_sorted(pd.Series([], dtype=str))
        assert result == []


# ---------------------------------------------------------------------------
# done_time_eligible_mask — fallback paths
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# apply_portfolio_module_filters
# ---------------------------------------------------------------------------

@pytest.fixture
def portfolio_df():
    return pd.DataFrame({
        "Tipo": ["Epic", "Bug", "Support", "Story"],
        "Prioridade": ["Standard", "Highest", "Standard", "Standard"],
        "ClasseServico": ["Standard", "", "Standard", "Fixed Date"],
        "Team": ["W1NNER", "W1NNER", "S1NC", "S1NC"],
        "Responsavel": ["Alice", "Bob", "Carol", "Dave"],
    })


class TestApplyPortfolioModuleFilters:
    def test_empty_df_returns_empty(self):
        result_df, project, notes = apply_portfolio_module_filters(pd.DataFrame())
        assert result_df.empty

    def test_none_df_returns_empty(self):
        result_df, project, notes = apply_portfolio_module_filters(None)
        assert result_df.empty

    def test_no_filter_returns_all(self, portfolio_df):
        result_df, project, notes = apply_portfolio_module_filters(portfolio_df)
        assert len(result_df) == len(portfolio_df)
        assert project is None
        assert notes == []

    def test_portfolio_project_filter(self, portfolio_df):
        result_df, project, notes = apply_portfolio_module_filters(
            portfolio_df, portfolio_project="W1NNER"
        )
        assert project == "W1NNER"
        assert (result_df["Team"] == "W1NNER").all()

    def test_tipo_filter(self, portfolio_df):
        result_df, _, notes = apply_portfolio_module_filters(
            portfolio_df, tipo=TYPE_DEV
        )
        assert (result_df["PortfolioTipoDemanda"] == TYPE_DEV).all()

    def test_missing_team_column_returns_empty_with_note(self):
        df = pd.DataFrame({"Tipo": ["Epic"]})
        result_df, project, notes = apply_portfolio_module_filters(
            df, portfolio_project="W1NNER"
        )
        assert result_df.empty
        assert any("Team" in n or "coluna" in n.lower() for n in notes)

    def test_adds_portfolio_tipo_demanda_column(self, portfolio_df):
        result_df, _, _ = apply_portfolio_module_filters(portfolio_df)
        assert "PortfolioTipoDemanda" in result_df.columns

    def test_quarter_filter(self, portfolio_df):
        df = portfolio_df.copy()
        df["DueDate"] = pd.to_datetime([
            "2026-01-15", "2026-07-01", "2026-04-01", "2026-02-28"
        ])
        result_df, _, _ = apply_portfolio_module_filters(df, portfolio_quarter="Q1-2026")
        assert len(result_df) == 2  # Jan-15 and Feb-28 in Q1

    def test_hint_project_uses_aliases(self, portfolio_df):
        result_df, project, _ = apply_portfolio_module_filters(
            portfolio_df, projeto="W1NNER"
        )
        assert project == "W1NNER"
        assert len(result_df) > 0

    def test_team_filter_no_match_adds_note(self, portfolio_df):
        result_df, _, notes = apply_portfolio_module_filters(
            portfolio_df, portfolio_project="NONEXISTENT_TEAM"
        )
        assert result_df.empty
        assert len(notes) > 0

    def test_hint_project_no_team_column_returns_empty_with_note(self):
        df = pd.DataFrame({"Tipo": ["Epic"]})
        result_df, project, notes = apply_portfolio_module_filters(
            df, projeto="W1NNER"
        )
        assert result_df.empty
        assert any("Team" in n or "coluna" in n.lower() for n in notes)

    def test_tipo_filter_no_match_adds_note(self, portfolio_df):
        result_df, _, notes = apply_portfolio_module_filters(
            portfolio_df, tipo="NONEXISTENT_TYPE"
        )
        assert result_df.empty
        assert len(notes) > 0

    def test_classe_servico_filter(self, portfolio_df):
        result_df, _, notes = apply_portfolio_module_filters(
            portfolio_df, classe_servico="Fixed Date"
        )
        assert (result_df["ClasseServico"] == "Fixed Date").all()

    def test_classe_servico_no_match_adds_note(self, portfolio_df):
        result_df, _, notes = apply_portfolio_module_filters(
            portfolio_df, classe_servico="NONEXISTENT"
        )
        assert result_df.empty
        assert len(notes) > 0

    def test_responsavel_no_column_adds_note(self):
        df = pd.DataFrame({"Tipo": ["Epic"]})
        result_df, _, notes = apply_portfolio_module_filters(df, responsavel="Alice")
        assert result_df.empty
        assert len(notes) > 0

    def test_df_without_tipo_column(self):
        df = pd.DataFrame({"ClasseServico": ["Standard"], "Team": ["W1NNER"]})
        result_df, _, _ = apply_portfolio_module_filters(df)
        assert "PortfolioTipoDemanda" in result_df.columns


# ---------------------------------------------------------------------------
# done_time_eligible_mask — fallback paths
# ---------------------------------------------------------------------------

class TestDoneTimeEligibleMaskFallback:
    def test_fallback_cancelado_column(self):
        df = pd.DataFrame({"Cancelado": [0, 1, 0]})
        mask = done_time_eligible_mask(df)
        assert mask.sum() == 2

    def test_fallback_data_cancelled_column(self):
        df = pd.DataFrame({
            "DataCancelled": [pd.NaT, pd.Timestamp("2025-01-01"), pd.NaT]
        })
        mask = done_time_eligible_mask(df)
        assert mask.sum() == 2
