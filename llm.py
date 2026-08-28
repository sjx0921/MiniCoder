"""A small OpenAI-compatible chat-completions client built on the stdlib."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Call an OpenAI-compatible ``/chat/completions`` endpoint locally."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None, timeout_seconds: int = 90) -> None:
        self.api_key = api_key or os.getenv("MINICODER_API_KEY")
        self.base_url = (base_url or os.getenv("MINICODER_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("MINICODER_MODEL") or "gpt-4o-mini"
        self.timeout_seconds = timeout_seconds

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("MINICODER_API_KEY is not set. Add it to your environment and try again.")
        payload = json.dumps({"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions", data=payload, method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:2_000]
            raise LLMError(f"Model API returned HTTP {exc.code}: {body}") from exc
        except (URLError, TimeoutError) as exc:
            raise LLMError(f"Could not reach model API at {self.base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError("Model API returned invalid JSON") from exc
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Model API returned no assistant message: {str(data)[:2_000]}") from exc
