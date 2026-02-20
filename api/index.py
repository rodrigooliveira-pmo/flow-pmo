"""Vercel Python entrypoint for the Dash application."""

import importlib
import os

from flask import Flask, Response

DASH_MODULE = os.getenv("FLOW_PMO_DASH_MODULE", "dashboard_full")
DASH_ATTR = os.getenv("FLOW_PMO_DASH_ATTR", "app")

try:
    module = importlib.import_module(DASH_MODULE)
    dash_obj = getattr(module, DASH_ATTR)
    # Dash instance exposes the Flask app in `.server`.
    app = getattr(dash_obj, "server", dash_obj)
except Exception as exc:  # pragma: no cover - runtime safeguard
    error_message = str(exc)
    fallback = Flask(__name__)

    @fallback.get("/")
    @fallback.get("/<path:_path>")
    def _startup_error(_path=None):
        return Response(
            f"Falha ao inicializar o Dash ({DASH_MODULE}.{DASH_ATTR}): {error_message}",
            status=500,
            mimetype="text/plain",
        )

    app = fallback
