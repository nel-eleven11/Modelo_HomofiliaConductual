"""Manually probe 5-10 Gemini utterances; this command requires an API key."""

import argparse
from pathlib import Path

from homophily_sim.data.topics import load_topics
from homophily_sim.llm.base import UtteranceRequest
from homophily_sim.llm.gemini import GeminiLanguageModelProvider


def main() -> None:
    """Run a small, explicit set of prompts outside the automated test suite."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", type=Path, default=Path("data/topics/topics_v1.yaml"))
    parser.add_argument("--count", type=int, choices=range(5, 11), default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    bank = load_topics(args.topics)
    provider = GeminiLanguageModelProvider(generation_seed=args.seed)
    orientations = (-0.8, -0.4, 0.0, 0.4, 0.8)
    for index, topic in enumerate(bank.topics[: args.count]):
        request = UtteranceRequest(
            agent_id=index,
            topic_id=topic.topic_id,
            topic_prompt=topic.prompt,
            orientation=orientations[index % len(orientations)],
            relevant_interests=(topic.category,),
            extraversion=5.0,
            previous_message="Me interesa tu opinión sobre esto." if index % 2 else None,
            max_words=30,
        )
        result = provider.generate_utterance(request)
        print(f"{topic.topic_id}: {result.text}")
    print(f"API calls: {provider.api_calls}; cache hits: {provider.cache_hits}")


if __name__ == "__main__":
    main()
