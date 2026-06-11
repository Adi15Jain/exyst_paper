"""
Centralized LLM client using Google AI Studio (Gemini) directly.

Optimized for free-tier rate limits with:
- Multi-model fallback chain (Flash → Flash Lite → Gemma)
- Prompt-level response caching (skip repeat calls)
- Adaptive rate limiting with per-model tracking
- Smart retry with exponential backoff
- Task-tiered model routing (heavy tasks get Flash, light tasks get Lite)

Uses the official `google-genai` SDK exclusively — no litellm, no OpenAI.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings
from app.core.exceptions import LLMError, LLMOutputParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Model tiers — route tasks to the cheapest model that can handle them
# ---------------------------------------------------------------------------
MODEL_FALLBACK_CHAIN = [
    "gemini-2.5-flash",       # Best quality, 5 RPM, 20 RPD
    "gemini-2.5-flash-lite",  # Good quality, 10 RPM, 20 RPD
    "gemma-4-31b-it",         # Good quality, 15 RPM, UNLIMITED RPD
]

# Models suited for simpler tasks (classification, validation, extraction)
LITE_MODELS = [
    "gemini-2.5-flash-lite",  # 10 RPM, 20 RPD — good for structured JSON
    "gemma-4-31b-it",         # 15 RPM, unlimited RPD — great fallback
]

# ---------------------------------------------------------------------------
# In-memory prompt cache — avoids re-calling the API for identical prompts
# ---------------------------------------------------------------------------
_prompt_cache: dict[str, tuple[str, float]] = {}  # hash -> (response_content, timestamp)
CACHE_TTL_SECONDS = 3600  # Cache responses for 1 hour

# ---------------------------------------------------------------------------
# Per-model request tracking for smart rotation
# ---------------------------------------------------------------------------
_model_request_counts: dict[str, list[float]] = {}  # model -> list of timestamps

# Free-tier limits
MODEL_LIMITS = {
    "gemini-2.5-flash": {"rpm": 5, "rpd": 20},
    "gemini-2.5-flash-lite": {"rpm": 10, "rpd": 20},
    "gemini-3.5-flash": {"rpm": 5, "rpd": 20},
    "gemma-4-31b-it": {"rpm": 15, "rpd": 1500},  # Effectively unlimited
    "gemma-4-26b-it": {"rpm": 15, "rpd": 1500},
}


def _cache_key(prompt: str, system_prompt: str | None, temperature: float) -> str:
    """Generate a cache key from prompt parameters."""
    raw = f"{system_prompt or ''}|{prompt}|{temperature}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached_response(key: str) -> str | None:
    """Check if a valid cached response exists."""
    if key in _prompt_cache:
        content, timestamp = _prompt_cache[key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return content
        else:
            del _prompt_cache[key]  # Expired
    return None


def _set_cache(key: str, content: str) -> None:
    """Store a response in cache."""
    _prompt_cache[key] = (content, time.time())
    # Evict old entries if cache gets too large
    if len(_prompt_cache) > 200:
        oldest_key = min(_prompt_cache, key=lambda k: _prompt_cache[k][1])
        del _prompt_cache[oldest_key]


def _track_request(model: str) -> None:
    """Record a request timestamp for rate tracking."""
    if model not in _model_request_counts:
        _model_request_counts[model] = []
    _model_request_counts[model].append(time.time())


def _get_rpm_usage(model: str) -> int:
    """Get number of requests in the last 60 seconds for a model."""
    if model not in _model_request_counts:
        return 0
    cutoff = time.time() - 60
    _model_request_counts[model] = [
        t for t in _model_request_counts[model] if t > cutoff
    ]
    return len(_model_request_counts[model])


def _pick_best_model(preferred: str, fallback_chain: list[str]) -> str:
    """
    Pick the best available model based on current rate limit usage.
    Tries the preferred model first, then falls back through the chain.
    """
    # Check if preferred model has room
    limits = MODEL_LIMITS.get(preferred, {"rpm": 5, "rpd": 20})
    usage = _get_rpm_usage(preferred)
    if usage < limits["rpm"] - 1:  # Leave 1 slot buffer
        return preferred

    # Try fallbacks
    for model in fallback_chain:
        if model == preferred:
            continue
        limits = MODEL_LIMITS.get(model, {"rpm": 5, "rpd": 20})
        usage = _get_rpm_usage(model)
        if usage < limits["rpm"] - 1:
            logger.info(
                "model_fallback",
                preferred=preferred,
                fallback=model,
                preferred_rpm_usage=_get_rpm_usage(preferred),
            )
            return model

    # All models at limit — return preferred and let retry handle it
    return preferred


class LLMResponse:
    """Wrapper around an LLM response with metadata."""

    def __init__(
        self,
        content: str,
        model: str,
        usage: dict[str, int] | None = None,
        latency_ms: float = 0,
        cached: bool = False,
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.latency_ms = latency_ms
        self.cached = cached

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

    Features:
    - Multi-model fallback (Flash → Flash Lite → Gemma)
    - Prompt-level caching (skip repeat API calls)
    - Adaptive rate limit tracking
    - Smart retry with exponential backoff

    Usage:
        client = LLMClient()
        response = await client.complete("What is 2+2?")

        # For lightweight tasks (classification, validation):
        client = LLMClient(tier="lite")
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 4,
        retry_delay: float = 2.0,
        tier: str = "default",
    ):
        """
        Args:
            model: Specific model override.
            max_retries: Max retry attempts.
            retry_delay: Base delay for exponential backoff.
            tier: "default" for best model, "lite" for lightweight tasks.
        """
        settings = get_settings()
        self.preferred_model = model or settings.DEFAULT_LLM_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.tier = tier
        self.timeout = settings.LLM_TIMEOUT_SECONDS

        # Choose fallback chain based on tier
        if tier == "lite":
            self.fallback_chain = LITE_MODELS
            if not model:
                self.preferred_model = LITE_MODELS[0]
        else:
            self.fallback_chain = MODEL_FALLBACK_CHAIN

        # Initialize the Google GenAI client
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> LLMResponse:
        """
        Send a completion request to Gemini with caching, fallback, and retry.

        Args:
            prompt: The user message.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Max response tokens.
            response_format: Optional format enforcement (e.g., {"type": "json_object"}).
            use_cache: Whether to check/store prompt cache (default True).

        Returns:
            LLMResponse with parsed content and metadata.
        """
        # --- Check cache first ---
        if use_cache:
            cache_key = _cache_key(prompt, system_prompt, temperature)
            cached = _get_cached_response(cache_key)
            if cached is not None:
                logger.info("llm_cache_hit", cache_key=cache_key[:12])
                return LLMResponse(
                    content=cached,
                    model="cache",
                    latency_ms=0,
                    cached=True,
                )

        last_error = None

        # Ordered model candidates: start with the least rate-limited model, then
        # rotate through the rest of the fallback chain. A model that is overloaded
        # (503/UNAVAILABLE) or rate-limited is therefore NOT retried in place — the
        # next attempt uses a different model, which is far more likely to succeed.
        first_choice = _pick_best_model(self.preferred_model, self.fallback_chain)
        candidates: list[str] = []
        for m in [first_choice, self.preferred_model, *self.fallback_chain]:
            if m not in candidates:
                candidates.append(m)

        for attempt in range(1, self.max_retries + 1):
            model = candidates[(attempt - 1) % len(candidates)]

            try:
                start_time = time.perf_counter()

                # Gemma models don't support a system role or JSON-mime mode in AI
                # Studio, so for them we fold the system prompt into the text and rely
                # on parse_json()'s fence-stripping instead of response_mime_type.
                is_gemma = model.startswith("gemma")
                effective_prompt = prompt

                config_kwargs: dict[str, Any] = {
                    "temperature": temperature,
                }
                if max_tokens:
                    config_kwargs["max_output_tokens"] = max_tokens
                if system_prompt:
                    if is_gemma:
                        effective_prompt = f"{system_prompt}\n\n{prompt}"
                    else:
                        config_kwargs["system_instruction"] = system_prompt

                # JSON mode (not supported by Gemma)
                if (
                    response_format
                    and response_format.get("type") == "json_object"
                    and not is_gemma
                ):
                    config_kwargs["response_mime_type"] = "application/json"

                config = types.GenerateContentConfig(**config_kwargs)

                # Track the request
                _track_request(model)

                # Use run_in_executor for sync SDK, bounded by a timeout so a
                # hung request raises (and is retried) instead of stalling.
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda mdl=model, cfg=config, txt=effective_prompt: (
                            self.client.models.generate_content(
                                model=mdl,
                                contents=txt,
                                config=cfg,
                            )
                        ),
                    ),
                    timeout=self.timeout,
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
                    model=model,
                    attempt=attempt,
                    latency_ms=latency_ms,
                    tokens_used=usage.get("total_tokens", 0),
                    preferred=self.preferred_model,
                )

                # Cache the successful response
                if use_cache:
                    _set_cache(cache_key, content.strip())

                return LLMResponse(
                    content=content.strip(),
                    model=model,
                    usage=usage,
                    latency_ms=latency_ms,
                )

            except TimeoutError:
                last_error = TimeoutError(
                    f"Gemini call to {model} exceeded {self.timeout}s timeout"
                )
                logger.warning(
                    "llm_call_timeout",
                    model=model,
                    attempt=attempt,
                    timeout_seconds=self.timeout,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))
                continue

            except Exception as e:
                last_error = e
                err_msg = str(e).lower()

                is_rate_limit = any(
                    kw in err_msg
                    for kw in ["429", "rate", "exhausted", "resource_exhausted", "quota"]
                )

                logger.warning(
                    "llm_call_failed",
                    model=model,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(e)[:200],
                    is_rate_limit=is_rate_limit,
                )

                if attempt < self.max_retries:
                    next_model = candidates[attempt % len(candidates)]
                    if is_rate_limit:
                        # Rate limited — modest wait; the next attempt also switches model.
                        delay = 8.0 + (attempt * 4)
                        logger.info(
                            "rate_limit_backoff",
                            model=model,
                            next_model=next_model,
                            delay_seconds=delay,
                        )
                    else:
                        delay = self.retry_delay * (2 ** (attempt - 1))
                        logger.info(
                            "retry_backoff",
                            model=model,
                            next_model=next_model,
                            delay_seconds=delay,
                        )

                    await asyncio.sleep(delay)

        raise LLMError(
            message=f"Gemini call failed after {self.max_retries} attempts: {str(last_error)}",
            model=self.preferred_model,
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
