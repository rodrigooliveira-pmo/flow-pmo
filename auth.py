"""Google Workspace OAuth 2.0 authentication for the Dash/Flask dashboard.

Exposes a single entry point:

    from auth import init_app
    init_app(flask_server)

Environment variables required:
    GOOGLE_CLIENT_ID        — OAuth 2.0 client ID from Google Cloud Console
    GOOGLE_CLIENT_SECRET    — OAuth 2.0 client secret
    FLASK_SECRET_KEY        — random secret used to sign Flask sessions
    FLOW_PMO_ALLOWED_DOMAIN — principal Google Workspace domain used as the
                              Google login hint (`hd`) and tenant label shown
                              on the auth screen.

Optional:
    FLOW_PMO_ALLOWED_EMAILS — comma-separated static allowlist of specific
                              e-mails. This is the current access-control gate
                              when group membership is not configured.
    FLOW_PMO_ALLOWED_GROUP  — Google Workspace group allowed to access the app.
                              Used only together with GOOGLE_SERVICE_ACCOUNT_JSON
                              and GOOGLE_IMPERSONATE_EMAIL.
"""

import base64
import binascii
import json
import os

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, render_template_string, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_service_account_info(raw_value: str) -> dict:
    """Parse service-account credentials from env.

    Accepts raw JSON, JSON encoded with literal ``\\n`` sequences, or a base64
    representation of the JSON payload.
    """
    value = _strip_wrapping_quotes(raw_value)
    if not value:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON vazio.")

    candidates: list[str] = [value]
    if "\\n" in value:
        candidates.append(value.replace("\\n", "\n"))

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON inválido: informe JSON puro, JSON com "
            "\\n escapado ou o conteúdo em base64."
        ) from exc

    for candidate in (decoded, decoded.replace("\\n", "\n")):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(
        "GOOGLE_SERVICE_ACCOUNT_JSON inválido: o conteúdo base64 decodificado "
        "não é um JSON de service account válido."
    )


def _is_group_member(email: str, group_email: str, sa_info: dict, impersonate: str) -> bool:
    """Check if *email* belongs to the given Google Workspace group.

    Uses a service account with Domain-Wide Delegation to call the
    Admin SDK Directory API (members.hasMember endpoint).
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/admin.directory.group.member.readonly"],
    ).with_subject(impersonate)

    service = build("admin", "directory_v1", credentials=creds, cache_discovery=False)
    result = (
        service.members()
        .hasMember(groupKey=group_email, memberKey=email)
        .execute()
    )
    return bool(result.get("isMember", False))

# ---------------------------------------------------------------------------
# Minimal user model (no database — identity lives in the session)
# ---------------------------------------------------------------------------

class _User(UserMixin):
    def __init__(self, email: str) -> None:
        self.id = email
        self.email = email


# ---------------------------------------------------------------------------
# HTML templates (inline — no extra template directory needed)
# ---------------------------------------------------------------------------

_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Flow PMO — Entrar</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f1117;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .card {
      background: #1a1d27;
      border: 1px solid #2d3148;
      border-radius: 12px;
      padding: 48px 40px;
      text-align: center;
      width: 100%;
      max-width: 380px;
    }
    .logo { font-size: 2rem; font-weight: 700; color: #e2e8f0; margin-bottom: 4px; }
    .subtitle { color: #64748b; font-size: 0.9rem; margin-bottom: 36px; }
    .btn-google {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      background: #fff;
      color: #3c4043;
      border: none;
      border-radius: 8px;
      padding: 12px 24px;
      font-size: 0.95rem;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      width: 100%;
      justify-content: center;
      transition: box-shadow 0.15s;
    }
    .btn-google:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
    .google-icon { width: 20px; height: 20px; }
    {% if error %}
    .error-msg {
      margin-top: 20px;
      color: #f87171;
      font-size: 0.85rem;
      background: rgba(248,113,113,0.1);
      border-radius: 6px;
      padding: 10px 14px;
    }
    {% endif %}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">Flow PMO</div>
    <div class="subtitle">Acesso restrito — conta {{ domain }}</div>
    {% if google_url %}
    <a href="{{ google_url }}" class="btn-google">
      <svg class="google-icon" viewBox="0 0 48 48">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        <path fill="none" d="M0 0h48v48H0z"/>
      </svg>
      Entrar com Google Workspace
    </a>
    {% endif %}
    {% if error %}
    <div class="error-msg">{{ error }}</div>
    {% endif %}
  </div>
</body>
</html>"""

