# 🚀 BUILD: GOVBID INTELLIGENCE

You are a senior Python engineer, AI engineer, data engineer, web scraping engineer, and Streamlit UI/UX developer.

Build a working MVP called:

**GovBid Intelligence**

The application is an AI-powered government procurement/tender discovery and analysis tool focused on Indian government procurement and publicly accessible GeM-related bid information.

The goal is:

A user should be able to open one Streamlit application and type:

> "Show me all desktop computer bids from Ministry of Finance"

The application should discover/search available permitted public government procurement information, apply accurate filters, extract useful information from tender documents, and present the results in a professional UI.

---

# ⚠️ IMPORTANT SOURCE / ACCESS RULES

Do NOT bypass:

* CAPTCHA
* authentication
* login requirements
* anti-bot systems
* rate limits
* access controls
* robots restrictions
* paywalls

Do NOT attempt to defeat or circumvent government website security.

Only use publicly accessible/permitted sources.

The application must clearly identify the source of every bid.

If a source cannot be accessed programmatically:

* don't bypass the restriction
* don't fake the data
* expose the source URL when available
* allow the user to manually upload/import documents if appropriate
* continue using other available sources

NEVER fabricate a tender, bid ID, price, date, specification, ministry, quantity, or eligibility requirement.

---

# 🎯 PRIMARY USE CASE

The primary workflow is:

USER QUERY
↓
AI QUERY PARSER
↓
STRUCTURED FILTERS
↓
PUBLIC PROCUREMENT SEARCH
↓
NORMALIZATION
↓
DEDUPLICATION
↓
DOCUMENT EXTRACTION
↓
AI ANALYSIS
↓
RESULTS

Example:

User:

"Show me all desktop computers in Ministry of Finance"

The system should understand:

keywords:
desktop computer

organization/ministry:
Ministry of Finance

category:
Computers

Then search available procurement sources.

---

# 🧰 TECH STACK

Use ONLY Python for the MVP.

Frontend/UI:

* Streamlit

AI:

* Groq API

Default Groq model:

llama-3.3-70b-versatile

Make the model configurable.

Data:

* SQLite for MVP
* SQLAlchemy ORM

Vector search:

* Start with simple local semantic-search abstraction
* Keep vector search modular
* If practical, use ChromaDB or FAISS
* Do not make vector search mandatory for basic filtering

Documents:

* PyMuPDF
* pdfplumber
* OCR fallback where practical

Data processing:

* pandas
* requests
* BeautifulSoup
* lxml

Configuration:

* python-dotenv
* Pydantic Settings if useful

Charts:

* Plotly

Exports:

* pandas
* openpyxl

Testing:

* pytest

---

# 📁 PROJECT STRUCTURE

Create:

govbid-intelligence/

├── app.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
│
├── src/
│   ├── **init**.py
│   │
│   ├── config.py
│   │
│   ├── database.py
│   ├── models.py
│   │
│   ├── ai/
│   │   ├── **init**.py
│   │   ├── groq_client.py
│   │   ├── query_parser.py
│   │   ├── bid_analyzer.py
│   │   └── prompts.py
│   │
│   ├── ingestion/
│   │   ├── **init**.py
│   │   ├── base_connector.py
│   │   ├── gem_connector.py
│   │   ├── cppp_connector.py
│   │   └── ministry_connector.py
│   │
│   ├── extraction/
│   │   ├── **init**.py
│   │   ├── pdf_extractor.py
│   │   ├── text_cleaner.py
│   │   └── requirement_extractor.py
│   │
│   ├── search/
│   │   ├── **init**.py
│   │   ├── filters.py
│   │   ├── search_engine.py
│   │   └── semantic_search.py
│   │
│   ├── services/
│   │   ├── **init**.py
│   │   ├── bid_service.py
│   │   ├── ingestion_service.py
│   │   └── analytics_service.py
│   │
│   └── utils/
│       ├── **init**.py
│       ├── dates.py
│       ├── currency.py
│       ├── deduplication.py
│       └── logging.py
│
├── data/
│   ├── govbid.db
│   ├── raw/
│   ├── documents/
│   └── processed/
│
└── tests/
├── test_query_parser.py
├── test_filters.py
├── test_deduplication.py
└── test_pdf_extraction.py

Keep the code modular even though the application is only one Streamlit app.

---

# 🔐 GROQ API KEY

The existing `.env` already contains:

groq_api_key=

