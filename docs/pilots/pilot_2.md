# Piloto 2: cohorte completa durante un semestre

## Configuración y alcance

- Ejecución: `outputs/pilot-2-medium-seed-42-final/`.
- Revisión del código usada: `700d2cb4cbef7fa438d38de4723e77da068a8ac4`.
- Escenario de homofilia media (`h = 0.50`), semilla 42.
- 80 agentes sintéticos y las 20 semanas del primer semestre.
- Lenguaje y sentimiento simulados durante toda la simulación; 0 solicitudes
  LLM para la red. No se ajustaron parámetros tras revisar el piloto.
- La configuración guardada describe el horizonte de 10 semestres del modelo;
  el resumen registra el semestre efectivamente ejecutado.

## Resultados observados

| Indicador | Resultado |
| --- | ---: |
| Tiempo de simulación | 0.54 s |
| Pico RSS del proceso | 246.5 MiB |
| Conversaciones principales | 720 |
| Exposiciones | 5 040 |
| Respuestas | 1 513 |
| Tasa de participación | 30.02 % |
| Interacciones dirigidas | 6 553 |
| Aristas dirigidas al fin del semestre | 3 622 |
| Densidad de la red | 0.5731 |
| Reciprocidad | 0.7846 |
| Modularidad | 0.0570 |
| Similitud media en los extremos de aristas | 0.2140 |

El tiempo cubre la simulación y el cálculo de su instantánea semestral; excluye
la exportación de archivos y las figuras. El pico RSS es el del proceso Python
en Linux, incluidas las bibliotecas cargadas, y puede variar entre máquinas.
Estas cifras proceden de una sola semilla; no estiman variabilidad entre
réplicas ni representan estudiantes reales.

## Muestra independiente de Gemini

Se generaron cinco mensajes a partir de agentes y temas de la corrida guardada
con `gemini-3.5-flash-lite`. Se leyó cada solicitud una segunda vez para medir
la caché.

| Indicador | Resultado |
| --- | ---: |
| Solicitudes lógicas al SDK | 5 |
| Aciertos de caché local | 5 de 10 lecturas (50 %) |
| Tiempo de la muestra | 6.87 s |
| Tokens de entrada informados | 850 |
| Tokens de salida informados | 158 |
| Tokens totales informados | 1 008 |

El conteo de solicitudes corresponde a llamadas lógicas al SDK y no incluye
eventuales reintentos HTTP internos. Los mensajes de la muestra no afectaron
las interacciones ni la red. El número de tokens proviene de las respuestas
de la API; no se calculó un costo monetario.

## Archivos conservados

En `outputs/pilot-2-medium-seed-42-final/` están:

- `pilot_2_summary.json` y `pilot_2_report.md`: resumen y lectura breve.
- `weekly_metrics.csv`: conversaciones, exposiciones, respuestas e interacciones
  de cada una de las 20 semanas.
- `network_metrics.json`: métricas detalladas, grados, comunidades, pesos y
  componentes de la instantánea semestral.
- `gemini_probe.json`: solicitudes, tokens y cinco textos de muestra.
- `config.json` y `run_metadata.json`: parámetros, versiones, semilla y commit.
- `agents.parquet`, `interactions.parquet` y `relationships.parquet`: estado
  final y registros completos para análisis posterior.
- `network_semester_01.png` y `relationship_distribution.png`: figuras.

`outputs/` está excluido de Git. El archivo
`outputs/pilot-2-medium-seed-42-final.zip` reúne estos resultados para
transportarlos a la presentación. Este documento conserva las cifras
principales dentro del repositorio.
