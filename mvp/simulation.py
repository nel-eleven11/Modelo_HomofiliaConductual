"""Simulation flow for the behavioral homophily MVP."""

from __future__ import annotations

import random

from agent import StudentAgent


NOMBRES = [
    "Ana",
    "Luis",
    "Sofia",
    "Diego",
    "Camila",
    "Pablo",
    "Andrea",
    "Javier",
    "Valeria",
    "Mateo",
    "Lucia",
    "Carlos",
    "Maria",
    "Fernando",
    "Elena",
    "Roberto",
    "Gabriela",
    "Jose",
    "Paola",
    "Daniel",
]

GUSTOS_POSIBLES = [
    "programacion",
    "videojuegos",
    "musica",
    "deportes",
    "lectura",
    "arte",
    "anime",
    "tecnologia",
]

GENEROS_POSIBLES = ["F", "M", "Otro"]
CARRERA_BASE = "Ingenieria en Ciencias de la Computacion"


def generar_agentes(cantidad: int = 10, semilla: int | None = None) -> list[StudentAgent]:
    """Generate synthetic student agents for the MVP simulation."""
    if not 10 <= cantidad <= 20:
        raise ValueError("La cantidad de agentes debe estar entre 10 y 20.")

    generador = random.Random(semilla)
    nombres = generador.sample(NOMBRES, cantidad)

    agentes = []
    for indice, nombre in enumerate(nombres, start=1):
        gustos = generador.sample(GUSTOS_POSIBLES, k=generador.randint(2, 4))
        agente = StudentAgent(
            id=indice,
            nombre=nombre,
            edad=generador.randint(18, 24),
            genero=generador.choice(GENEROS_POSIBLES),
            carrera=CARRERA_BASE,
            semestre=generador.randint(1, 10),
            gustos=gustos,
            extroversion=round(generador.uniform(0.0, 1.0), 2),
            responsabilidad=round(generador.uniform(0.0, 1.0), 2),
        )
        agentes.append(agente)

    return agentes
