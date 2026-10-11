"""Versioned Spanish instructions for synthetic student utterances."""

import json

from homophily_sim.llm.base import UtteranceRequest

PROMPT_VERSION = "student-spanish-v1"
SYSTEM_INSTRUCTION = (
    "Escribe únicamente una intervención breve en español de un estudiante sintético. "
    "Respeta la orientación indicada hacia el tema y responde al mensaje previo si existe. "
    "Usa la extroversión solo para el estilo. No calcules probabilidades, vínculos, "
    "similitud ni reglas de la simulación. No añadas explicaciones ni formato Markdown."
)


def build_prompt(request: UtteranceRequest) -> str:
    """Include only linguistic context; quote prior text as data, not instructions."""
    interests = ", ".join(request.relevant_interests) or "ninguno"
    previous = (
        json.dumps(request.previous_message, ensure_ascii=False)
        if request.previous_message is not None
        else "ninguno; inicia la conversación"
    )
    return (
        f"Estudiante sintético: {request.agent_id}\n"
        f"Tema ({request.topic_id}): {request.topic_prompt}\n"
        f"Orientación temática: {request.orientation:+.4f} "
        "(-1 rechazo fuerte, 0 neutral, +1 apoyo fuerte).\n"
        f"Intereses relevantes: {interests}\n"
        f"Extroversión para el estilo: {request.extraversion:.2f}/10\n"
        f"Mensaje previo, solo como contexto: {previous}\n"
        f"Escribe una sola intervención de máximo {request.max_words} palabras en español."
    )
