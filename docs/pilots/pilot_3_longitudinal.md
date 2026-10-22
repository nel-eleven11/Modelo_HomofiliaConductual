# Piloto longitudinal: 80 agentes durante 10 semestres

## Configuración congelada

- Ejecución: `outputs/pilot-3-longitudinal-seed-42/`.
- Revisión de código: `e4b5c39501742ad40c4c90eff5aa9036d45981ce`.
- Semilla 42, escenario de homofilia media (`h = 0.50`).
- 80 agentes sintéticos, 10 semestres, 20 semanas por semestre.
- Lenguaje y sentimiento simulados; ninguna llamada API. La versión activa
  del texto es `mock-v1`. También se registra la huella del archivo de prompts
  de Gemini, aunque ese prompt no interviene en esta corrida.
- `frozen_inputs.json` contiene SHA-256 de la configuración base y del
  escenario, banco de temas, perfil demográfico, generador de texto simulado,
  prompts y analizador de sentimiento simulado. `config.json` conserva todos
  los parámetros y `run_metadata.json` registra versiones de software y datos.

## Resultado y reproducibilidad

| Indicador | Resultado |
| --- | ---: |
| Semestres / años / semanas completados | 10 / 5 / 200 |
| Conversaciones principales | 7 200 |
| Interacciones dirigidas | 66 201 |
| Instantáneas guardadas | 16 (10 semestrales, 5 anuales, 1 final) |
| Tiempo de la primera simulación | 6.89 s |
| Tiempo de la repetición | 7.39 s |
| Pico RSS antes de la repetición | 430.5 MiB |
| Agentes al finalizar | 80 |
| Aristas dirigidas finales | 6 317 de 6 320 posibles |
| Densidad final | 0.9995 |

La repetición con la misma semilla produjo huellas SHA-256 idénticas para el
estado de los agentes, los registros de interacciones y todas las instantáneas.
La comparación omite únicamente el identificador propio de cada corrida; la
configuración y la semilla permanecen iguales. Los tiempos y la memoria
dependen del equipo; el pico RSS incluye bibliotecas cargadas por Python.

| Semestre | Aristas dirigidas | Densidad |
| ---: | ---: | ---: |
| 1 | 3 622 | 0.5731 |
| 2 | 5 166 | 0.8174 |
| 3 | 5 814 | 0.9199 |
| 4 | 6 081 | 0.9622 |
| 5 | 6 213 | 0.9831 |
| 6 | 6 267 | 0.9916 |
| 7 | 6 295 | 0.9960 |
| 8 | 6 309 | 0.9983 |
| 9 | 6 314 | 0.9991 |
| 10 | 6 317 | 0.9995 |

La red se vuelve casi completa porque las interacciones crean aristas que
permanecen registradas. Esto limita cuánto pueden distinguir los indicadores
de topología, como densidad y modularidad, en los semestres finales. Es una
observación de este piloto; no se modificaron las reglas ni los parámetros.
La siguiente comparación de escenarios debe examinar también pesos de vínculos
y similitud entre extremos de aristas. Una sola semilla no permite estimar
variación entre réplicas ni inferir resultados para estudiantes reales.

## Archivos conservados

En `outputs/pilot-3-longitudinal-seed-42/` están:

- `longitudinal_summary.json`: conteos, tiempos, memoria y huellas comparadas.
- `frozen_inputs.json`, `config.json`, `run_metadata.json`: insumos,
  parámetros y versiones.
- `snapshot_index.json` y `snapshots/*.parquet`: las 16 instantáneas con sus
  aristas dirigidas y pesos; cada fila del índice indica semestre y nodos.
- `metrics_by_semester.json`: métricas completas de los 10 semestres.
- `agents.parquet`, `interactions.parquet`, `relationships.parquet`: datos
  finales e historial de interacciones.
- `network_final.png`, `density_over_time.png`, `assortativity_over_time.png`,
  `modularity_over_time.png`, `relationship_distribution.png`: figuras.

`outputs/pilot-3-longitudinal-seed-42.zip` agrupa los archivos para conservarlos
fuera de este equipo. `outputs/` está excluido de Git; este documento guarda
las cifras principales en el repositorio.
