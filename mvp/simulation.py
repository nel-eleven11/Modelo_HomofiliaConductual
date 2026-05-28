"""Simulation flow for the behavioral homophily MVP."""

from __future__ import annotations

import random

from agent import StudentAgent
from environment import CourseEnvironment


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
DIAS_SEMANA = [
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
]


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


def decidir_interaccion(
    agente_1: StudentAgent,
    agente_2: StudentAgent,
    entorno: CourseEnvironment,
    generador: random.Random | None = None,
) -> dict[str, object]:
    """Decide whether two students interact using the homophily rule."""
    generador = generador or random.Random()
    similitud = agente_1.calcular_similitud(agente_2)
    probabilidad = entorno.calcular_probabilidad_interaccion(agente_1, agente_2)
    interactuan = generador.random() < probabilidad

    if interactuan:
        agente_1.registrar_interaccion(agente_2)
        agente_2.registrar_interaccion(agente_1)

    return {
        "agente_1": agente_1.id,
        "agente_2": agente_2.id,
        "similitud": similitud,
        "probabilidad_interaccion": probabilidad,
        "interaccion": interactuan,
    }


def simular_dias(
    entorno: CourseEnvironment,
    duracion_dias: int = 7,
    semilla: int | None = None,
) -> list[dict[str, object]]:
    """Run the interaction simulation for a short period of days."""
    if not 7 <= duracion_dias <= 30:
        raise ValueError("La duracion de la simulacion debe estar entre 7 y 30 dias.")

    generador = random.Random(semilla)
    registros = []

    for dia_numero in range(1, duracion_dias + 1):
        dia_semana = DIAS_SEMANA[(dia_numero - 1) % len(DIAS_SEMANA)]
        interacciones_dia = 0

        if entorno.hay_clase(dia_semana):
            for agente_1, agente_2 in entorno.obtener_pares_posibles():
                resultado = decidir_interaccion(
                    agente_1,
                    agente_2,
                    entorno,
                    generador,
                )
                resultado["dia"] = dia_numero
                resultado["dia_semana"] = dia_semana
                registros.append(resultado)

                if resultado["interaccion"]:
                    interacciones_dia += 1

        print(
            f"Dia {dia_numero} ({dia_semana}) completado: "
            f"{interacciones_dia} interacciones."
        )

    return registros
