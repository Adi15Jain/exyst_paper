"""
Centralized LLM client with retry logic, structured output, and provider abstraction.

All LLM calls in the application go through this client, which provides:
- Retry with exponential backoff
- Structured JSON output enforcement
- Token usage tracking
- Error wrapping with ExystBaseError hierarchy
"""

import json
import time
from typing import Any, TypeVar

from litellm import acompletion
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
    Centralized LLM client for all AI operations.

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

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Send a completion request to the LLM with retry logic.

        Args:
            prompt: The user message.
            system_prompt: Optional system message for role instruction.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Max response tokens.
            response_format: Optional format enforcement (e.g., {"type": "json_object"}).

        Returns:
            LLMResponse with parsed content and metadata.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.perf_counter()

                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                if response_format:
                    kwargs["response_format"] = response_format

                response = await acompletion(**kwargs)

                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                content = response.choices[0].message.content or ""  # type: ignore
                usage = dict(response.usage) if response.usage else {}  # type: ignore

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
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info("llm_retry_waiting", delay_seconds=delay)
                    import asyncio
                    await asyncio.sleep(delay)

        raise LLMError(
            message=f"LLM call failed after {self.max_retries} attempts: {str(last_error)}",
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
