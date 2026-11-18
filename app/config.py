"""Application configuration loaded from environment variables and local .env."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv(override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str
    gemini_fallback_models: tuple[str, ...]
    enable_llm_breakpoint: bool
    debug_errors: bool
    request_timeout_seconds: float
    max_page_bytes: int


def get_settings() -> Settings:
    fallback_models = tuple(
        model.strip()
        for model in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite").split(",")
        if model.strip()
    )
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip(),
        gemini_fallback_models=fallback_models,
        enable_llm_breakpoint=_env_bool("ENABLE_LLM_BREAKPOINT"),
        debug_errors=_env_bool("DEBUG_ERRORS"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        max_page_bytes=int(os.getenv("MAX_PAGE_BYTES", "1500000")),
    )
