"""
Centralized LLM client using Google AI Studio (Gemini) directly.

All LLM calls in the application go through this client, which provides:
- Retry with exponential backoff + rate-limit awareness
- Structured JSON output enforcement
- Token usage tracking
- Error wrapping with ExystBaseError hierarchy

Uses the official `google-genai` SDK exclusively — no litellm, no OpenAI.
"""

import json
import time
import asyncio
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings
from app.core.exceptions import LLMError, LLMOutputParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


T = TypeVar("T", bound=BaseModel)


class LLMResponse:
    """Wrapper around an LLM response with metadata."""

    def __init__(
        self,
        content: str,
        model: str,
        usage: dict[str, int] | None = None,
        latency_ms: float = 0,
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.latency_ms = latency_ms

    def parse_json(self) -> dict[str, Any]:
        """Parse content as JSON, cleaning markdown fences if present."""
        cleaned = self.content.strip()

        # Remove markdown code fences
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMOutputParsingError(
                message=f"Failed to parse LLM JSON output: {str(e)}",
                raw_output=cleaned,
            )

    def parse_as(self, model_class: type[T]) -> T:
        """Parse content into a Pydantic model."""
        data = self.parse_json()
        try:
            return model_class.model_validate(data)
        except Exception as e:
            raise LLMOutputParsingError(
                message=f"LLM output doesn't match schema {model_class.__name__}: {str(e)}",
                raw_output=self.content[:500],
            )


class LLMClient:
    """
    Centralized LLM client using Google AI Studio (Gemini) directly.

    Usage:
        client = LLMClient()
        response = await client.complete("What is 2+2?")
        data = response.parse_json()
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        settings = get_settings()
        self.model = model or settings.DEFAULT_LLM_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize the Google GenAI client
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Send a completion request to Gemini with retry logic.

        Args:
            prompt: The user message.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Max response tokens.
            response_format: Optional format enforcement (e.g., {"type": "json_object"}).

        Returns:
            LLMResponse with parsed content and metadata.
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.perf_counter()

                # Build config
                config_kwargs: dict[str, Any] = {
                    "temperature": temperature,
                }
                if max_tokens:
                    config_kwargs["max_output_tokens"] = max_tokens

                # System instruction
                if system_prompt:
                    config_kwargs["system_instruction"] = system_prompt

                # JSON mode
                if response_format and response_format.get("type") == "json_object":
                    config_kwargs["response_mime_type"] = "application/json"

                config = types.GenerateContentConfig(**config_kwargs)

                # Use run_in_executor to call the sync SDK method from async context
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    ),
                )

                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                content = response.text or ""

                # Extract usage metadata
                usage: dict[str, int] = {}
                if response.usage_metadata:
                    usage = {
                        "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                        "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                        "total_tokens": response.usage_metadata.total_token_count or 0,
                    }

                logger.info(
                    "llm_call_success",
                    model=self.model,
                    attempt=attempt,
                    latency_ms=latency_ms,
                    tokens_used=usage.get("total_tokens", 0),
                )

                return LLMResponse(
                    content=content.strip(),
                    model=self.model,
                    usage=usage,
                    latency_ms=latency_ms,
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "llm_call_failed",
                    model=self.model,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(e),
                )

                if attempt < self.max_retries:
                    err_msg = str(e).lower()
                    if "429" in err_msg or "rate" in err_msg or "exhausted" in err_msg or "resource_exhausted" in err_msg:
                        delay = 15.0
                        logger.info("gemini_rate_limit_detected_waiting_15s", attempt=attempt)
                    else:
                        delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                        logger.info("gemini_retry_waiting", delay_seconds=delay)

                    await asyncio.sleep(delay)

        raise LLMError(
            message=f"Gemini call failed after {self.max_retries} attempts: {str(last_error)}",
            model=self.model,
        )

    async def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """
        Convenience method: complete and parse as JSON.

        Returns parsed dict directly. Raises LLMOutputParsingError on failure.
        """
        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.parse_json()

    async def complete_structured(
        self,
        prompt: str,
        output_model: type[BaseModel],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> BaseModel:
        """
        Complete and parse into a Pydantic model.

        Returns a validated Pydantic instance. Raises LLMOutputParsingError on failure.
        """
        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.parse_as(output_model)