DO NOT ask the user for the key again.

DO NOT hardcode it.

DO NOT print it.

DO NOT expose it to the Streamlit UI.

DO NOT commit it.

Load it server-side using python-dotenv.

Support:

groq_api_key

and optionally:

GROQ_API_KEY

Configuration example:

groq_api_key = os.getenv("groq_api_key") or os.getenv("GROQ_API_KEY")

Model:

GROQ_MODEL=llama-3.3-70b-versatile

If GROQ_MODEL does not exist, use the default above.

---

# 🤖 GROQ CLIENT

Create:

src/ai/groq_client.py

Use the official Groq Python SDK.

Create a reusable client:

GroqClient

Methods:

chat()
structured_output()
summarize()

Handle:

timeouts
API errors
rate limits
invalid responses

Never expose API credentials.

---

# 🧠 QUERY PARSER

Create:

src/ai/query_parser.py

The user should be able to enter natural-language procurement queries.

Examples:

"desktop computers in Ministry of Finance"

"active laptop tenders from central government"

"computer bids above 10 lakh closing within 15 days"

"desktop workstation tenders requiring OEM authorization"

"Ministry of Finance IT procurement"

"printers in Delhi government departments"

Convert the query into strict structured JSON.

Schema:

{
"keywords": [],
"organization": [],
"ministry": [],
"department": [],
"category": [],
"subcategory": [],
"state": [],
"city": [],
"status": null,
"min_value": null,
"max_value": null,
"min_quantity": null,
"max_quantity": null,
"closing_after": null,
"closing_before": null,
"semantic_query": null
}

Use Pydantic to validate the response.

IMPORTANT:

The LLM is NOT allowed to directly decide which bids match.

The LLM only converts natural language into filters.

Actual filtering happens in Python/SQLite.

---

# 🔎 SEARCH ENGINE

Create:

src/search/search_engine.py

Search should work in this order:

1. Structured filters
2. Keyword matching
3. Semantic search when useful
4. Optional ranking

Structured filters are deterministic.

Examples:

status = ACTIVE

estimated_value >= 1000000

quantity >= 100

closing_date <= X

ministry = "Ministry of Finance"

Do not ask Groq to filter a large dataset.

---

# 🏛️ SOURCE CONNECTOR SYSTEM

Create a common interface:

BaseConnector

Methods:

search()
fetch_bid()
fetch_documents()
normalize()
health_check()

Create:

GemConnector
CpppConnector
MinistryConnector

IMPORTANT:

The connectors must be designed so they can be independently enabled/disabled.

Configuration:

ENABLED_SOURCES=gem,cppp,ministry

If direct automated access to a source is unavailable or blocked:

return a clear source status such as:

"Unavailable for automated access"

Do not bypass the restriction.

---

# 🌐 PROCUREMENT SOURCES

Prioritize publicly accessible/permitted information from:

* GeM-related public bid pages/information
* Central Public Procurement Portal / eProcurement
* official ministry procurement/tender pages
* official department tender pages

Use requests with:

reasonable timeout
user-agent
rate limiting
retry logic

Do not aggressively crawl websites.

Do not crawl unlimited pages.

Implement configurable limits:

MAX_PAGES_PER_SOURCE=10
REQUEST_DELAY_SECONDS=1

These can be changed later.

---

# 📦 NORMALIZED BID MODEL

Every source must normalize into the same structure:

{
"bid_id": "",
"title": "",
"description": "",
"source": "",
"source_url": "",
"organization": "",
"ministry": "",
"department": "",
"buyer_name": "",
"category": "",
"subcategory": "",
"quantity": null,
"estimated_value": null,
"currency": "INR",
"bid_start_date": null,
"bid_end_date": null,
"status": "",
"delivery_location": "",
"state": "",
"city": "",
"eligibility": "",
"technical_requirements": "",
"financial_requirements": "",
"experience_requirements": "",
"oem_required": null,
"mse_preference": null,
"startup_preference": null,
"turnover_requirement": "",
"past_experience_requirement": "",
"documents": [],
"raw_data": {}
}

---

# 🗄️ SQLITE DATABASE

Use SQLite for MVP.

Create:

bids

bid_documents

bid_requirements

source_records

saved_searches

alerts

Use SQLAlchemy.

Automatically create tables on startup.

Do not require a database server for the MVP.

---

# ♻️ DEDUPLICATION

Deduplicate using:

