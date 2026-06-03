"""Entry point for the behavioral homophily MVP."""

from environment import crear_curso_base
from network_analysis import (
    calcular_metricas_red,
    construir_red_interacciones,
    exportar_metricas_red,
)
from simulation import exportar_interacciones, generar_agentes, simular_dias
from visualization import visualizar_red


def main() -> None:
    """Run the MVP pipeline."""
    print("Simulacion iniciada")

    agentes = generar_agentes(cantidad=10, semilla=42)
    print(f"Agentes creados: {len(agentes)}")

    curso = crear_curso_base(agentes)
    print(f"Curso creado: {curso.nombre_curso}")

    registros_interaccion = simular_dias(
        curso,
        duracion_dias=7,
        semilla=123,
    )

    red = construir_red_interacciones(agentes, registros_interaccion)
    metricas = calcular_metricas_red(red)
    print("Red final generada")

    for nombre, valor in metricas.items():
        print(f"{nombre}: {valor}")

    ruta_interacciones = exportar_interacciones(registros_interaccion)
    ruta_metricas = exportar_metricas_red(metricas)
    ruta_visualizacion = visualizar_red(red)

    print(f"Interacciones guardadas: {ruta_interacciones}")
    print(f"Metricas guardadas: {ruta_metricas}")
    print(f"Visualizacion guardada: {ruta_visualizacion}")


if __name__ == "__main__":
    main()