_FORBIDDEN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Acesso negado — Flow PMO</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f1117; color: #e2e8f0;
      display: flex; align-items: center; justify-content: center; min-height: 100vh;
    }
    .card {
      background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px;
      padding: 48px 40px; text-align: center; max-width: 420px;
    }
    h1 { font-size: 1.4rem; margin-bottom: 12px; color: #f87171; }
    p { color: #94a3b8; font-size: 0.9rem; line-height: 1.6; }
    .email { color: #e2e8f0; font-weight: 600; }
    .domain { color: #60a5fa; }
    a { display: inline-block; margin-top: 24px; color: #60a5fa; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Acesso negado</h1>
    <p>A conta <span class="email">{{ email }}</span> não tem permissão para acessar este dashboard.</p>
    {% if reason == "domain" %}
    <p style="margin-top:8px">
      É necessário usar uma conta do domínio <span class="domain">{{ domain }}</span>.
    </p>
    {% elif reason == "config" %}
    <p style="margin-top:8px">
      O controle de acesso do dashboard está temporariamente indisponível. Entre em contato com o administrador.
    </p>
    {% else %}
    <p style="margin-top:8px">Entre em contato com o administrador para solicitar acesso.</p>
    {% endif %}
    <a href="{{ logout_url }}">Sair e tentar com outra conta</a>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_app(flask_server) -> None:
    """Attach Google Workspace OAuth + Flask-Login to an existing Flask app."""

    # --- Secret key (required for signed sessions) -------------------------
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "FLASK_SECRET_KEY não definida. "
            "Defina uma string aleatória longa nessa variável de ambiente."
        )
    flask_server.secret_key = secret_key

    # --- Google Workspace domain -------------------------------------------
    allowed_domain = os.environ.get("FLOW_PMO_ALLOWED_DOMAIN", "").strip().lower()
    if not allowed_domain:
        raise RuntimeError(
            "FLOW_PMO_ALLOWED_DOMAIN não definida. "
            "Defina o domínio Google Workspace (ex: empresa.com)."
        )
    logger = flask_server.logger

    # --- Static email allowlist (fallback when group check is unavailable) -
    raw_emails = os.environ.get("FLOW_PMO_ALLOWED_EMAILS", "")
    allowed_emails: set[str] = {
        e.strip().lower() for e in raw_emails.split(",") if e.strip()
    }

    # --- Google Workspace Group membership check ---------------------------
    allowed_group = os.environ.get("FLOW_PMO_ALLOWED_GROUP", "").strip().lower()
    raw_sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    impersonate = os.environ.get("GOOGLE_IMPERSONATE_EMAIL", "").strip()

    sa_info: dict | None = None
    sa_json_error: str | None = None
    if raw_sa_json:
        try:
            sa_info = _load_service_account_info(raw_sa_json)
        except ValueError as exc:
            sa_json_error = str(exc)

    use_group_check = bool(allowed_group and sa_info and impersonate)
    has_group_signal = bool(allowed_group or raw_sa_json or impersonate)
    access_mode = "deny"
    login_error = None

    if use_group_check:
        access_mode = "group"
        logger.info(
            "Google auth access control ativo em modo grupo (%s).", allowed_group
        )
    elif allowed_emails:
        access_mode = "allowlist"
        logger.info(
            "Google auth access control ativo em modo allowlist estática (%d e-mails).",
            len(allowed_emails),
        )
    else:
        login_error = (
            "Controle de acesso não configurado. Defina uma allowlist de e-mails "
            "ou configure o grupo do Google Workspace com service account."
        )
        logger.error(login_error)

    if has_group_signal and not use_group_check:
        missing_parts: list[str] = []
        if not allowed_group:
            missing_parts.append("FLOW_PMO_ALLOWED_GROUP")
        if not raw_sa_json:
            missing_parts.append("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not impersonate:
            missing_parts.append("GOOGLE_IMPERSONATE_EMAIL")
        if sa_json_error:
            missing_parts.append("GOOGLE_SERVICE_ACCOUNT_JSON válido")

        logger.warning(
            "Checagem por grupo Google Workspace não foi ativada. Fallback atual: %s. "
            "Pendências: %s%s",
            access_mode,
            ", ".join(missing_parts) or "nenhuma",
            f" | detalhe: {sa_json_error}" if sa_json_error else "",
        )
        if access_mode == "deny":
            login_error = (
                "A checagem por grupo do Google Workspace está incompleta. "
                "Revise as variáveis de ambiente do grupo, da service account "
                "e do e-mail de impersonação."
            )

    # --- Flask-Login -------------------------------------------------------
    login_manager = LoginManager()
    login_manager.init_app(flask_server)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def _load_user(user_id: str):
        return _User(user_id)

    # --- Authlib / Google OAuth --------------------------------------------
    oauth = OAuth(flask_server)
    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # --- Blueprint ---------------------------------------------------------
    auth_bp = Blueprint("auth", __name__)

    @auth_bp.route("/login")
    def login():
        error = session.pop("auth_error", None) or login_error
        google_url = None if access_mode == "deny" else url_for("auth.google_authorize")
        return render_template_string(
            _LOGIN_HTML, google_url=google_url, error=error, domain=allowed_domain
        )

    @auth_bp.route("/auth/google")
    def google_authorize():
        redirect_uri = url_for("auth.google_callback", _external=True)
        # hd hint: pre-selects the Workspace account picker on Google's side
        return oauth.google.authorize_redirect(redirect_uri, hd=allowed_domain)

    @auth_bp.route("/callback")
    def google_callback():
        try:
            token = oauth.google.authorize_access_token()
            userinfo = token.get("userinfo") or oauth.google.userinfo()
        except Exception:
            session["auth_error"] = "Falha na autenticação com Google. Tente novamente."
            return redirect(url_for("auth.login"))

        email: str = (userinfo.get("email") or "").lower()
        # hd claim is set by Google for Workspace accounts; absent for @gmail.com
        token_hd: str = (userinfo.get("hd") or "").lower()

        # Reject personal Gmail accounts (no hd claim) — must be a Workspace account
        if not token_hd:
            logout_user()
            return render_template_string(
                _FORBIDDEN_HTML,
                email=email,
                domain=allowed_domain,
                reason="domain",
                logout_url=url_for("auth.logout"),
            ), 403

        if access_mode == "deny":
            logout_user()
            return render_template_string(
                _FORBIDDEN_HTML,
                email=email,
                domain=allowed_domain,
                reason="config",
                logout_url=url_for("auth.logout"),
            ), 403

        # Static allowlist (active when group check vars are not configured)
        if access_mode == "allowlist" and email not in allowed_emails:
            logger.info("Acesso negado por allowlist estática para %s.", email)
            logout_user()
            return render_template_string(
                _FORBIDDEN_HTML,
                email=email,
                domain=allowed_domain,
                reason="allowlist",
                logout_url=url_for("auth.logout"),
            ), 403

        # Google Workspace Group membership check (takes priority over allowlist)
        if use_group_check:
            try:
                member = _is_group_member(email, allowed_group, sa_info, impersonate)
            except Exception:
                logger.exception(
                    "Falha ao verificar o grupo %s para o usuário %s.",
                    allowed_group,
                    email,
                )
                session["auth_error"] = "Erro ao verificar permissão de acesso. Tente novamente."
                return redirect(url_for("auth.login"))

            if not member:
                logger.info(
                    "Acesso negado por grupo Google Workspace. Usuário=%s Grupo=%s.",
                    email,
                    allowed_group,
                )
                logout_user()
                return render_template_string(
                    _FORBIDDEN_HTML,
                    email=email,
                    domain=allowed_domain,
                    reason="allowlist",
                    logout_url=url_for("auth.logout"),
                ), 403

        login_user(_User(email), remember=True)
        return redirect("/")

    @auth_bp.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("auth.login"))

    flask_server.register_blueprint(auth_bp)

    # --- Protect all non-auth routes ---------------------------------------
    _PUBLIC_PREFIXES = ("/login", "/auth/google", "/callback", "/logout", "/_dash-", "/favicon")

    @flask_server.before_request
    def _require_login():
        from flask import request
        path = request.path
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
