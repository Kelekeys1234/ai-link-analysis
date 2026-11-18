"""Coordinates website extraction, LLM analysis, and response assembly."""

from app.config import Settings
from app.schemas import LinkAnalysisResponse
from app.services.competitor_service import label_competitors_as_suggestions
from app.services.llm_service import analyze_content
from app.services.website_extractor import extract_website


async def analyze_website(url: str, settings: Settings) -> LinkAnalysisResponse:
    page = await extract_website(
        url,
        timeout=settings.request_timeout_seconds,
        max_bytes=settings.max_page_bytes,
    )
    brand, analysis = await analyze_content(page, settings)
    analysis = label_competitors_as_suggestions(analysis)

    return LinkAnalysisResponse(
        website=page["url"],
        brand=brand,
        analysis=analysis,
        limitations=[
            "Competitors are AI-generated candidates and were not independently verified.",
            "Search volumes and rankings are not reported because no keyword data provider is connected.",
        ],
    )
