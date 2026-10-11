"""Google Gemini text provider, isolated from social-model decisions."""

import os

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from homophily_sim.llm.base import UtteranceRequest, UtteranceResult
from homophily_sim.llm.cache import SqliteUtteranceCache, utterance_cache_key
from homophily_sim.llm.prompts import PROMPT_VERSION, SYSTEM_INSTRUCTION, build_prompt


class LanguageGenerationError(RuntimeError):
    """The provider could not generate a usable utterance."""


class GeminiRateLimitError(LanguageGenerationError):
    """Gemini remained rate-limited after the SDK retry policy."""


class EmptyGeminiResponseError(LanguageGenerationError):
    """Gemini returned no text that can be used as a conversation message."""


class GeminiLanguageModelProvider:
    """Generate short Spanish messages with SDK retries and a local cache."""

    def __init__(
        self,
        *,
        cache: SqliteUtteranceCache | None = None,
        client: genai.Client | None = None,
        api_key: str | None = None,
        model: str | None = None,
        generation_seed: int = 0,
        temperature: float = 0.3,
        max_output_tokens: int = 128,
        timeout_ms: int = 30_000,
        retry_attempts: int = 3,
        refresh_cache: bool = False,
    ) -> None:
        load_dotenv()
        self.model_name = (
            model if model is not None else (os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite")
        )
        if not self.model_name.strip():
            raise ValueError("Gemini model name cannot be empty")
        if not 0 <= temperature <= 1:
            raise ValueError("temperature must be in [0, 1]")
        if max_output_tokens < 1 or timeout_ms < 1 or retry_attempts < 1:
            raise ValueError("token limit, timeout and retry attempts must be positive")
        if client is None:
            secret = api_key or os.getenv("GEMINI_API_KEY")
            if not secret:
                raise ValueError("GEMINI_API_KEY is required for the Gemini provider")
            client = genai.Client(
                api_key=secret,
                http_options=types.HttpOptions(
                    timeout=timeout_ms,
                    retry_options=types.HttpRetryOptions(
                        attempts=retry_attempts,
                        initial_delay=1.0,
                        exp_base=2.0,
                        max_delay=8.0,
                        jitter=0.0,
                        http_status_codes=[408, 429, 500, 502, 503, 504],
                    ),
                ),
            )
        self.client = client
        self.cache = cache or SqliteUtteranceCache(
            os.getenv("HOMOPHILY_LLM_CACHE_PATH", "outputs/llm_cache.sqlite3")
        )
        self.generation_seed = generation_seed
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout_ms = timeout_ms
        self.retry_attempts = retry_attempts
        self.refresh_cache = refresh_cache
        self.cache_hits = 0
        self.api_calls = 0

    def generate_utterance(self, request: UtteranceRequest) -> UtteranceResult:
        """Return a cached wording or request one completion from the SDK."""
        key = utterance_cache_key(
            request,
            model=self.model_name,
            prompt_version=PROMPT_VERSION,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            generation_seed=self.generation_seed,
        )
        cached = self.cache.get(key)
        if cached is not None and not self.refresh_cache:
            self.cache_hits += 1
            return cached
        self.api_calls += 1
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=build_prompt(request),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                    seed=self.generation_seed,
                    candidate_count=1,
                ),
            )
            text = " ".join((response.text or "").split())
        except errors.APIError as exc:
            if cached is not None:
                self.cache_hits += 1
                return cached
            if exc.code == 429:
                raise GeminiRateLimitError("Gemini rate limit exhausted after retries") from exc
            if exc.code == 404:
                raise LanguageGenerationError(
                    f"Gemini model {self.model_name} is unavailable (404). "
                    "Check access or set GEMINI_MODEL=gemini-3.5-flash-lite in .env"
                ) from exc
            raise LanguageGenerationError(f"Gemini request failed with status {exc.code}") from exc
        except (httpx.TimeoutException, httpx.TransportError, TimeoutError) as exc:
            if cached is not None:
                self.cache_hits += 1
                return cached
            raise LanguageGenerationError("Gemini request timed out or lost connection") from exc
        if not text:
            if cached is not None:
                self.cache_hits += 1
                return cached
            raise EmptyGeminiResponseError("Gemini returned an empty response")
        result = UtteranceResult(text=" ".join(text.split()[: request.max_words]))
        self.cache.put(key, result)
        return result
