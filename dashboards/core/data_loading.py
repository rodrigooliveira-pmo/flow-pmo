import os
import json
import hashlib
import urllib.request
import urllib.parse
import posixpath
import re
from datetime import datetime, timedelta
from pathlib import Path

from shared.env_utils import load_env_file, parse_json_env
from shared.path_utils import candidate_data_folders, _sanitize_os_path
from shared.text_utils import normalize_text


def _get_cache_dir() -> str:
    """Returns the cache directory, configurable via FLOW_PMO_CACHE_DIR."""
    return os.getenv('FLOW_PMO_CACHE_DIR', '/tmp/flow-pmo-models')


def download_cached(url: str, prefix: str, ext: str, extra_key: str = '') -> str:
    """Download URL to a TTL-cached local file. Returns local file path.

    Args:
        url: Remote URL to download.
        prefix: Filename prefix (e.g. 'PowerBI_Model', 'portfolio-bt-ns').
        ext: File extension including dot (e.g. '.xlsx', '.csv').
        extra_key: Optional extra key for disambiguation (e.g. project_key).
    """
    cache_dir = _get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    safe_extra = (
        ''.join(ch for ch in str(extra_key).lower() if ch.isalnum() or ch in {'_', '-'})
        if extra_key else ''
    )
    name = '-'.join(p for p in [prefix, safe_extra, url_hash] if p) + ext
    out_file = os.path.join(cache_dir, name)
    _refresh_remote_cache_file(url, out_file)
    return out_file


def _download_model_from_url(url):
    print(f"[data_loading] Downloading model from URL: {url}", flush=True)
    return download_cached(url, 'PowerBI_Model', '.xlsx')


def _download_portfolio_csv_from_url(url):
    return download_cached(url, 'portfolio-bt-ns', '.csv')


def _download_four_ps_kanban_csv_from_url(url):
    return download_cached(url, 'four-ps-kanban', '.csv')


def _download_bottleneck_csv_from_url(url, project_key):
    return download_cached(url, 'bottleneck', '.csv', extra_key=project_key or 'project')


def _download_process_mining_report_from_url(url):
    return download_cached(url, 'process-mining', '.xlsx')


def _download_downstream_items_csv_from_url(url, project_key):
    return download_cached(url, 'downstream', '.csv', extra_key=project_key or 'project')


def _download_capex_csv_from_url(url, key):
    return download_cached(url, 'capex', '.csv', extra_key=key or 'capex')


def _download_gmud_csv_from_url(url, kind):
    return download_cached(url, 'gmud', '.csv', extra_key=kind or 'gmud')


def _remote_cache_ttl_seconds():
    raw = os.getenv('FLOW_PMO_REMOTE_CACHE_TTL_SECONDS', '').strip()
    if not raw:
        return 300
    try:
        return max(0, int(raw))
    except Exception:
        return 300


def _refresh_remote_cache_file(url, out_file):
    """Download URL into cache file with TTL-based refresh for stable *latest* URLs."""
    ttl = _remote_cache_ttl_seconds()
    if os.path.exists(out_file):
        age_seconds = max(0.0, (datetime.now() - datetime.fromtimestamp(os.path.getmtime(out_file))).total_seconds())
        if age_seconds <= float(ttl):
            return out_file
    tmp_file = f"{out_file}.tmp"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(tmp_file, 'wb') as f:
        f.write(response.read())
    os.replace(tmp_file, out_file)
    return out_file


def _load_bottleneck_url_map():
    raw = os.getenv('FLOW_PMO_BOTTLENECK_CSV_URL_MAP', '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out = {}
    for key, value in parsed.items():
        project_key = str(key).strip().upper()
        url = str(value).strip()
        if project_key and url:
            out[project_key] = url
    return out


def _load_bitbucket_csv_url_map():
    """Carrega mapa de URLs para CSVs do Bitbucket.
    Formato: {"w1nner_commits": "https://...", "w1nner_pullrequests": "https://...", ...}
    A chave é {prefix}_{tipo} (sem .csv). Ex: w1nner_commits, s1nc_pullrequests, befinance_commits.
    """
    raw = os.getenv('FLOW_PMO_BITBUCKET_CSV_URL_MAP', '').strip()
    if not raw:
        return {}
    cleaned = ' '.join(raw.splitlines())
    parsed = None
    for candidate in (cleaned, cleaned.strip('"').strip("'"), cleaned.replace('\\"', '"')):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            break
        except Exception:
            continue
    if parsed is None:
        matches = re.findall(r'"([a-z0-9_]+)"\s*:\s*"([^"]+)"', cleaned)
        if matches:
            parsed = {k: v for k, v in matches}
        else:
            return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k).strip().lower(): str(v).strip() for k, v in parsed.items() if k and v}


def _download_bitbucket_csv_from_url(url, key):
    return download_cached(url, 'bb', '.csv', extra_key=key or 'bb')


