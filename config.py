"""Typed configuration helpers without exposing credentials in the UI."""

import os
from dotenv import load_dotenv

load_dotenv()


def api_key_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"


def ai_mode() -> str:
    mode = os.getenv("BIZPILOT_AI_MODE", "openai").strip().lower()
    if mode not in ("openai", "gemini", "offline"):
        raise ValueError("BIZPILOT_AI_MODE must be 'openai', 'gemini', or 'offline'.")
    return mode


def gemini_key_available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def gemini_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() or "gemini-3.1-flash-lite"


def deployment_mode() -> str:
    """Return the explicit runtime boundary.

    ``demo`` may initialize fictional data. ``pilot`` requires a prepared
    database and an authenticated, allowlisted owner.
    """
    mode = os.getenv("BIZPILOT_DEPLOYMENT_MODE", "demo").strip().lower()
    if mode not in ("demo", "pilot"):
        raise ValueError("BIZPILOT_DEPLOYMENT_MODE must be 'demo' or 'pilot'.")
    return mode


def data_mode() -> str:
    mode = os.getenv("BIZPILOT_DATA_MODE", "synthetic").strip().lower()
    if mode not in ("synthetic", "external"):
        raise ValueError("BIZPILOT_DATA_MODE must be 'synthetic' or 'external'.")
    if deployment_mode() == "pilot" and mode != "synthetic":
        raise ValueError("The current pilot supports synthetic data only.")
    return mode


def data_source_label() -> str:
    default = "Fictional BizPilot demo dataset"
    return os.getenv("BIZPILOT_DATA_SOURCE_LABEL", default).strip() or default


def dataset_version() -> str:
    return os.getenv("BIZPILOT_DATASET_VERSION", "fictional-v1").strip() or "fictional-v1"


def max_result_rows() -> int:
    raw = os.getenv("BIZPILOT_MAX_RESULT_ROWS", "50").strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("BIZPILOT_MAX_RESULT_ROWS must be an integer.") from error
    if not 1 <= value <= 200:
        raise ValueError("BIZPILOT_MAX_RESULT_ROWS must be between 1 and 200.")
    return value


def owner_subject_allowlist() -> set[tuple[str, str]]:
    """Parse ``issuer|subject`` pairs separated by semicolons."""
    entries: set[tuple[str, str]] = set()
    raw = os.getenv("BIZPILOT_OWNER_SUBJECTS", "")
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        issuer, separator, subject = item.rpartition("|")
        if not separator or not issuer.strip() or not subject.strip():
            raise ValueError(
                "BIZPILOT_OWNER_SUBJECTS entries must use 'issuer|subject', separated by semicolons."
            )
        entries.add((issuer.strip(), subject.strip()))
    if deployment_mode() == "pilot" and len(entries) > 2:
        raise ValueError("The restricted pilot permits at most two owner identities.")
    return entries


def session_hours() -> int:
    raw = os.getenv("BIZPILOT_SESSION_HOURS", "8").strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("BIZPILOT_SESSION_HOURS must be an integer.") from error
    if not 1 <= value <= 12:
        raise ValueError("BIZPILOT_SESSION_HOURS must be between 1 and 12.")
    return value


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def max_message_chars() -> int:
    return _bounded_int("BIZPILOT_MAX_MESSAGE_CHARS", 2000, 100, 10000)


def max_history_chars() -> int:
    return _bounded_int("BIZPILOT_MAX_HISTORY_CHARS", 12000, 1000, 50000)


def max_tool_result_chars() -> int:
    return _bounded_int("BIZPILOT_MAX_TOOL_RESULT_CHARS", 12000, 1000, 50000)


def max_model_calls() -> int:
    return _bounded_int("BIZPILOT_MAX_MODEL_CALLS", 4, 1, 8)


def max_tool_calls() -> int:
    return _bounded_int("BIZPILOT_MAX_TOOL_CALLS", 6, 1, 12)


def max_output_tokens() -> int:
    return _bounded_int("BIZPILOT_MAX_OUTPUT_TOKENS", 600, 100, 2000)


def run_deadline_seconds() -> int:
    return _bounded_int("BIZPILOT_RUN_DEADLINE_SECONDS", 30, 5, 120)


def daily_budget_usd_micros() -> int:
    raw = os.getenv("BIZPILOT_DAILY_BUDGET_USD", "2.00").strip()
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError("BIZPILOT_DAILY_BUDGET_USD must be numeric.") from error
    if not 0.01 <= value <= 100:
        raise ValueError("BIZPILOT_DAILY_BUDGET_USD must be between 0.01 and 100.")
    return round(value * 1_000_000)


def max_active_runs_per_owner() -> int:
    return 1


def max_active_runs_global() -> int:
    return 2
