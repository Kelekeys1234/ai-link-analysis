"""Ensure competitor output is clearly represented as unverified AI suggestions."""

from app.schemas import Analysis


UNVERIFIED_COMPETITOR_EVIDENCE = (
    "AI-generated candidate based on the submitted website's category; "
    "not independently researched or verified."
)


def label_competitors_as_suggestions(analysis: Analysis) -> Analysis:
    """Set consistent provenance labels instead of implying external research."""
    competitor_analysis = analysis.competitor_analysis.model_copy(
        update={
            "competitors": [
                competitor.model_copy(
                    update={"confidence": "suggested", "evidence": UNVERIFIED_COMPETITOR_EVIDENCE}
                )
                for competitor in analysis.competitor_analysis.competitors
            ]
        }
    )
    return analysis.model_copy(update={"competitor_analysis": competitor_analysis})
