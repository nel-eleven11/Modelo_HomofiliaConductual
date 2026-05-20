"""Student agent definitions for the behavioral homophily MVP."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StudentAgent:
    """Represents a student in the behavioral homophily simulation."""

    id: int
    nombre: str
    edad: int
    genero: str
    carrera: str
    semestre: int
    gustos: list[str]
    extroversion: float
    responsabilidad: float
    conexiones_sociales: list[int] = field(default_factory=list)

    def calcular_similitud(self, otro: "StudentAgent") -> float:
        """Calculate a simple homophily score between 0.0 and 1.0."""
        puntajes = [
            self._similitud_gustos(otro),
            1.0 if self.carrera == otro.carrera else 0.0,
            self._similitud_semestre(otro),
            1.0 if self.genero == otro.genero else 0.0,
            self._similitud_extroversion(otro),
        ]

        return round(sum(puntajes) / len(puntajes), 3)

    def comparar_con(self, otro: "StudentAgent") -> dict[str, object]:
        """Return the main comparison values used by the similarity score."""
        gustos_compartidos = sorted(set(self.gustos).intersection(otro.gustos))

        return {
            "agente_1": self.id,
            "agente_2": otro.id,
            "gustos_compartidos": gustos_compartidos,
            "misma_carrera": self.carrera == otro.carrera,
            "mismo_semestre": self.semestre == otro.semestre,
            "mismo_genero": self.genero == otro.genero,
            "diferencia_extroversion": abs(self.extroversion - otro.extroversion),
            "similitud": self.calcular_similitud(otro),
        }

    def registrar_interaccion(self, otro: "StudentAgent") -> None:
        """Register a social connection with another student."""
        if otro.id == self.id:
            return

        if otro.id not in self.conexiones_sociales:
            self.conexiones_sociales.append(otro.id)

    def _similitud_gustos(self, otro: "StudentAgent") -> float:
        gustos_propios = set(self.gustos)
        gustos_otro = set(otro.gustos)

        if not gustos_propios and not gustos_otro:
            return 1.0

        union = gustos_propios.union(gustos_otro)
        interseccion = gustos_propios.intersection(gustos_otro)

        return len(interseccion) / len(union)

    def _similitud_semestre(self, otro: "StudentAgent") -> float:
        diferencia = abs(self.semestre - otro.semestre)
        return max(0.0, 1.0 - diferencia / 10)

    def _similitud_extroversion(self, otro: "StudentAgent") -> float:
        diferencia = abs(self.extroversion - otro.extroversion)
        return max(0.0, 1.0 - diferencia)
