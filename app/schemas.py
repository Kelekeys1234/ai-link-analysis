from pydantic import AnyHttpUrl, BaseModel, Field


class AnalysisRequest(BaseModel):
    url: AnyHttpUrl


class Competitor(BaseModel):
    name: str
    overview: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses_or_gaps: list[str] = Field(default_factory=list)
    evidence: str
    confidence: str = "suggested"


class SearchQuery(BaseModel):
    query: str
    platforms: list[str]
    intent: str
    business_relevance: str
    target_audience: str


class SeoImprovements(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str]
    long_tail_keywords: list[str]
    recommended_title: str
    title_primary_keyword: str
    meta_description: str
    supporting_content: list[str]


class Service(BaseModel):
    name: str
    description: str
    target_industry: str
    target_customer: str
    main_benefit: str
    source: str


class AudienceSegment(BaseModel):
    segment: str
    business_type: str
    requirement: str
    needs_and_challenges: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class CompetitorAnalysis(BaseModel):
    brand_overview: str
    business_category: str
    main_products_and_services: list[str]
    competitors: list[Competitor]
    competitive_advantages: list[str]
    opportunities: list[str]


class TargetAudience(BaseModel):
    primary_audience: list[AudienceSegment]
    secondary_audience: list[AudienceSegment]
    industries: list[str]
    business_types: list[str]
    customer_profiles: list[str]
    geography: str
    customer_needs: list[str]
    marketing_segments: list[str]


class Analysis(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery]
    seo_improvements: SeoImprovements
    top_services: list[Service]
    target_audience: TargetAudience


class Brand(BaseModel):
    name: str
    category: str
    summary: str


class LinkAnalysisResponse(BaseModel):
    success: bool = True
    website: str
    brand: Brand
    analysis: Analysis
    limitations: list[str] = Field(default_factory=list)


class LLMAnalysisResult(BaseModel):
    brand: Brand
    analysis: Analysis
