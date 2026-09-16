"""Full bid analysis and 'Ask this bid' Q&A, grounded strictly in extracted
document text. Results are cached per-bid so Groq is not called repeatedly
for an unchanged document set."""
from __future__ import annotations

from typing import Any, List, Optional

from src.ai.groq_client import GroqClient, GroqClientError
from src.ai.prompts import ASK_BID_SYSTEM_PROMPT, BID_ANALYSIS_SYSTEM_PROMPT
from src.utils.logging import get_logger

logger = get_logger(__name__)

MAX_CONTEXT_CHARS = 24_000


def _build_document_context(documents: List[dict]) -> str:
    """documents: [{"name": str, "pages": [{"page": int, "text": str}]}]"""
    chunks = []
    total = 0
    for doc in documents:
        name = doc.get("name", "document")
        for page in doc.get("pages", []):
            page_num = page.get("page")
            text = (page.get("text") or "").strip()
            if not text:
                continue
            block = f"\n--- Document: {name} | Page {page_num} ---\n{text}\n"
            if total + len(block) > MAX_CONTEXT_CHARS:
                break
            chunks.append(block)
            total += len(block)
    return "".join(chunks)


class BidAnalyzer:
    def __init__(self, client: Optional[GroqClient] = None):
        self._client = client

    def _get_client(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def analyze(self, bid_meta: dict, documents: List[dict]) -> dict[str, Any]:
        """Produce a structured analysis grounded only in provided document text.
        Callers are responsible for caching the result (see BidDocument.analysis_cache)."""
        context = _build_document_context(documents)
        if not context.strip():
            return {
                "summary": "No extracted document text is available for this bid.",
                "procurement": {"what": bid_meta.get("title", ""), "quantity": bid_meta.get("quantity"), "category": bid_meta.get("category")},
                "technical_requirements": [],
                "eligibility": {"oem": None, "turnover": None, "experience": None, "certifications": None},
                "commercial": {"bid_value": bid_meta.get("estimated_value"), "emd": None, "security": None, "payment_terms": None},
                "delivery": {"location": bid_meta.get("delivery_location"), "period": None},
                "important_dates": [],
                "documents_required": [],
                "important_notes": "Analysis limited to bid metadata; no source documents were indexed.",
            }

        user_prompt = (
            f"BID METADATA:\n{bid_meta}\n\n"
            f"SOURCE DOCUMENT TEXT (page-tagged):\n{context}"
        )
        try:
            client = self._get_client()
            return client.structured_output(
                system_prompt=BID_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=3000,
            )
        except GroqClientError as exc:
            logger.error("Bid analysis failed: %s", exc)
            return {"error": str(exc)}

    def ask(self, question: str, documents: List[dict]) -> str:
        context = _build_document_context(documents)
        if not context.strip():
            return "The available bid documents do not specify this."

        try:
            client = self._get_client()
            return client.chat(
                system_prompt=ASK_BID_SYSTEM_PROMPT,
                user_prompt=f"SOURCE DOCUMENT TEXT (page-tagged):\n{context}\n\nQUESTION: {question}",
                temperature=0.0,
                max_tokens=800,
            )
        except GroqClientError as exc:
            logger.error("Ask-bid failed: %s", exc)
            return f"Unable to answer right now ({exc})."