def _load_downstream_url_map():
    raw = os.getenv('FLOW_PMO_DOWNSTREAM_CSV_URL_MAP', '').strip()
    if not raw:
        return {}
    parsed = None
    for candidate in (
        raw,
        raw.strip('"').strip("'"),
        raw.replace('\\"', '"'),
    ):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            break
        except Exception:
            continue
    if parsed is None:
        # Fallback tolerante para env malformada:
        # ex.: FLOW_PMO_DOWNSTREAM_CSV_URL_MAP="{"W1NNER":"https://..."}"
        matches = re.findall(r'"?([A-Za-z0-9& _-]+)"?\s*:\s*"([^"]+)"', raw)
        if matches:
            parsed = {k: v for k, v in matches}
        else:
            return {}
    if not isinstance(parsed, dict):
        return {}
    out = {}
    for key, value in parsed.items():
        project_key = str(key).strip().upper()
        url = str(value).strip()
        if project_key and url:
            out[project_key] = url
    return out


def _url_filename_matches_project_suffix(url, expected_prefix, suffix):
    """Validate if URL filename seems to belong to the expected project prefix/suffix."""
    if not url or not expected_prefix:
        return False
    parsed = urllib.parse.urlparse(str(url).strip())
    filename = os.path.basename(parsed.path or '').lower()
    prefix = str(expected_prefix).strip().lower()
    return filename.startswith(prefix) and filename.endswith(str(suffix or '').lower())


def _url_filename_matches_project(url, expected_prefix):
    """Backward-compatible helper for bottleneck URLs."""
    return _url_filename_matches_project_suffix(url, expected_prefix, '-data_bottlenecks.csv')


def _resolve_model_file(data_folders):
    explicit_model = _sanitize_os_path(os.getenv('FLOW_PMO_MODEL_FILE', ''))
    if explicit_model:
        candidate = explicit_model if os.path.isabs(explicit_model) else os.path.join(os.path.dirname(__file__), explicit_model)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise FileNotFoundError(f'FLOW_PMO_MODEL_FILE aponta para arquivo inexistente: {candidate}')

    model_url = os.getenv('FLOW_PMO_MODEL_URL', '').strip()
    if model_url:
        try:
            return _download_model_from_url(model_url)
        except Exception as _url_exc:
            import warnings
            warnings.warn(
                f"[data_loading] Falha ao baixar modelo de FLOW_PMO_MODEL_URL ({_url_exc}). "
                "Tentando arquivo local como fallback.",
                RuntimeWarning,
                stacklevel=2,
            )

    model_files = []
    for folder in data_folders:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            if name.startswith('PowerBI_Model_') and name.endswith('.xlsx'):
                model_files.append(os.path.join(folder, name))
    if model_files:
        return max(model_files, key=os.path.getctime)

    raise FileNotFoundError(
        'Arquivo de modelo não encontrado. Configure FLOW_PMO_MODEL_FILE ou FLOW_PMO_MODEL_URL, '
        'ou adicione PowerBI_Model_*.xlsx em uma destas pastas: '
        + ', '.join(data_folders or ['(nenhuma pasta encontrada)'])
    )


DATA_FOLDERS = candidate_data_folders()
DATA_FOLDER = DATA_FOLDERS[0] if DATA_FOLDERS else os.path.dirname(__file__)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_MODULE_DIR))
PROCESS_MINING_ARTIFACT_FOLDER = os.path.join(_PROJECT_ROOT, 'artifacts', 'process_mining')
try:
    MODEL_FILE = _resolve_model_file(DATA_FOLDERS)
except Exception as _model_file_exc:
    import warnings
    warnings.warn(
        f"[data_loading] Não foi possível resolver MODEL_FILE no import: {_model_file_exc}. "
        "O modelo será carregado sob demanda na primeira requisição.",
        RuntimeWarning,
        stacklevel=1,
    )
    MODEL_FILE = None


def _iter_local_data_folders(include_process_mining_artifacts=False):
    folders = []
    seen = set()
    candidates = list(DATA_FOLDERS or [])
    if include_process_mining_artifacts:
        candidates.append(PROCESS_MINING_ARTIFACT_FOLDER)
    for raw_folder in candidates:
        folder = str(raw_folder or '').strip()
        if not folder:
            continue
        folder = os.path.abspath(folder)
        if folder in seen or not os.path.isdir(folder):
            continue
        seen.add(folder)
        folders.append(folder)
    return folders


def _format_last_processed_load(model_file):
    """Best-effort label for the processed data load timestamp."""
    try:
        filename = os.path.basename(model_file or '')
        match = re.match(r'^PowerBI_Model_(\d{8})_(\d{6})\.xlsx$', filename)
        if match:
            return datetime.strptime(''.join(match.groups()), '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M')
        return datetime.fromtimestamp(os.path.getmtime(model_file)).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return 'indisponível'


LAST_PROCESSED_LOAD_LABEL = _format_last_processed_load(MODEL_FILE)