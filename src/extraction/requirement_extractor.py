"""AI-assisted requirement extraction from tender document text.

Every extracted item must retain its source document, page, and (where
available) source URL, per the source-traceability requirement.
"""
from __future__ import annotations

from typing import Any, List, Optional

from src.ai.groq_client import GroqClient, GroqClientError
from src.ai.prompts import REQUIREMENT_EXTRACTION_SYSTEM_PROMPT
from src.extraction.text_cleaner import truncate_for_context
from src.utils.logging import get_logger

logger = get_logger(__name__)

_EMPTY_RESULT: dict[str, Any] = {
    "technical_requirements": [],
    "eligibility_requirements": [],
    "financial_requirements": [],
    "experience_requirements": [],
    "oem_requirements": [],
    "certifications": [],
    "warranty": None,
    "delivery_period": None,
    "delivery_location": [],
    "important_dates": [],
    "documents_required": [],
}


class RequirementExtractor:
    def __init__(self, client: Optional[GroqClient] = None):
        self._client = client

    def _get_client(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def extract(self, document_name: str, pages: List[dict], source_url: Optional[str] = None) -> dict[str, Any]:
        """pages: [{"page": int, "text": str}, ...]"""
        page_tagged_text = "\n".join(
            f"[Document: {document_name} | Page {p['page']}]\n{p['text']}"
            for p in pages
            if p.get("text", "").strip()
        )
        page_tagged_text = truncate_for_context(page_tagged_text)

        if not page_tagged_text.strip():
            return dict(_EMPTY_RESULT)

        try:
            client = self._get_client()
            result = client.structured_output(
                system_prompt=REQUIREMENT_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=page_tagged_text,
                max_tokens=3000,
            )
        except GroqClientError as exc:
            logger.error("Requirement extraction failed for %s: %s", document_name, exc)
            return dict(_EMPTY_RESULT)

        merged = dict(_EMPTY_RESULT)
        for key in merged:
            if key in result:
                merged[key] = result[key]

        if source_url:
            for key, value in merged.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and "source_url" not in item:
                            item["source_url"] = source_url

        return merged
