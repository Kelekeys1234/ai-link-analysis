import json
import logging

from fastapi import HTTPException
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.config import Settings
from app.schemas import Analysis, Brand, LLMAnalysisResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You analyze public business websites. Ground claims in supplied page content. Never pretend competitor facts were researched: competitor candidates are AI-generated suggestions, confidence='suggested', and evidence must say category-level suggestion when not verified. Do not invent traffic, rankings, search volume, testimonials, or locations. Use 'unknown' where not established. Mark each service source 'observed' or 'inferred'. Return JSON only. Produce exactly five search-query objects and five service objects; inferred services must be labeled."""


class GeminiModelRequestError(Exception):
    """Provider failure annotated with the model that was actually attempted."""

    def __init__(self, model_name: str, provider_error: Exception):
        super().__init__(str(provider_error))
        self.model_name = model_name
        self.provider_error = provider_error


async def _generate_with_fallback(client, prompt: str, primary_model: str, fallback_models: tuple[str, ...]):
    models = list(dict.fromkeys([primary_model, *fallback_models]))

    for index, model_name in enumerate(models):
        try:
            return await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=LLMAnalysisResult,
                ),
            )
        except Exception as exc:
            error_text = str(exc).upper()
            is_service_unavailable = (
                getattr(exc, "code", None) == 503
                or getattr(exc, "status_code", None) == 503
                or "503 UNAVAILABLE" in error_text
            )
            is_model_unavailable = (
                getattr(exc, "code", None) == 404
                or getattr(exc, "status_code", None) == 404
                or "404 NOT_FOUND" in error_text
            )
            is_quota_exhausted = (
                getattr(exc, "code", None) == 429
                or getattr(exc, "status_code", None) == 429
                or "429 RESOURCE_EXHAUSTED" in error_text
            )
            if (is_service_unavailable or is_model_unavailable or is_quota_exhausted) and index + 1 < len(models):
                failure_type = (
                    "503 UNAVAILABLE" if is_service_unavailable
                    else "404 NOT_FOUND" if is_model_unavailable
                    else "429 RESOURCE_EXHAUSTED"
                )
                logger.warning(
                    "Gemini model %s is unavailable (%s); trying fallback %s",
                    model_name,
                    failure_type,
                    models[index + 1],
                )
                continue
            raise GeminiModelRequestError(model_name, exc) from exc


def _safe_error_message(exc: Exception, api_key: str) -> str:
    """Return concise provider diagnostics without echoing the configured secret."""
    message = " ".join(str(exc).split()) or "No provider error message was supplied"
    message = message.replace(api_key, "[REDACTED]")
    return message[:400]


async def analyze_content(page: dict[str, str], settings: Settings) -> tuple[Brand, Analysis]:
    api_key = settings.gemini_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="LLM is not configured. Set GEMINI_API_KEY.")
    api_key = api_key.strip()
    if not api_key or api_key in {
        "your-google-ai-studio-api-key",
        "replace-with-your-google-ai-studio-key",
    }:
        raise HTTPException(status_code=503, detail="Set a valid GEMINI_API_KEY in your local .env file.")
    prompt = (
        "Analyze this website and return top-level brand (name, category, summary) and analysis "
        "(competitor_analysis, target_search_queries, seo_improvements, top_services, target_audience). "
        "Allowed platforms: Google, Facebook, Instagram, LinkedIn, X.\n"
        + json.dumps(page, ensure_ascii=False)
    )
    try:
        if settings.enable_llm_breakpoint:
            breakpoint()
        client = genai.Client(api_key=api_key)
        result = await _generate_with_fallback(
            client,
            prompt,
            settings.gemini_model,
            settings.gemini_fallback_models,
        )
        data = json.loads(result.text or "{}")
        parsed = LLMAnalysisResult.model_validate(data)
        brand = parsed.brand
        analysis = parsed.analysis
        if len(analysis.target_search_queries) != 5 or len(analysis.top_services) != 5:
            raise ValueError("The model returned an unexpected number of items")
        return brand, analysis
    except (ValidationError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.exception("Gemini returned an invalid analysis structure")
        raise HTTPException(status_code=502, detail="LLM returned an invalid analysis structure") from exc
    except Exception as exc:
        failed_model = exc.model_name if isinstance(exc, GeminiModelRequestError) else settings.gemini_model
        logger.exception("Gemini analysis request failed (model=%s)", failed_model)
        detail = "Gemini analysis request failed. Check the server log."
        provider_error = exc.provider_error if isinstance(exc, GeminiModelRequestError) else exc
        is_service_unavailable = (
            getattr(provider_error, "code", None) == 503
            or getattr(provider_error, "status_code", None) == 503
            or "503 UNAVAILABLE" in str(provider_error).upper()
        )
        is_quota_or_rate_limit = (
            getattr(provider_error, "code", None) == 429
            or getattr(provider_error, "status_code", None) == 429
            or "429 RESOURCE_EXHAUSTED" in str(provider_error).upper()
        )
        status_code = 429 if is_quota_or_rate_limit else 503 if is_service_unavailable else 502
        if is_quota_or_rate_limit:
            detail = "Gemini quota or rate limit reached. Check the model quota/billing, or retry after the reset time."
        elif is_service_unavailable:
            detail = "Gemini is temporarily unavailable on the configured models. Retry later."
        if settings.debug_errors:
            detail = (
                f"Gemini analysis failed on {failed_model} "
                f"({provider_error.__class__.__name__}): {_safe_error_message(provider_error, api_key)}"
            )
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc
