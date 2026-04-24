"""Utilitário de error boundary para callbacks Dash."""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional

from dash.exceptions import PreventUpdate

_logger = logging.getLogger("flow_pmo.callbacks")


def error_boundary(fallback: Any = None) -> Callable:
    """Decorator que protege callbacks Dash de falhas silenciosas.

    Captura qualquer Exception, loga o traceback e retorna `fallback`.
    PreventUpdate propaga normalmente (não é erro de negócio).

    Uso:
        @app.callback(...)
        @error_boundary(fallback=html.Div("Erro ao carregar."))
        def my_callback(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except PreventUpdate:
                raise
            except Exception as exc:
                _logger.error(
                    "Callback %r falhou: %s",
                    func.__name__,
                    exc,
                    exc_info=True,
                )
                if fallback is not None:
                    return fallback
                raise PreventUpdate
        return wrapper
    return decorator


def callback_error_div(message: str = "Erro ao carregar o conteúdo. Verifique os filtros e tente novamente.") -> Any:
    """Retorna um html.Div com mensagem de erro padronizada."""
    try:
        from dash import html
        return html.Div(
            [
                html.P(
                    f"⚠️ {message}",
                    style={
                        "color": "#b91c1c",
                        "textAlign": "center",
                        "padding": "16px",
                        "fontSize": "14px",
                    },
                )
            ],
            style={
                "border": "1px solid #fca5a5",
                "borderRadius": "8px",
                "margin": "20px auto",
                "maxWidth": "720px",
                "backgroundColor": "#fff5f5",
            },
        )
    except ImportError:
        return message
