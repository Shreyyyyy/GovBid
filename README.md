# 🇮🇳 GovBid Intelligence

AI-powered discovery and analysis of publicly accessible Indian government procurement / GeM-related bid information.

> Deterministic procurement search engine enhanced by AI — not "an LLM that searches tenders."
> Groq is used only for query parsing, document analysis, summarization, and "Ask this bid" Q&A.
> Filtering, sorting, deduplication, date math, and currency math are all plain Python/SQL.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment

Create `.env` (see `.env.example`):

```
groq_api_key=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
ENABLED_SOURCES=gem
MAX_PAGES_PER_SOURCE=10
REQUEST_DELAY_SECONDS=1
```

- `ENABLED_SOURCES` defaults to `gem` only — this build searches **GeM exclusively** (see
  "What sources are currently connected" below for why CPPP/Ministry are off by default).

- `groq_api_key` (lowercase) or `GROQ_API_KEY` are both supported.
- `GROQ_MODEL` defaults to `llama-3.3-70b-versatile` if unset. **Note:** Groq periodically
  retires/rotates model IDs — if you see a `model_not_found` error, run
  `python -c "from groq import Groq; from src.config import settings; print([m.id for m in Groq(api_key=settings.groq_api_key).models.list().data])"`
  to list models currently available to your key, and set `GROQ_MODEL` accordingly.
- The key is loaded server-side only (`src/config.py`) via `python-dotenv`. It is never
  logged (see `src/utils/logging.py`, which redacts `gsk_...` tokens), never sent to the
  browser, and never hardcoded.
- Never commit the real `.env` (see `.gitignore`).

## Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (typically http://localhost:8501).

Type a query and click **🔍 Search GeM** — this immediately runs a live search against GeM's
public bid listing and shows results with a direct link back to each bid's source page. No
setup step is required first. (If you'd rather explore without hitting the live site, **Admin
→ Load Demo Data** populates a handful of clearly-marked `DEMO` records instead.)

## Architecture

```
Streamlit (app.py)
    ↓
Query Parser        (src/ai/query_parser.py — Groq → strict JSON filters, Pydantic-validated)
    ↓
Search Engine       (src/search/ — deterministic SQL filters, then optional local semantic ranking)
    ↓
Source Connectors   (src/ingestion/ — GeM / CPPP / Ministry / Demo, each independently toggleable)
    ↓
PDF Extraction      (src/extraction/ — PyMuPDF → pdfplumber → OCR fallback, page-tagged text)
    ↓
Groq Analysis       (src/ai/bid_analyzer.py, src/extraction/requirement_extractor.py)
    ↓
SQLite (SQLAlchemy) (src/models.py, src/database.py)
```

The LLM **never** decides which bids match a query or performs sorting/counting/date math —
it only converts natural language into structured filters, and summarizes/extracts from
already-retrieved document text. All of that is enforced in `src/search/filters.py`,
`src/utils/dates.py`, and `src/utils/currency.py`.

## What is implemented

- Natural-language query parsing → strict Pydantic-validated JSON filters (Groq), with a
  graceful keyword-only fallback if Groq is unavailable/misconfigured.
- Deterministic structured filtering (ministry, department, organization, category,
  subcategory, state, city, status, value range, quantity range, closing-date range,
  OEM/MSE/startup preference) plus a dependency-light local semantic ranking pass.
- Source connector architecture (`BaseConnector`) with `search()`, `fetch_bid()`,
  `fetch_documents()`, `normalize()`, `health_check()` — GeM, CPPP, Ministry, and a
  clearly-labeled Demo connector, independently enabled via `ENABLED_SOURCES`.
- Deduplication by bid_id → source+bid_id → canonical URL → content hash → normalized
  title+organization, preserving multiple source URLs on a single bid record.
- PDF download (size/type validated) and text extraction preserving page boundaries, with
  a PyMuPDF → pdfplumber → OCR (best-effort, degrades gracefully) fallback chain.
- AI requirement extraction and full bid analysis, strictly grounded in indexed document
  text, with every extracted fact retaining its source document/page.
- "Ask this bid" chat grounded only in indexed documents, with an explicit
  "The available bid documents do not specify this." fallback.
- SQLite/SQLAlchemy models for bids, documents, requirements, source records, saved
  searches, and alerts (alerts have a real DB model and UI; notification delivery is an
  explicit placeholder, not faked).
- Dashboard analytics computed only from actual database rows (never fabricated).
- Ministry Explorer, Category Explorer, Saved Searches (save/run/delete), CSV/Excel/JSON
  export, and an Admin page with per-source ingestion logs.
- Manual PDF upload on the bid detail page for sources that can't be reached programmatically.

## What sources are currently connected

