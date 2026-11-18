import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.schemas import AnalysisRequest, LinkAnalysisResponse
from app.services.analysis_service import analyze_website

logger = logging.getLogger("uvicorn.error")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Gemini model chain loaded: primary=%s, fallbacks=%s",
        settings.gemini_model,
        ",".join(settings.gemini_fallback_models) or "none",
    )
    yield


app = FastAPI(title="AI Website Link Analysis API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/link-analysis", response_model=LinkAnalysisResponse)
async def link_analysis(request: AnalysisRequest) -> LinkAnalysisResponse:
    return await analyze_website(str(request.url), settings)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "detail": jsonable_encoder(exc.errors())})
