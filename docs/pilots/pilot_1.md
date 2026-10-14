# Piloto 1: escenario de homofilia media

## Configuración y alcance

- Cohorte sintética: 20 agentes; semilla: 42; `h = 0.50`.
- Dos semanas simuladas: una en el primer semestre y otra en el segundo.
- Lenguaje: proveedor simulado; sentimiento: modelo local multilingüe
  `cardiffnlp/twitter-xlm-roberta-base-sentiment`.
- Las reglas sociales usan los parámetros de `configs/homophily_medium.yaml`,
  con el tamaño y la duración reducidos por el modo piloto. No se ajustó
  ningún parámetro tras examinar estos resultados.

## Métricas observadas

| Indicador | Resultado |
| --- | ---: |
| Conversaciones principales | 72 |
| Exposiciones | 144 |
| Participantes que respondieron | 45 |
| Tasa de participación | 31.25 % |
| Evaluaciones dirigidas de mensajes | 189 |
| Probabilidad de participación media | 0.3004 |
| Probabilidad mediana | 0.2513 |
| Probabilidad mínima / máxima | 0.1702 / 0.5972 |
| Relación después de evaluar un mensaje, media | 0.5345 |
| Peso medio de los vínculos finales | 0.5345 |
| Vínculos finales saturados (≤0.01 o ≥0.99) | 0 |
| Generaciones de texto simulado | 117 |
| Llamadas y costo de API LLM | 0 / USD 0 |
| Comprobaciones de coherencia | 14 de 14 correctas |
| Errores detectados | 0 |

| Semestre | Aristas dirigidas | Densidad | Aislados | Peso medio |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 80 | 0.2105 | 0 | 0.5398 |
| 2 | 144 | 0.3789 | 0 | 0.5345 |

La participación quedó entre los casos extremos previstos en el plan: hubo
respuestas sin participación universal, las relaciones permanecieron dentro
de `[0, 1]` sin saturarse y la red ganó aristas sin hacerse completa. Los
registros de conversaciones, exposiciones, respuestas e interacciones
coincidieron en las comprobaciones automáticas.

Estas cifras describen una sola ejecución exploratoria con datos sintéticos;
no son una estimación de estudiantes reales ni una prueba de sensibilidad.
La tasa de participación y las métricas de red pueden cambiar con otras
semillas o parámetros.

## Archivos para reutilizar

La ejecución final queda en `outputs/pilot-1-medium-seed-42-final/`:

- `pilot_1_summary.json`: todas las métricas y comprobaciones del piloto.
- `pilot_1_network_metrics.csv`: indicadores por semestre para gráficos.
- `pilot_1_conversations.csv`: iniciadores, temas, exposiciones,
  participantes y probabilidades por conversación.
- `pilot_1_report.md`: resumen breve para lectura o diapositivas.
- `metrics_by_semester.json`: métricas de red detalladas.
- `config.json` y `run_metadata.json`: parámetros, semilla y versiones.
- `agents.parquet`, `interactions.parquet` y `relationships.parquet`: estado
  final, interacciones y vínculos dirigidos.
- `network_final.png`, `network_semester_01.png`, `network_semester_02.png`,
  `density_over_time.png`, `assortativity_over_time.png`,
  `modularity_over_time.png` y `relationship_distribution.png`: figuras.

La carpeta `outputs/` está excluida de Git. Para conservar los datos y las
figuras fuera de este equipo, copie la carpeta de la ejecución final. Este
documento versionado conserva las cifras principales en el repositorio.