- **GeM** (`src/ingestion/gem_connector.py`): **performs real, live scraping.** GeM's public
  "All Bids" page (`bidplus.gem.gov.in/all-bids`) is server-rendered and calls a public,
  anonymous JSON endpoint (`all-bids-data`) to load bid cards for any visitor — no login, no
  CAPTCHA, and `robots.txt` permits it (only `/resources/` and a couple of unrelated
  bank-guarantee paths are disallowed). The connector replicates exactly what the page's own
  JavaScript does: load the public page once to get a session cookie + CSRF token, then reuse
  both for the same search calls, paginated up to `MAX_PAGES_PER_SOURCE` with
  `REQUEST_DELAY_SECONDS` between requests. Each returned bid also has a real
  `showbidDocument/<id>` PDF link; use **"📥 Fetch documents from source"** on a bid's
  Documents tab to download and extract it on demand (not done in bulk during search, to
  keep polling polite). Verified against the live site: real bid numbers, ministries,
  category names, and closing dates, plus real PDF tender documents that flow correctly
  through AI Analysis and Ask-This-Bid with page citations.
- **CPPP / eProcure** (`src/ingestion/cppp_connector.py`): **investigated and found
  CAPTCHA-gated.** Every tender-listing view on eprocure.gov.in (`FrontEndLatestActiveTenders`,
  `FrontEndTendersByOrganisation`, `FrontEndListTendersbyDate`, etc.) renders a CAPTCHA image
  and explicitly requires solving it before returning any tender rows. Per this project's
  rules, CAPTCHAs are never bypassed, so this connector only does a reachability check and
  reports `Unavailable for automated access`, with a link to search CPPP manually.
- **Ministry sources** (`src/ingestion/ministry_connector.py`): generic connector driven by
  a configurable list of verified, static, public ministry tender pages
  (`MINISTRY_SOURCES` in that file — empty by default until an operator adds verified URLs).
- **Demo** (`src/ingestion/demo_connector.py`): local, clearly-labeled (`source = "DEMO"`)
  sample data for development/testing. The UI always renders a ⚠ DEMO DATA badge on these
  records and they are never presented as real government data.

On the Search Results page, click **"🌐 Search live sources now"** to run all enabled
connectors with your current parsed filters before showing results — this is what actually
queries GeM (and any other enabled source) live rather than only searching what's already
in the local database.

## Known limitations

- GeM's `all-bids-data` endpoint is undocumented (it's the site's internal AJAX contract,
  not a published API) and can change without notice — a markup/JS change on GeM's side
  could break the CSRF-token or field parsing. When that happens the connector will fail
  loudly (caught and reported as unavailable) rather than return wrong data.
- Not every GeM bid has a downloadable tender PDF at the time it's listed (e.g. older reverse
  auction records); "Fetch documents from source" reports unavailable rather than guessing
  in that case.
- CPPP has no automated data path at all under this project's CAPTCHA rule — real CPPP data
  requires a human to search it manually in a browser.
- Semantic search is a simple local term-overlap scorer, not a vector/embedding index (kept
  modular so ChromaDB/FAISS/embeddings can be swapped in later without touching callers).
- OCR fallback requires `pytesseract` + a system Tesseract install; if unavailable, scanned
  PDFs will simply be marked as empty-extraction rather than crashing.
- Alerts are stored and displayed but do not send real notifications yet
  ("Alert engine configured — notification provider can be connected later.").

## How to add another government procurement source

1. Create `src/ingestion/<name>_connector.py` subclassing `BaseConnector`
   (`src/ingestion/base_connector.py`) and implement `health_check()`, `search()`,
   `fetch_bid()`, `fetch_documents()`. Use `self.normalize(raw_dict)` to map source-specific
   fields onto the shared normalized bid schema.
2. Register it in `_CONNECTOR_REGISTRY` in `src/services/ingestion_service.py`.
3. Add its short name to `ENABLED_SOURCES` in `.env` to enable it.
4. If the source cannot be reached without bypassing CAPTCHA/login/anti-bot/robots
   restrictions, return a `SourceStatus(reachable=False/True, message="Unavailable for
   automated access: ...")` — never fabricate bids.
5. Add a focused test under `tests/` for any new parsing/normalization logic.

## Testing

```bash
pytest -q
python -m compileall .
```

## Deployment

- Runs anywhere Python + SQLite are available: `streamlit run app.py`. No FastAPI, no
  Node.js, no database server, no Docker requirement.
- For **Streamlit Community Cloud**, configure `groq_api_key` (and optionally `GROQ_MODEL`,
  `ENABLED_SOURCES`, etc.) via the app's **Secrets**, not a committed `.env`.
- Streamlit is not a Vercel-style app; do not deploy it as a standard Vercel Node/React
  project. Use Streamlit Community Cloud or any generic Python host that can run a
  long-lived `streamlit run` process.
# GovBid
