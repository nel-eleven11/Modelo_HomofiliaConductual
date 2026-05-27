"""Interaction environment definitions for the behavioral homophily MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from agent import StudentAgent


@dataclass
class CourseEnvironment:
    """Represents a shared course where students can interact."""

    nombre_curso: str
    estudiantes: list[StudentAgent]
    dias_clase: list[str] = field(
        default_factory=lambda: ["lunes", "miercoles", "viernes"]
    )
    probabilidad_base_interaccion: float = 0.10
    peso_homofilia: float = 0.50

    def obtener_pares_posibles(self) -> list[tuple[StudentAgent, StudentAgent]]:
        """Return all student pairs that coincide in the course."""
        return list(combinations(self.estudiantes, 2))

    def calcular_probabilidad_interaccion(
        self, estudiante_1: StudentAgent, estudiante_2: StudentAgent
    ) -> float:
        """Calculate interaction probability using the homophily rule."""
        similitud = estudiante_1.calcular_similitud(estudiante_2)
        probabilidad = self.probabilidad_base_interaccion + similitud * self.peso_homofilia

        return min(1.0, round(probabilidad, 3))

    def hay_clase(self, dia: str) -> bool:
        """Check whether the course meets on a given day name."""
        return dia.lower() in self.dias_clase

    def inscribir_estudiante(self, estudiante: StudentAgent) -> None:
        """Enroll a student if they are not already in the course."""
        if estudiante.id not in {actual.id for actual in self.estudiantes}:
            self.estudiantes.append(estudiante)


def crear_curso_base(estudiantes: list[StudentAgent]) -> CourseEnvironment:
    """Create the initial shared course for the MVP."""
    return CourseEnvironment(
        nombre_curso="Introduccion a la Programacion",
        estudiantes=estudiantes,
    )