1. bid_id
2. source + bid_id
3. canonical URL
4. content hash
5. normalized title + organization as fallback

A bid appearing on multiple official sources should not become multiple independent bids.

Instead preserve multiple source URLs.

---

# 📄 PDF DOCUMENT PROCESSING

Create:

src/extraction/pdf_extractor.py

When a bid has a PDF:

1. download it
2. save it locally
3. calculate hash
4. extract text
5. detect whether extraction is empty
6. use OCR fallback where practical
7. store extracted text
8. preserve page boundaries

Every page should remain identifiable.

Example:

{
"page": 4,
"text": "Minimum annual turnover..."
}

---

# 🤖 AI REQUIREMENT EXTRACTION

Use Groq to extract information from documents.

Extract:

Product
Quantity
Technical specifications
Eligibility
OEM requirements
Turnover
Past experience
Certifications
Warranty
Delivery period
Delivery location
EMD
Performance security
Important dates
Documents required
Special conditions

Output:

{
"technical_requirements": [],
"eligibility_requirements": [],
"financial_requirements": [],
"experience_requirements": [],
"oem_requirements": [],
"certifications": [],
"warranty": null,
"delivery_period": null,
"delivery_location": [],
"important_dates": [],
"documents_required": []
}

Every extracted item should contain:

{
"value": "...",
"document": "...",
"page": 4
}

If something is not present:

null

NEVER infer missing information.

---

# 📌 SOURCE TRACEABILITY

Every important AI-extracted field must retain:

source document
page
source URL

Example:

Minimum turnover

₹10 crore

Source:
ATC.pdf — Page 4

[Open Source]

The UI must make this visible.

This is a core requirement.

---

# 🧠 BID ANALYSIS

Create:

src/ai/bid_analyzer.py

Add:

"Analyze Bid"

The AI should produce:

## Summary

Short factual summary.

## Procurement

What is being purchased?

Quantity?

Category?

## Technical Requirements

List extracted requirements.

## Eligibility

OEM
Turnover
Experience
Certifications

## Commercial

Bid value
EMD
Security
Payment terms

## Delivery

Location
Delivery period

## Important Dates

Opening
Closing
Pre-bid meeting

## Documents

Required documents.

## Important Notes

Only information supported by source documents.

No hallucinations.

---

# 💬 ASK THIS BID

On every bid detail page, add:

"Ask this bid"

Example questions:

"What are the eligibility requirements?"

"What processor is required?"

"What is the minimum turnover?"

"When does the bid close?"

"List all required documents."

"What are the technical specifications?"

Answers MUST use only indexed source documents.

If information is missing:

"The available bid documents do not specify this."

Show source document/page for factual answers.

---

# 🎨 STREAMLIT UI

Create a polished Streamlit application.

Do NOT make it look like a raw Streamlit demo.

Use:

custom CSS
cards
metrics
tabs
expanders
tables
icons/emojis where appropriate
clean spacing
professional typography

Use Streamlit session_state where needed.

---

# 🏠 HOME PAGE

Header:

# 🇮🇳 GovBid Intelligence

Subtitle:

AI-powered government procurement discovery and analysis.

Large search box:

"Search government bids in natural language..."

Example:

Show me all desktop computer bids from Ministry of Finance

Button:

🔍 Search Bids

Below search:

Quick searches:

[Desktop Computers]
[Ministry of Finance]
[Laptops]
[Active IT Bids]
[Closing Soon]

---

# 📊 DASHBOARD

Show metrics:

Total Bids
Active Bids
Closing Soon
Total Procurement Value

Charts:

Bids by Ministry
Bids by Category
Bids by State
Bids over Time
Upcoming Closures

All metrics must come from actual database records.

Never fabricate dashboard numbers.

---

# 🔍 SEARCH RESULTS

After searching:

Show:

"142 bids found"

Then display active filters:

Ministry: Ministry of Finance
Category: Computer
Status: Active

Allow filters in sidebar:

Ministry
Department
Organization
Category
Subcategory
State
City
Status
Minimum Value
Maximum Value
Minimum Quantity
Maximum Quantity
Closing Date
OEM Required
MSE Preference
Startup Preference

---

# 📋 BID TABLE

Columns:

Bid ID
Title
Organization
Department
Category
Quantity
Value
Closing Date
Status
Location

Use Streamlit dataframe/table.

Allow selection.

Provide:

[View]

for each bid.

---

# 📄 BID DETAILS

