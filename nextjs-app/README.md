# GovBid Intelligence (Next.js)

A lean Next.js port of the core search flow from the Streamlit app one level up:
natural-language search → Groq-parsed filters → live GeM search → big result cards
with direct links back to each bid's GeM source page.

## What's included

- One page (`app/page.tsx`): search box, optional filters (ministry, category,
  status, quantity), results rendered as big cards matching GeM's own bid card
  layout (BID NO, Items, Quantity, Start/End Date, Department, status, link).
- One API route (`app/api/search/route.ts`): parses the query with Groq, then
  calls GeM's public `all-bids-data` endpoint the same way the Streamlit app's
  `GemConnector` does (session cookie + CSRF token, no login/CAPTCHA bypass).
- `lib/gem.ts` — the GeM connector, ported from `src/ingestion/gem_connector.py`.
- `lib/groq.ts` — query parsing via Groq's chat completions API.

## What's NOT included (out of scope for this quick port)

The Streamlit app's AI Analysis, Ask-This-Bid, PDF extraction/upload, dashboard,
and SQLite persistence are not ported here — this covers only the live search
and result display. If you want those here too, they'd need to be added as
additional API routes (PDF text extraction in Node, a database, etc.).

## Setup

```bash
npm install
cp .env.local.example .env.local   # then fill in GROQ_API_KEY
npm run dev
```

Open http://localhost:3000.

## Known limitation (same as the Streamlit app)

GeM blocks known cloud/PaaS datacenter IP ranges at the firewall level. If you
deploy this to Vercel (or any similar host), it runs on shared cloud IPs and
may get a connection-refused error reaching GeM — this is not a bug, and this
project does not attempt to route around GeM's access controls. It works
reliably when run locally or from a normal ISP connection.
