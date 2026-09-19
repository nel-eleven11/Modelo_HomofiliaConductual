"""Deterministic Spanish text generation for offline runs."""

from homophily_sim.llm.base import UtteranceRequest, UtteranceResult


class MockLanguageModelProvider:
    """Use short templates that preserve the requested topic orientation."""

    def generate_utterance(self, request: UtteranceRequest) -> UtteranceResult:
        if request.orientation > 0.25:
            stance = "Estoy a favor de esta idea."
        elif request.orientation < -0.25:
            stance = "No estoy a favor de esta idea."
        else:
            stance = "Tengo una postura neutral sobre esta idea."
        context = "Sobre tu comentario y " if request.previous_message else "Sobre "
        words = f"{stance} {context}{request.topic_prompt}".split()
        return UtteranceResult(text=" ".join(words[:request.max_words]))
