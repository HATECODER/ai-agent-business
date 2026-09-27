"""Local configuration without exposing credentials in the UI."""

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
