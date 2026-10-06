"""Structured OpenRouter calls for five-option answers."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import instructor
import litellm
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel

litellm.suppress_debug_info = True
load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLM:
    def __init__(
        self,
        model_id: str,
        *,
        reasoning_effort: str | None = "high",
        temperature: float = 1.0,
        max_tokens: int = 8192,
    ):
        self.model_name = (
            model_id
            if model_id.startswith("openrouter/")
            else f"openrouter/{model_id}"
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self._client = instructor.from_litellm(completion)

    def ask(
        self,
        messages: list[dict],
        response_model: type[ResponseModelT],
    ) -> tuple[ResponseModelT, dict]:
        kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "response_model": response_model,
            "max_retries": 3,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": 300,
        }
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
            kwargs["allowed_openai_params"] = ["reasoning_effort"]
            kwargs["temperature"] = 1

        parsed, raw = self._client.chat.completions.create_with_completion(**kwargs)
        serialized = (
            raw.model_dump(mode="json") if hasattr(raw, "model_dump") else raw
        )
        return parsed, serialized
