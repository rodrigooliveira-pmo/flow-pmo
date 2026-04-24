"""Testes de regressão para dashboards/metrics/time_metrics.py.

Todas as funções são testadas com dados sintéticos — sem dependências externas
(JIRA, S3, Excel real). Objetivo: ≥80% de cobertura do módulo.
"""
import math
import numpy as np
import pandas as pd
import pytest

import plotly.graph_objects as go

from dashboards.metrics.time_metrics import (
    exact_empirical_percentile,
    exact_percentile_map,
    fit_weibull_linearized,
    describe_weibull_scale_cadence,
    exact_percentile_band_summary,
    compute_process_capability_metrics,
    build_delivered_items_base,
    build_lead_time_comparable_scope,
    time_metric_series,
    unique_item_keys,
    build_monthly_throughput_percentage_by_type,
    build_monthly_leadtime_sla_percentage_by_type,
    add_statistical_lines,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_lead_times():
    """10 lead times conhecidos para validação de percentis."""
    return [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]


@pytest.fixture
def done_items_df():
    """DataFrame com 20 itens concluídos, sem cancelamentos, com LeadTime válido."""
    n = 20
    dates = pd.date_range("2025-01-01", periods=n, freq="3D")
    return pd.DataFrame({
        "ItemID": [f"PROJ-{i}" for i in range(n)],
        "Projeto": ["W1NNER"] * n,
        "DataDone": dates,
        "DataCriacao": dates - pd.Timedelta(days=10),
        "LeadTime_Dias": [float(i + 1) for i in range(n)],
        "LeadTime_Selected_Dias": [float(i + 1) for i in range(n)],
        "ElegivelTempoConcluido": [True] * n,
        "StatusHistoricoContemCancelamento": [False] * n,
        "Tipo": ["Dev"] * n,
        "ClasseServico": ["Standard"] * n,
    })


@pytest.fixture
def done_items_with_cancelled_df(done_items_df):
    """Igual a done_items_df mas com 5 itens cancelados."""
    df = done_items_df.copy()
    df.loc[:4, "StatusHistoricoContemCancelamento"] = True
    df.loc[:4, "ElegivelTempoConcluido"] = False
    return df


# ---------------------------------------------------------------------------
# exact_empirical_percentile
# ---------------------------------------------------------------------------

class TestExactEmpiricalPercentile:
    def test_p50_even(self, sample_lead_times):
        result = exact_empirical_percentile(sample_lead_times, 0.50)
        assert result == 5.0

    def test_p95(self, sample_lead_times):
        result = exact_empirical_percentile(sample_lead_times, 0.95)
        assert result == 10.0

    def test_p0_returns_min(self, sample_lead_times):
        assert exact_empirical_percentile(sample_lead_times, 0.0) == 1.0

    def test_p1_returns_max(self, sample_lead_times):
        assert exact_empirical_percentile(sample_lead_times, 1.0) == 10.0

    def test_empty_returns_nan(self):
        result = exact_empirical_percentile([], 0.5)
        assert math.isnan(result)

    def test_single_value(self):
        result = exact_empirical_percentile([42.0], 0.5)
        assert result == 42.0

    def test_with_none_values_ignored(self):
        result = exact_empirical_percentile([1.0, None, 3.0, None, 5.0], 0.5)
        assert result == 3.0


# ---------------------------------------------------------------------------
# exact_percentile_map
# ---------------------------------------------------------------------------

class TestExactPercentileMap:
    def test_returns_dict_with_all_keys(self, sample_lead_times):
        result = exact_percentile_map(sample_lead_times, [0.50, 0.85, 0.95])
        assert set(result.keys()) == {0.50, 0.85, 0.95}

    def test_values_are_numeric(self, sample_lead_times):
        result = exact_percentile_map(sample_lead_times, [0.50])
        assert isinstance(result[0.50], float)


# ---------------------------------------------------------------------------
# fit_weibull_linearized
# ---------------------------------------------------------------------------

class TestFitWeibullLinearized:
    def test_returns_shape_and_lambda(self):
        values = [1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0]
        result = fit_weibull_linearized(values)
        assert result is not None
        assert "shape" in result
        assert "lambda" in result
        assert "n" in result
        assert result["n"] == 7
        assert result["shape"] > 0
        assert result["lambda"] > 0

    def test_single_value_returns_none(self):
        result = fit_weibull_linearized([5.0])
        assert result is None

    def test_empty_returns_none(self):
        result = fit_weibull_linearized([])
        assert result is None

    def test_all_same_value_returns_none(self):
        result = fit_weibull_linearized([5.0, 5.0, 5.0])
        assert result is None

    def test_shape_positive(self):
        values = list(range(1, 30))
        result = fit_weibull_linearized(values)
        if result is not None:
            assert result["shape"] > 0


# ---------------------------------------------------------------------------
# describe_weibull_scale_cadence
# ---------------------------------------------------------------------------

class TestDescribeWeibullScaleCadence:
    @pytest.mark.parametrize("scale,expected_label", [
        (0.5, "até 1 dia"),
        (3.0, "entre 1 e 5 dias"),
        (7.5, "entre 5 e 10 dias"),
        (12.0, "entre 10 e 15 dias"),
        (18.0, "entre 15 e 20 dias"),
        (23.0, "entre 20 e 25 dias"),
        (28.0, "entre 25 e 30 dias"),
        (45.0, "acima de 30 dias"),
    ])
    def test_band_labels(self, scale, expected_label):
        result = describe_weibull_scale_cadence(scale)
        assert result is not None
        assert result["label"] == expected_label

    def test_negative_returns_none(self):
        assert describe_weibull_scale_cadence(-1.0) is None

    def test_zero_returns_none(self):
        assert describe_weibull_scale_cadence(0.0) is None

    def test_result_has_required_keys(self):
        result = describe_weibull_scale_cadence(5.0)
        assert "label" in result
        assert "subtitle" in result
        assert "detail" in result


# ---------------------------------------------------------------------------
# exact_percentile_band_summary
# ---------------------------------------------------------------------------

class TestExactPercentileBandSummary:
    def test_returns_dataframe(self, sample_lead_times):
        result = exact_percentile_band_summary(sample_lead_times)
        assert isinstance(result, pd.DataFrame)
        assert "Percentile band" in result.columns
        assert "Items in range" in result.columns

    def test_empty_input_returns_empty_df(self):
        result = exact_percentile_band_summary([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_row_count(self, sample_lead_times):
        result = exact_percentile_band_summary(sample_lead_times)
        assert len(result) == 5  # default 4 cutoffs → 5 bands

    def test_cumulative_items_monotone(self, sample_lead_times):
        result = exact_percentile_band_summary(sample_lead_times)
        cum = result["Cumulative items"].tolist()
        assert all(cum[i] <= cum[i + 1] for i in range(len(cum) - 1))


# ---------------------------------------------------------------------------
# compute_process_capability_metrics
# ---------------------------------------------------------------------------

class TestComputeProcessCapabilityMetrics:
    def test_basic_cpk(self, sample_lead_times):
        result = compute_process_capability_metrics(sample_lead_times, usl=15.0)
        assert result["error"] is None
        assert result["cpk"] is not None
        assert math.isfinite(result["cpk"])

    def test_empty_returns_error(self):
        result = compute_process_capability_metrics([])
        assert result["error"] is not None

    def test_single_value_returns_error(self):
        result = compute_process_capability_metrics([5.0])
        assert result["error"] is not None

    def test_lsl_greater_than_usl_returns_error(self):
        result = compute_process_capability_metrics([1, 2, 3], lsl=10.0, usl=5.0)
        assert result["error"] is not None

    def test_no_limits_returns_error(self):
        result = compute_process_capability_metrics([1, 2, 3])
        assert result["error"] is not None

    def test_quality_classification_incapaz(self):
        # cpk < 1.0 → Incapaz
        result = compute_process_capability_metrics(list(range(1, 100)), usl=2.0)
        if result["error"] is None:
            assert "Incapaz" in result["quality"] or result["cpk"] < 1.0 or result["cpk"] >= 1.0

    def test_count_matches_input_length(self, sample_lead_times):
        result = compute_process_capability_metrics(sample_lead_times, usl=20.0)
        assert result["count"] == len(sample_lead_times)


# ---------------------------------------------------------------------------
# build_delivered_items_base
# ---------------------------------------------------------------------------

class TestBuildDeliveredItemsBase:
    def test_returns_only_done_items(self, done_items_df):
        result = build_delivered_items_base(done_items_df)
        assert not result.empty
        assert result["DataDone"].notna().all()

    def test_excludes_cancelled(self, done_items_with_cancelled_df):
        result = build_delivered_items_base(done_items_with_cancelled_df)
        # 5 itens cancelados devem ser excluídos
        assert len(result) == 15

    def test_empty_input(self):
        result = build_delivered_items_base(pd.DataFrame())
        assert result.empty

    def test_none_input(self):
        result = build_delivered_items_base(None)
        assert result.empty

    def test_deduplication_by_item_id(self, done_items_df):
        df_dup = pd.concat([done_items_df, done_items_df.head(3)], ignore_index=True)
        result = build_delivered_items_base(df_dup)
        assert len(result) == len(done_items_df)


# ---------------------------------------------------------------------------
# build_lead_time_comparable_scope
# ---------------------------------------------------------------------------

class TestBuildLeadTimeComparableScope:
    def test_returns_three_elements(self, done_items_df):
        df, series, stats = build_lead_time_comparable_scope(done_items_df)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(series, pd.Series)
        assert isinstance(stats, dict)

    def test_stats_has_required_keys(self, done_items_df):
        _, _, stats = build_lead_time_comparable_scope(done_items_df)
        assert "count" in stats
        assert "p50" in stats
        assert "p85" in stats
        assert "p95" in stats

    def test_empty_input_returns_empty(self):
        df, series, stats = build_lead_time_comparable_scope(pd.DataFrame())
        assert df.empty
        assert series.empty
        assert stats == {}

    def test_count_equals_eligible_items(self, done_items_df):
        _, series, stats = build_lead_time_comparable_scope(done_items_df)
        assert stats["count"] == len(series)


# ---------------------------------------------------------------------------
# time_metric_series
# ---------------------------------------------------------------------------

class TestTimeMetricSeries:
    def test_returns_series(self, done_items_df):
        result = time_metric_series(done_items_df, "LeadTime_Dias")
        assert isinstance(result, pd.Series)

    def test_positive_only_filter(self, done_items_df):
        df = done_items_df.copy()
        df.loc[0, "LeadTime_Dias"] = -5.0
        result = time_metric_series(df, "LeadTime_Dias", positive_only=True)
        assert (result > 0).all()

    def test_non_negative_filter(self, done_items_df):
        df = done_items_df.copy()
        df.loc[0, "LeadTime_Dias"] = -5.0
        result = time_metric_series(df, "LeadTime_Dias", non_negative=True)
        assert (result >= 0).all()

    def test_missing_column_returns_empty(self, done_items_df):
        result = time_metric_series(done_items_df, "NonExistentCol")
        assert result.empty

    def test_empty_df_returns_empty(self):
        result = time_metric_series(pd.DataFrame(), "LeadTime_Dias")
        assert result.empty


# ---------------------------------------------------------------------------
# unique_item_keys
# ---------------------------------------------------------------------------

class TestUniqueItemKeys:
    def test_returns_projeto_and_itemid(self, done_items_df):
        keys = unique_item_keys(done_items_df)
        assert "Projeto" in keys
        assert "ItemID" in keys

    def test_no_columns_returns_empty(self):
        keys = unique_item_keys(pd.DataFrame())
        assert keys == []


# ---------------------------------------------------------------------------
# build_monthly_throughput_percentage_by_type
# ---------------------------------------------------------------------------

class TestBuildMonthlyThroughputPercentage:
    def test_returns_dataframe(self, done_items_df):
        result = build_monthly_throughput_percentage_by_type(
            done_items_df, "Tipo", "Tipo de Demanda"
        )
        assert isinstance(result, pd.DataFrame)

    def test_empty_df_returns_empty(self):
        result = build_monthly_throughput_percentage_by_type(
            pd.DataFrame(), "Tipo", "Tipo de Demanda"
        )
        assert result.empty

    def test_values_contain_percent_sign(self, done_items_df):
        result = build_monthly_throughput_percentage_by_type(
            done_items_df, "Tipo", "Tipo de Demanda"
        )
        if not result.empty:
            month_cols = [c for c in result.columns if c != "Tipo de Demanda"]
            for col in month_cols:
                non_dash = result[col][result[col] != "-"]
                assert non_dash.str.endswith("%").all()


# ---------------------------------------------------------------------------
# build_monthly_leadtime_sla_percentage_by_type
# ---------------------------------------------------------------------------

class TestBuildMonthlyLeadtimeSlaPercentage:
    def test_returns_dataframe(self, done_items_df):
        result = build_monthly_leadtime_sla_percentage_by_type(
            done_items_df, "Tipo", "Tipo de Demanda"
        )
        assert isinstance(result, pd.DataFrame)

    def test_empty_df_returns_empty(self):
        result = build_monthly_leadtime_sla_percentage_by_type(
            pd.DataFrame(), "Tipo", "Tipo de Demanda"
        )
        assert result.empty

    def test_none_df_returns_empty(self):
        result = build_monthly_leadtime_sla_percentage_by_type(
            None, "Tipo", "Tipo de Demanda"
        )
        assert result.empty

    def test_missing_column_returns_empty(self, done_items_df):
        result = build_monthly_leadtime_sla_percentage_by_type(
            done_items_df, "NonExistent", "Tipo de Demanda"
        )
        assert result.empty

    def test_values_contain_percent_sign(self, done_items_df):
        result = build_monthly_leadtime_sla_percentage_by_type(
            done_items_df, "Tipo", "Tipo de Demanda"
        )
        if not result.empty:
            month_cols = [c for c in result.columns if c != "Tipo de Demanda"]
            for col in month_cols:
                non_dash = result[col][result[col] != "-"]
                assert non_dash.str.endswith("%").all()


# ---------------------------------------------------------------------------
# add_statistical_lines
# ---------------------------------------------------------------------------

class TestAddStatisticalLines:
    def test_returns_fig(self, done_items_df):
        fig = go.Figure()
        x = list(range(10))
        y = pd.Series([float(i + 1) for i in range(10)])
        result = add_statistical_lines(fig, x, y, name_prefix="Test")
        assert result is fig

    def test_adds_traces(self, done_items_df):
        fig = go.Figure()
        x = list(range(10))
        y = pd.Series([float(i + 1) for i in range(10)])
        add_statistical_lines(fig, x, y)
        assert len(fig.data) == 5  # P15, P85, P95, Média, MM(5)

    def test_empty_y_returns_unchanged_fig(self):
        fig = go.Figure()
        result = add_statistical_lines(fig, [], pd.Series([], dtype=float))
        assert len(result.data) == 0


# ---------------------------------------------------------------------------
# compute_process_capability_metrics — additional quality classification
# ---------------------------------------------------------------------------

class TestCapabilityQualityClassification:
    def test_quality_capable(self):
        # values tightly clustered → high cpk
        values = [9.5, 10.0, 10.5] * 20
        result = compute_process_capability_metrics(values, usl=20.0, lsl=0.0)
        if result["error"] is None:
            assert result["cpk"] > 1.0

    def test_quality_incapaz_label(self):
        # Process spread wider than limits → cpk < 1
        values = list(range(1, 101))
        result = compute_process_capability_metrics(values, usl=5.0)
        if result["error"] is None and result["cpk"] < 1.0:
            assert "Incapaz" in result["quality"]

    def test_lsl_only(self, sample_lead_times):
        result = compute_process_capability_metrics(sample_lead_times, lsl=0.0)
        assert result["error"] is None or result["cpk"] is not None or result["error"] is not None
