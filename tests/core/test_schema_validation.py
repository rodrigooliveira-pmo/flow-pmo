"""Testes de regressão para RF-031/RF-032: SchemaValidationError em load_model_data."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dashboards.core.data_processing import (
    SchemaValidationError,
    _validate_required_columns,
)


# ---------------------------------------------------------------------------
# _validate_required_columns
# ---------------------------------------------------------------------------

class TestValidateRequiredColumns:
    def test_passes_when_all_present(self):
        df = pd.DataFrame({"ProjetoID": [1], "NomeProjeto": ["W1NNER"]})
        _validate_required_columns(df, ("ProjetoID", "NomeProjeto"), "Dim_Projeto")

    def test_raises_when_column_missing(self):
        df = pd.DataFrame({"ProjetoID": [1]})
        with pytest.raises(SchemaValidationError) as exc_info:
            _validate_required_columns(df, ("ProjetoID", "NomeProjeto"), "Dim_Projeto")
        assert "NomeProjeto" in str(exc_info.value)
        assert "Dim_Projeto" in str(exc_info.value)

    def test_error_message_contains_sheet_name(self):
        df = pd.DataFrame({"X": [1]})
        with pytest.raises(SchemaValidationError) as exc_info:
            _validate_required_columns(df, ("ProjetoID",), "Fato_Items")
        assert "Fato_Items" in str(exc_info.value)

    def test_error_lists_all_missing(self):
        df = pd.DataFrame({"Z": [1]})
        with pytest.raises(SchemaValidationError) as exc_info:
            _validate_required_columns(df, ("A", "B", "C"), "Sheet")
        msg = str(exc_info.value)
        assert "A" in msg
        assert "B" in msg
        assert "C" in msg

    def test_empty_required_never_raises(self):
        df = pd.DataFrame({"X": [1]})
        _validate_required_columns(df, (), "Sheet")

    def test_empty_df_raises_for_required_columns(self):
        df = pd.DataFrame()
        with pytest.raises(SchemaValidationError):
            _validate_required_columns(df, ("ProjetoID",), "Dim_Projeto")


# ---------------------------------------------------------------------------
# SchemaValidationError is a ValueError subclass
# ---------------------------------------------------------------------------

class TestSchemaValidationError:
    def test_is_value_error(self):
        err = SchemaValidationError("test")
        assert isinstance(err, ValueError)

    def test_message_preserved(self):
        msg = "SchemaValidationError: missing columns ['DataDone']"
        err = SchemaValidationError(msg)
        assert msg in str(err)


# ---------------------------------------------------------------------------
# load_model_data — schema validation integration (mocked Excel)
# ---------------------------------------------------------------------------

class TestLoadModelDataSchemaValidation:
    def _make_excel_mock(self, fato_cols=None, dim_projeto_cols=None, dim_tipo_cols=None):
        """Create a mock ExcelFile with the given column sets."""
        fato_cols = fato_cols or ["ProjetoID", "TipoID"]
        dim_projeto_cols = dim_projeto_cols or ["ProjetoID", "NomeProjeto"]
        dim_tipo_cols = dim_tipo_cols or ["TipoID", "Tipo"]

        mock_xls = MagicMock()
        mock_xls.sheet_names = ["Fato_Items", "Dim_Projeto", "Dim_Tipo"]

        def read_excel_side_effect(sheet_name=None, **kwargs):
            if sheet_name == "Dim_Projeto":
                return pd.DataFrame(columns=dim_projeto_cols)
            if sheet_name == "Dim_Tipo":
                return pd.DataFrame(columns=dim_tipo_cols)
            if sheet_name == "Fato_Items":
                return pd.DataFrame(columns=fato_cols)
            return pd.DataFrame()

        mock_xls.parse = read_excel_side_effect
        return mock_xls

    def test_raises_on_missing_fato_column(self):
        from dashboards.core.data_processing import load_model_data
        mock_xls = MagicMock()
        mock_xls.sheet_names = ["Fato_Items", "Dim_Projeto", "Dim_Tipo"]

        with patch("dashboards.core.data_processing.pd.ExcelFile") as mock_ef, \
             patch("pandas.read_excel") as mock_read:

            def side_effect(xls, sheet_name=None, **kwargs):
                if sheet_name == "Dim_Projeto":
                    return pd.DataFrame({"ProjetoID": [1], "NomeProjeto": ["W1NNER"]})
                if sheet_name == "Dim_Tipo":
                    return pd.DataFrame({"TipoID": [1], "Tipo": ["Epic"]})
                if sheet_name == "Fato_Items":
                    # Missing TipoID
                    return pd.DataFrame({"ProjetoID": [1]})
                return pd.DataFrame()

            mock_ef.return_value.__enter__ = lambda s: s
            mock_ef.return_value.__exit__ = MagicMock(return_value=False)
            mock_read.side_effect = side_effect

            with pytest.raises(SchemaValidationError) as exc_info:
                load_model_data("fake.xlsx")
            assert "TipoID" in str(exc_info.value)
