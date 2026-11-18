# AI Website Link Analysis API

A FastAPI service that fetches a public website, extracts its title, metadata, headings, and readable text, then asks an LLM to return typed business, competitor, SEO, service, search-query, and audience insights.

## Project structure

```text
app/
├── main.py                       # FastAPI routes and HTTP error handlers
├── config.py                     # Environment-backed application settings
├── schemas.py                    # Pydantic request and response models
├── services/
│   ├── analysis_service.py        # Orchestrates extraction and analysis
│   ├── competitor_service.py      # Labels AI competitor candidates as unverified
│   ├── llm_service.py             # Gemini request, fallback, and validation
│   └── website_extractor.py       # Fetches and parses public HTML pages
└── utils/
    └── validators.py             # URL and public-address validation
```

## Run locally

Requires Python 3.10+ and a Gemini API key. **Python 3.14 is recommended on Windows** for the current dependency set. Python 3.15 may make pip build PyYAML from source, which requires Microsoft C++ Build Tools. Create a key in [Google AI Studio](https://aistudio.google.com/app/apikey) and put it in your local `.env` file. The application reads it from `GEMINI_API_KEY`; the key is not in source code.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # Windows PowerShell: Copy-Item .env.example .env (only if .env does not exist)
# Set GEMINI_API_KEY in .env. Do not overwrite an existing .env with a key configured.
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

### Windows PowerShell setup

If Python 3.14 is not installed, install it with:

```powershell
winget install --id Python.Python.3.14 --exact --accept-source-agreements --accept-package-agreements
```

From the project directory, create a Python 3.14 virtual environment and install dependencies:

```powershell
py -3.14 -m venv .venv314
.\.venv314\Scripts\python.exe -m pip install -r .\requirements.txt
# Only run this if .env does not already exist; otherwise preserve your existing key/settings.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Put your real key in `.env`, then launch Uvicorn through that environment's Python:

```powershell
.\.venv314\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 4000
```

### Windows Command Prompt (CMD)

From the project folder, install and run with the virtual environment's Python. Copy the template only when you do not already have a `.env` file:

```cmd
if not exist .env copy .env.example .env
.venv314\Scripts\python.exe -m pip install -r requirements.txt
.venv314\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Add your Gemini API key to `.env` before starting the server. The application logs the configured primary model and fallback chain at startup. Defaults use `gemini-3.1-flash-lite` with `gemini-3.5-flash-lite` as fallback.

In your IDE, select `.venv314\Scripts\python.exe` as the project interpreter. If your virtual environment uses another name, use its Python executable instead. Do not run `python -m venv .venv314` again after it has already been created.

Open `http://localhost:4000/docs`. The health endpoint is `GET /health`.

## Request

### Live deployment

- **Base URL:** https://ai-link-analysis.fastapicloud.dev
- **API endpoint:** `POST https://ai-link-analysis.fastapicloud.dev/link-analysis`
- **API documentation:** https://ai-link-analysis.fastapicloud.dev/docs
- **Health check:** https://ai-link-analysis.fastapicloud.dev/health

### Postman

Create a `POST` request to `https://ai-link-analysis.fastapicloud.dev/link-analysis`, set the `Content-Type` header to `application/json`, and choose **Body → raw → JSON**:

```json
{
  "url": "https://www.shopify.com"
}
```

The same request from a terminal:

```bash
curl -X POST 'https://ai-link-analysis.fastapicloud.dev/link-analysis' \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://www.shopify.com"}'
```

### Local request

```bash
curl -X POST http://localhost:4000/link-analysis \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

Success returns `success`, the fetched website URL, a `brand` object, all five analysis sections, and limitations. Each service includes a `source` (`observed` or `inferred`). Competitors are marked `suggested` because this implementation does not perform independent competitor research. It never claims search volume or ranking data.

Errors return JSON such as `{"success":false,"detail":"..."}` with a suitable 4xx/5xx code. Missing LLM credentials return 503; Gemini quota/rate exhaustion returns 429; failed fetches, timeouts, non-HTML pages, and malformed model output are handled explicitly.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | unset | Required API credential; keep in environment or secret manager |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Stable primary model |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.5-flash-lite` | Fallback model used when the primary returns 503 UNAVAILABLE, 404 NOT_FOUND, or 429 RESOURCE_EXHAUSTED |
| `ENABLE_LLM_BREAKPOINT` | `false` | Set to `true` for a local Python debugger stop immediately before the Gemini call |
| `DEBUG_ERRORS` | `false` | Set to `true` locally to include a redacted Gemini error summary in 502 responses |
| `REQUEST_TIMEOUT_SECONDS` | `15` | Website fetch timeout |
| `MAX_PAGE_BYTES` | `1500000` | Maximum downloaded HTML size |

The Gemini call requests JSON Schema structured output, then validates brand and analysis against Pydantic models. The page text is capped before it enters the prompt. The primary is Gemini 3.1 Flash-Lite, with Gemini 3.5 Flash-Lite as fallback for 503 UNAVAILABLE, 404 NOT_FOUND, or 429 RESOURCE_EXHAUSTED errors. Google lists both as stable models. This means they are generally available model releases, not a promise against temporary outages or exhausted project quotas. Uvicorn logs the effective model chain on startup. For local runs, `.env` values override inherited shell variables; deployments should omit `.env` and set environment values through their host's secret configuration.

For local debugging, set `ENABLE_LLM_BREAKPOINT=true` in `.env`, start the server under your IDE's debugger, and submit a request. The breakpoint stops immediately before Gemini is called. If launching from a terminal instead of an IDE debugger, Python will pause in `pdb` in that terminal. Set the value back to `false` after debugging; do not enable this on a deployed server.

To inspect provider errors in the API response while debugging, set `DEBUG_ERRORS=true` and restart the server. The error summary redacts the configured API key; full exception details remain in the server log. Turn this setting off before deployment.

## Safety and scope

- Only HTTP(S) URLs are accepted. Hostnames are resolved and every resolved address must be public. Redirects are followed manually and revalidated; redirects to local/private addresses are rejected.
- Redirect count, page size, and request timeout are bounded. Scripts, styles, navigation, and footer content are excluded before extraction.
- Deploy behind infrastructure that blocks private, loopback, link-local, and cloud metadata egress too. DNS validation followed by a separate HTTP connection can still be vulnerable to DNS rebinding; production hardening should pin the validated destination IP at connection time or enforce an outbound network policy.
- This single-page extractor will not execute JavaScript or crawl linked pages. Some sites may block automated requests or expose little meaningful content.
- Competitors are suggestions inferred by the model, not researched/verified competitors. Search queries are recommendations, with no volume or rank claims.

## LLM selection research (18 November 2026)

Prices below are provider list prices per million tokens, USD, standard API use. They can change; confirm them before deployment. Latency and accuracy have not been benchmarked in this project. Speed notes are qualitative descriptions from the providers, not measurements; test representative URLs to compare quality and timing. Context windows and structured output support are taken from provider documentation.

| Provider/model | Input / output price | Context | JSON support | Speed profile (provider-described) | Accuracy evidence / fit |
|---|---:|---:|---|---|---|
| Google Gemini 3.1 Flash-Lite | $0.25 / $1.50 | 1M tokens | JSON Schema structured output | Low-latency, high-volume model (Google description) | No benchmark here; configured primary |
| OpenAI GPT-6 Luna | $0.10 / $0.50 | 1.05M tokens | Structured output; validate responses in-app | Focused, high-volume tasks (OpenAI description) | No benchmark here; cost-sensitive alternative, provider integration not implemented |
| Anthropic Claude Haiku 5.5 | $0.10 / $0.50 for prompts up to 100K; $0.50 / $2.50 above | Check current model docs | Structured output support; validate responses in-app | Latency-sensitive extraction/classification (Anthropic description) | No benchmark here; potential alternative, provider integration not implemented |

Sources: [Google Gemini model catalog](https://ai.google.dev/gemini-api/docs/models), [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini structured output guide](https://ai.google.dev/gemini-api/docs/structured-output), [Google GenAI SDK migration guide](https://ai.google.dev/gemini-api/docs/migrate), [OpenAI model catalog and prices](https://developers.openai.com/api/docs/models), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

### Recommendation and estimated per-analysis cost

Use Gemini 3.1 Flash-Lite as the primary: Google lists it as stable, low-latency, and cost-efficient. Gemini 3.5 Flash-Lite is configured as fallback. Neither Gemini 3.7 nor 3.8 is configured. Free-tier limits and temporary service load can still cause errors for any model; Google applies limits per project and model. Use a paid API tier for sustained use. This is a practical fit recommendation, not a claim of highest accuracy. Validate output quality on labeled sites before relying on it in production. The primary model and fallback can be changed with `GEMINI_MODEL` and `GEMINI_FALLBACK_MODELS`.

At an estimated 12,000 input tokens and 2,200 output tokens, using Gemini 3.1 Flash-Lite prices of $0.25/M input and $1.50/M output, the estimated paid-tier LLM cost is:

`(12,000 * $0.25 + 2,200 * $1.50) / 1,000,000 = $0.0063 per analysis`

The estimate excludes retries, taxes, and separately billed features; actual token counts depend on the website. Response time is unmeasured; benchmark cold and warm requests before setting production latency expectations. OpenAI GPT-6 Luna is a lower-cost alternative, but provider switching is not wired into this implementation.

### Cost and quality controls

- Remove non-content markup and cap extracted text before calling the model.
- Keep one request per analysis and use a concise schema-driven prompt.
- Cache results by normalized URL plus a content hash and refresh on a defined TTL.
- Track actual token usage and per-domain latency; tune text and output limits from those measurements.
- Compare a low-cost model with a stronger model on labeled examples. Escalate only ambiguous or low-confidence results.
- Use SEO/search-volume APIs only when actual keyword metrics are needed; do not ask the LLM to fabricate them.

## Deployment and submission

The application is deployed at **https://ai-link-analysis.fastapicloud.dev**. Configure `GEMINI_API_KEY` in the FastAPI Cloud app's secret/environment settings; never commit the key or a local `.env` file. The live API docs are at https://ai-link-analysis.fastapicloud.dev/docs. For local use, run with `uvicorn app.main:app --host 0.0.0.0 --port 4000`.
