"""Thin, reusable wrapper around the Groq SDK.

Never logs or exposes the API key. Never used to filter/sort/aggregate data -
that logic lives in Python/SQLite per the engineering principle of this app.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from groq import APIError, APITimeoutError, RateLimitError
from groq import Groq

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GroqClientError(RuntimeError):
    """Raised for any recoverable Groq client failure."""


class GroqClient:
    """Reusable Groq chat client.

    The API key is read server-side from settings (never accepted as a
    constructor argument from UI code, so it can't leak into widgets).
    """

    def __init__(self, model: Optional[str] = None, timeout: float = 30.0):
        if not settings.has_groq_key:
            raise GroqClientError(
                "Groq API key is not configured. Set groq_api_key in .env."
            )
        self._client = Groq(api_key=settings.groq_api_key, timeout=timeout)
        self.model = model or settings.groq_model

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request and return the raw text content."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except RateLimitError as exc:
            logger.warning("Groq rate limit hit")
            raise GroqClientError("Groq rate limit reached. Please try again shortly.") from exc
        except APITimeoutError as exc:
            logger.warning("Groq request timed out")
            raise GroqClientError("Groq request timed out.") from exc
        except APIError as exc:
            logger.error("Groq API error: %s", getattr(exc, "message", str(exc)))
            raise GroqClientError(f"Groq API error: {getattr(exc, 'message', 'unknown error')}") from exc

        if not response.choices:
            raise GroqClientError("Groq returned no choices.")

        content = response.choices[0].message.content
        if content is None:
            raise GroqClientError("Groq returned an empty response.")
        return content

    def structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Chat completion that must return valid JSON. Raises GroqClientError
        if the response cannot be parsed as JSON."""
        raw = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cleaned = _strip_code_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Groq JSON response")
            raise GroqClientError("Groq returned invalid JSON.") from exc

    def summarize(self, text: str, instructions: str = "Summarize factually. Do not add information not present in the text.") -> str:
        if not text.strip():
            return ""
        return self.chat(
            system_prompt="You produce concise, factual summaries. Never invent details.",
            user_prompt=f"{instructions}\n\nTEXT:\n{text}",
            temperature=0.1,
            max_tokens=512,
        )


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