When user opens a bid:

Show header:

Bid ID
Title
Status
Closing Date

Then metric cards:

Quantity
Estimated Value
Organization
Location

Tabs:

Overview
Technical
Eligibility
Commercial
Documents
AI Analysis
Sources

---

# 📑 DOCUMENTS TAB

Show:

Document name
Type
Pages
Source

Buttons:

Open Source
Download

If the document is stored locally, allow download.

---

# 🤖 AI ANALYSIS TAB

Button:

"Analyze with Groq"

Show:

Summary
Technical Requirements
Eligibility
Commercial
Delivery
Important Dates
Documents Required
Important Notes

Cache analysis.

Do not call Groq repeatedly for the same unchanged document.

---

# 💬 ASK BID TAB

Chat-style interface.

Example:

User:

What is the minimum turnover?

AI:

₹10 crore.

Source:
ATC.pdf — Page 4

Use st.chat_message.

Maintain conversation in session state.

---

# 🏛️ MINISTRY EXPLORER

Create a page/sidebar section:

"Ministries"

Show ministries available in the database.

Click:

Ministry of Finance

Show:

Total bids
Active bids
Categories
Departments
Recent bids
Upcoming bids

Allow filtering to:

Computers

Desktop Computers

Laptops

etc.

---

# 🖥️ CATEGORY EXPLORER

Show:

Computers & IT

Desktop Computers
Laptops
Workstations
Servers
Printers
Networking
Storage
Software

These should be generated from actual records where possible.

---

# ⭐ SAVED SEARCHES

Allow users to save searches.

Example:

"Finance Ministry Desktop Computers"

Store:

natural language query
parsed filters
created date

Allow:

Run
Delete

---

# 📤 EXPORT

Allow users to export search results.

Formats:

CSV
Excel
JSON

Use pandas/openpyxl.

---

# 🔔 ALERT ARCHITECTURE

Create alert database model even if notifications are not fully implemented in MVP.

Example:

Query:

Ministry of Finance
+
Desktop Computer
+
Active

Store it.

Add UI:

"Create Alert"

For MVP, provide a clear placeholder:

"Alert engine configured — notification provider can be connected later."

Do not fake notification delivery.

---

# 🛠️ ADMIN / DATA INGESTION

Sidebar:

Admin

Show:

Source
Status
Last Run
Records Found
New Records
Failed Records

Buttons:

[Run All Sources]

[Run GeM]

[Run CPPP]

[Run Ministry Sources]

[Re-index]

All ingestion should have logs.

---

# 🧪 DEMO DATA

Do NOT create fake government bids that look real.

For development testing, create clearly marked demo records.

Example:

source = "DEMO"

UI must show:

⚠ Demo Data

Never mix demo records with real records without clearly identifying them.

---

# 🔒 SECURITY

Implement:

* `.env` secrets
* `.gitignore`
* no API key exposure
* safe URL validation
* request timeouts
* download size limits
* file type validation
* SQLAlchemy parameterized queries
* error handling

Never log the Groq API key.

---

# ⚡ PERFORMANCE

Use caching where appropriate.

Streamlit:

@st.cache_data

for safe expensive data retrieval.

Cache:

database reads
source results
PDF extraction
AI analysis

Do not cache sensitive user state incorrectly.

Avoid unnecessary Groq calls.

---

# 🧠 AI COST CONTROL

Groq should only be used for:

1. Natural language query parsing
2. Document information extraction
3. Bid summarization
4. Ask-this-bid questions

Do NOT use Groq for:

sorting
filtering
counting
date calculations
aggregation
duplicate detection
simple string matching

Use Python/SQLite for those.

---

# 📅 DATE HANDLING

All date filtering must be deterministic.

Use Python datetime.

Support:

"next 7 days"
"next 15 days"
"this month"
"closing this week"

Convert these to exact dates in Python.

Do not let the LLM calculate date differences.

---

# 💰 CURRENCY HANDLING

Normalize Indian currency values.

Examples:

₹10 lakh
10 lakhs
1 crore
₹1,25,00,000

Convert internally to INR numeric values.

Example:

₹10 lakh → 1,000,000

₹1 crore → 10,000,000

Display using Indian formatting.

---

# 🧮 ANALYTICS

Create analytics service.

Functions:

get_total_bids()
get_active_bids()
get_total_value()
get_category_breakdown()
get_ministry_breakdown()
get_state_breakdown()
get_upcoming_bids()

