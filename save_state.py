import json
import os
import time
from datetime import date, datetime
from typing import Any, Dict

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

STATE_DIR = os.path.join(os.path.dirname(__file__), "generated_reports")

def get_state_file() -> str:
    # Intenta obtener o establecer un UUID único en los parámetros de consulta del navegador (URL)
    # para que la recarga de página mantenga el mismo estado sin mezclarlo con otros dispositivos/pestañas.
    try:
        import uuid
        if hasattr(st, "query_params"):
            if "session_uuid" in st.query_params:
                session_id = st.query_params["session_uuid"]
            else:
                session_id = uuid.uuid4().hex[:12]
                st.query_params["session_uuid"] = session_id
        else:
            params = st.experimental_get_query_params()
            if "session_uuid" in params:
                session_id = params["session_uuid"][0]
            else:
                session_id = uuid.uuid4().hex[:12]
                st.experimental_set_query_params(session_uuid=session_id)
    except Exception:
        # Fallback si st.query_params o st.experimental_set_query_params no están disponibles o fallan
        ctx = get_script_run_ctx()
        session_id = ctx.session_id if ctx is not None else "default"

    return os.path.join(STATE_DIR, f"saved_session_state_{session_id}.json")

def _cleanup_old_states() -> None:
    """Removes session state files older than 24 hours."""
    try:
        if not os.path.exists(STATE_DIR):
            return
        now = time.time()
        for filename in os.listdir(STATE_DIR):
            if filename.startswith("saved_session_state_") and filename.endswith(".json"):
                filepath = os.path.join(STATE_DIR, filename)
                if os.path.isfile(filepath):
                    mtime = os.path.getmtime(filepath)
                    # 24 hours = 86400 seconds
                    if now - mtime > 86400:
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
    except Exception:
        pass

_RESTORE_FLAG = "_saved_state_restored"

_EXACT_ALLOWED = {
    "datos_proyecto",
    "norma_global",
}

_ALLOWED_PREFIXES = (
    "bloque_",
    "procedimiento_",
    "materiales_",
    "procesos_",
    "tipos_",
    "tabla_",
    "estandares_",
    "parametros_",
    "resultados_",
    "tipo_metodo_",
    "proceso_corriente_",
    "palpador_",
    "frecuencias_",
    "elementos_",
    "modulo_",
    "detalle_",
    "observaciones_",
)

_BLOCKED_PREFIXES = (
    "_",
    "imagenes",
    "esquema_",
    "delete_idx",
)

_BLOCKED_EXACT = {
    "pages_config",
    "esquema_elementos_global",
}


def _is_upload_like(value: Any) -> bool:
    return hasattr(value, "read") and hasattr(value, "name")


def _serialize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, date) and not isinstance(value, datetime):
        return {"__type__": "date", "value": value.isoformat()}

    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}

    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if key == "archivo":
                # Uploaded files cannot be restored after reload.
                continue
            serialized = _serialize(item)
            if serialized is not None:
                out[key] = serialized
        return out

    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            serialized = _serialize(item)
            if serialized is not None:
                items.append(serialized)
        return items

    if _is_upload_like(value):
        return None

    return str(value)


def _deserialize(value: Any) -> Any:
    if isinstance(value, dict):
        t = value.get("__type__")
        if t == "date":
            try:
                return date.fromisoformat(value["value"])
            except Exception:
                return value.get("value")
        if t == "datetime":
            try:
                return datetime.fromisoformat(value["value"])
            except Exception:
                return value.get("value")
        return {k: _deserialize(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_deserialize(v) for v in value]

    return value


def _should_persist_key(key: str) -> bool:
    if key in _BLOCKED_EXACT:
        return False

    for prefix in _BLOCKED_PREFIXES:
        if key.startswith(prefix):
            return False

    if key in _EXACT_ALLOWED:
        return True

    for prefix in _ALLOWED_PREFIXES:
        if key.startswith(prefix):
            return True

    return False


def persist_session_state() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    _cleanup_old_states()

    state = {}
    for key, value in st.session_state.items():
        if not _should_persist_key(key):
            continue
        serialized = _serialize(value)
        if serialized is not None:
            state[key] = serialized

    payload = {
        "saved_at": datetime.now().isoformat(),
        "state": state,
    }

    state_file = get_state_file()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def restore_session_state() -> bool:
    if st.session_state.get(_RESTORE_FLAG):
        return False

    st.session_state[_RESTORE_FLAG] = True

    state_file = get_state_file()
    if not os.path.exists(state_file):
        return False

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    state = payload.get("state", {}) if isinstance(payload, dict) else {}
    if not isinstance(state, dict):
        return False

    for key, value in state.items():
        if key not in st.session_state:
            st.session_state[key] = _deserialize(value)

    return True


def get_saved_at() -> str:
    state_file = get_state_file()
    if not os.path.exists(state_file):
        return ""

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""

    if isinstance(payload, dict):
        return str(payload.get("saved_at", ""))
    return ""


def clear_persisted_state() -> None:
    """Clears persisted form state from disk and current session."""
    state_file = get_state_file()
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
        except OSError:
            pass

    for key in list(st.session_state.keys()):
        if _should_persist_key(key):
            del st.session_state[key]
