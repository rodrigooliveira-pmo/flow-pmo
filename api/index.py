"""Vercel Python entrypoint for the Dash application.

Seleciona o dashboard a servir via variáveis de ambiente:

  FLOW_PMO_DASH_MODULE  Nome do módulo Python a importar (padrão: dashboard_full)
  FLOW_PMO_DASH_ATTR    Atributo do módulo que contém o app Dash (padrão: app)

Dashboards disponíveis:
  dashboard_full          Dashboard principal com Flow Metrics, Portfólio e Process Mining
  dashboard_process_mining  Dashboard standalone dedicado ao Process Mining (análise detalhada)
  dashboard_spaf          Dashboard standalone dedicado ao módulo SPAF

Exemplos de configuração no Vercel (env vars):
  FLOW_PMO_DASH_MODULE=dashboard_full          → dashboard principal (padrão)
  FLOW_PMO_DASH_MODULE=dashboard_process_mining → somente process mining
  FLOW_PMO_DASH_MODULE=dashboard_spaf          → módulo SPAF standalone
"""

import importlib
import os
import sys
import traceback

# Ensure the project root is on sys.path so `auth` can be imported from api/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import Flask, Response

DASH_MODULE = os.getenv("FLOW_PMO_DASH_MODULE", "dashboard_full")
DASH_ATTR = os.getenv("FLOW_PMO_DASH_ATTR", "app")

app = None  # defined at top-level so Vercel can detect the entrypoint

try:
    module = importlib.import_module(DASH_MODULE)
    dash_obj = getattr(module, DASH_ATTR)
    # Dash instance exposes the Flask app in `.server`.
    app = getattr(dash_obj, "server", dash_obj)

    # Attach Google OAuth authentication (no-op if env vars not set in dev)
    try:
        from auth import init_app as _init_auth
        _init_auth(app)
    except RuntimeError as _auth_exc:
        import warnings
        warnings.warn(f"Auth não inicializada: {_auth_exc}", stacklevel=1)

except Exception as exc:  # pragma: no cover - runtime safeguard
    error_message = str(exc)
    error_trace = traceback.format_exc()
    try:
        import dash
        from dash import html

        diagnostic_dash = dash.Dash(__name__)
        diagnostic_dash.title = "Falha ao inicializar dashboard"
        diagnostic_dash.layout = html.Div(
            [
                html.H2("Falha ao inicializar o dashboard"),
                html.P(f"Módulo alvo: {DASH_MODULE}.{DASH_ATTR}"),
                html.P(f"Erro: {error_message}"),
                html.Pre(
                    error_trace,
                    style={
                        "whiteSpace": "pre-wrap",
                        "background": "#111",
                        "color": "#eee",
                        "padding": "12px",
                        "borderRadius": "6px",
                        "overflowX": "auto",
                        "fontSize": "12px",
                    },
                ),
            ],
            style={"maxWidth": "1100px", "margin": "24px auto", "fontFamily": "Arial, sans-serif"},
        )
        app = diagnostic_dash.server
    except Exception:
        fallback = Flask(__name__)

        @fallback.get("/")
        @fallback.get("/<path:_path>")
        def _startup_error(_path=None):
            return Response(
                (
                    f"Falha ao inicializar o Dash ({DASH_MODULE}.{DASH_ATTR}): {error_message}\n\n"
                    f"{error_trace}"
                ),
                status=500,
                mimetype="text/plain",
            )

        app = fallback