All calculations must be based on actual database records.

---

# 🧪 TESTS

Create tests for:

Query parsing

Example:

Input:

desktop computers Ministry of Finance

Expected:

category contains Computer
ministry contains Ministry of Finance

Test:

₹10 lakh conversion

1 crore conversion

date filtering

quantity filtering

deduplication

PDF extraction

database insertion

search

---

# 📦 REQUIREMENTS.TXT

Include only required dependencies.

Example categories:

streamlit
groq
python-dotenv
sqlalchemy
pandas
requests
beautifulsoup4
lxml
pymupdf
pdfplumber
plotly
openpyxl
pydantic
pytest

Only add packages when actually used.

---

# ▶️ RUNNING THE APP

The application must run with:

streamlit run app.py

No FastAPI.

No Node.js.

No Docker requirement for the MVP.

No external database server.

---

# 📄 README

Create a complete README.

Include:

## Installation

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

## Environment

Explain:

groq_api_key=
GROQ_MODEL=

Do NOT show the real key.

## Run

streamlit run app.py

## Architecture

Explain:

Streamlit
↓
Query Parser
↓
Search Engine
↓
Source Connectors
↓
PDF Extraction
↓
Groq Analysis
↓
SQLite

## Source limitations

Explain that automated collection only works where public/permitted access is available and that CAPTCHA/authentication/access controls are not bypassed.

---

# 🚀 DEPLOYMENT

The app should be deployment-friendly.

IMPORTANT:

Do not claim Streamlit can be deployed as a normal Vercel application.

For Streamlit deployment, make the project compatible with:

Streamlit Community Cloud

and generic Python hosting.

Keep all configuration environment-based.

For Streamlit Cloud:

groq_api_key

should be configured through Streamlit Secrets/environment configuration.

Never commit the actual `.env`.

---

# 🎯 FINAL UX TEST

After implementation, verify this exact flow:

1. Run:

streamlit run app.py

2. Open the application.

3. Enter:

"Show me all desktop computer bids from Ministry of Finance"

4. Groq parses the query.

5. Python converts it into filters.

6. Search sources/database.

7. Results appear.

8. User sees:

Bid ID
Title
Ministry
Department
Quantity
Value
Closing Date
Status
Source

9. User opens a bid.

10. User sees detailed information.

11. User clicks:

"Analyze with Groq"

12. AI extracts:

technical specifications
eligibility
turnover
OEM requirements
delivery
dates
documents

13. Every important extracted fact shows its source/page where available.

14. User can ask:

"What is the minimum turnover?"

15. AI answers only from source documents.

16. User can export results.

---

# 🧠 ENGINEERING PRINCIPLE

This application is NOT an "LLM that searches tenders."

It is:

A deterministic procurement search engine enhanced by AI.

Use:

Python → data processing
SQLite → storage
SQL → filtering
Pandas → analytics
Requests/BeautifulSoup → permitted public-source collection
PyMuPDF → documents
Groq → language understanding and document analysis
Streamlit → UI

Keep AI isolated and replaceable.

---

# 🚨 DO NOT DO THESE THINGS

Do not:

* fabricate tender data
* fabricate government information
* bypass CAPTCHA
* bypass login
* bypass anti-bot protection
* scrape aggressively
* expose API keys
* put Groq API key in frontend/browser code
* make Groq decide numeric filters
* invent missing specifications
* claim unavailable data is verified
* create fake "real" demo tenders
* create unnecessary microservices
* create FastAPI for this MVP
* create React/Next.js
* create Docker unless useful
* over-engineer the first version

Keep it simple, fast, modular and actually runnable.

---

# 🔥 START NOW

Do NOT only explain the architecture.

Actually create the complete project.

Create every required file.

Implement the Streamlit UI.

Implement Groq integration.

Implement SQLite.

Implement the query parser.

Implement search/filtering.

Implement source connector architecture.

Implement PDF extraction.

Implement AI analysis.

Implement exports.

Implement tests.

Implement README.

Then run:

pytest

and:

python -m compileall .

Fix all errors.

Finally run:

streamlit run app.py

and verify that the application starts successfully.

At the end, provide:

1. Project structure
2. Setup commands
3. Environment variables
4. Run command
5. What is implemented
6. What sources are currently connected
7. Known limitations
8. How to add another government procurement source

Do not stop at pseudocode.

BUILD THE ACTUAL APPLICATION.
