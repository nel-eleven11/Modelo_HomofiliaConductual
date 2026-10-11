"""Local SQLite cache keyed by all inputs that can change generated wording."""

import json
import sqlite3
from hashlib import sha256
from pathlib import Path

from homophily_sim.llm.base import UtteranceRequest, UtteranceResult


def utterance_cache_key(
    request: UtteranceRequest,
    *,
    model: str,
    prompt_version: str,
    temperature: float,
    max_output_tokens: int,
    generation_seed: int,
) -> str:
    """Hash model, prompt and request, including the prior-message hash."""
    previous_hash = sha256(
        json.dumps(request.previous_message, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    payload = {
        "model": model,
        "prompt_version": prompt_version,
        "request": request.model_dump(mode="json", exclude={"previous_message"}),
        "previous_message_hash": previous_hash,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "generation_seed": generation_seed,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


class SqliteUtteranceCache:
    """Persist exact generated messages without storing prompts or API keys."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS utterances "
                "(cache_key TEXT PRIMARY KEY, text TEXT NOT NULL)"
            )

    def get(self, key: str) -> UtteranceResult | None:
        with sqlite3.connect(self.path, timeout=30) as connection:
            row = connection.execute(
                "SELECT text FROM utterances WHERE cache_key = ?", (key,)
            ).fetchone()
        return UtteranceResult(text=row[0]) if row else None

    def put(self, key: str, result: UtteranceResult) -> None:
        with sqlite3.connect(self.path, timeout=30) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO utterances(cache_key, text) VALUES (?, ?)",
                (key, result.text),
            )
