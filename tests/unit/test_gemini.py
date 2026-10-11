"""Gemini adapter, prompt and cache tests without any network request."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from google.genai import errors

from homophily_sim.llm.base import UtteranceRequest
from homophily_sim.llm.cache import SqliteUtteranceCache, utterance_cache_key
from homophily_sim.llm.gemini import (
    EmptyGeminiResponseError,
    GeminiLanguageModelProvider,
    GeminiRateLimitError,
)
from homophily_sim.llm.prompts import PROMPT_VERSION, SYSTEM_INSTRUCTION, build_prompt


def _request() -> UtteranceRequest:
    return UtteranceRequest(
        agent_id=7,
        topic_id="tech_ai_jobs",
        topic_prompt="¿Qué opinas de la IA?",
        orientation=-0.7,
        relevant_interests=("technology",),
        extraversion=6.0,
        previous_message="Creo que ayuda.",
        max_words=5,
    )


def _provider(
    tmp_path: Path, client: Mock, *, refresh_cache: bool = False
) -> GeminiLanguageModelProvider:
    return GeminiLanguageModelProvider(
        client=client,
        cache=SqliteUtteranceCache(tmp_path / "utterances.sqlite3"),
        model="gemini-2.5-flash-lite",
        generation_seed=42,
        refresh_cache=refresh_cache,
    )


def test_prompt_contains_only_linguistic_context() -> None:
    prompt = build_prompt(_request())
    assert "tech_ai_jobs" in prompt
    assert "-0.7000" in prompt
    assert "technology" in prompt
    assert "Creo que ayuda." in prompt
    assert "máximo 5 palabras" in prompt
    assert "No calcules probabilidades" in SYSTEM_INSTRUCTION
    assert PROMPT_VERSION


def test_cache_key_changes_with_all_relevant_inputs() -> None:
    request = _request()

    def key(value: UtteranceRequest, model: str = "gemini-2.5-flash-lite", seed: int = 42) -> str:
        return utterance_cache_key(
            value,
            model=model,
            prompt_version=PROMPT_VERSION,
            temperature=0.3,
            max_output_tokens=128,
            generation_seed=seed,
        )

    original = key(request)
    assert original != key(request.model_copy(update={"agent_id": 8}))
    assert original != key(request.model_copy(update={"topic_id": "other_topic"}))
    assert original != key(request.model_copy(update={"orientation": 0.7}))
    assert original != key(request.model_copy(update={"previous_message": "No estoy de acuerdo."}))
    assert original != key(request.model_copy(update={"relevant_interests": ("science",)}))
    assert original != key(request, model="another-model")
    assert original != key(request, seed=43)


def test_sdk_is_mocked_and_second_call_uses_persistent_cache(tmp_path: Path) -> None:
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        text="  No estoy de acuerdo con esa idea y explico por qué. "
    )
    first = _provider(tmp_path, client)
    result = first.generate_utterance(_request())
    second = _provider(tmp_path, client)
    assert second.generate_utterance(_request()) == result
    assert result.text == "No estoy de acuerdo con"
    assert client.models.generate_content.call_count == 1
    assert second.cache_hits == 1
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash-lite"
    assert kwargs["config"].temperature == 0.3
    assert kwargs["config"].seed == 42
    assert kwargs["config"].max_output_tokens == 128


def test_rate_limit_empty_response_and_cached_fallback(tmp_path: Path) -> None:
    client = Mock()
    client.models.generate_content.side_effect = errors.APIError(429, {"message": "rate"})
    provider = _provider(tmp_path, client)
    with pytest.raises(GeminiRateLimitError):
        provider.generate_utterance(_request())
    client.models.generate_content.side_effect = None
    client.models.generate_content.return_value = SimpleNamespace(text="   ")
    with pytest.raises(EmptyGeminiResponseError):
        provider.generate_utterance(_request())
    client.models.generate_content.return_value = SimpleNamespace(text="Una respuesta breve.")
    saved = provider.generate_utterance(_request())
    client.models.generate_content.side_effect = TimeoutError("timed out")
    refreshed = _provider(tmp_path, client, refresh_cache=True)
    assert refreshed.generate_utterance(_request()) == saved
    assert refreshed.cache_hits == 1


def test_sdk_client_receives_timeout_and_exponential_retry_policy(tmp_path: Path) -> None:
    with patch("homophily_sim.llm.gemini.genai.Client") as client_factory:
        GeminiLanguageModelProvider(
            api_key="test-key",
            cache=SqliteUtteranceCache(tmp_path / "cache.sqlite3"),
            timeout_ms=12_000,
            retry_attempts=3,
        )
    options = client_factory.call_args.kwargs["http_options"]
    assert options.timeout == 12_000
    assert options.retry_options.attempts == 3
    assert options.retry_options.exp_base == 2.0
    assert 429 in options.retry_options.http_status_codes
