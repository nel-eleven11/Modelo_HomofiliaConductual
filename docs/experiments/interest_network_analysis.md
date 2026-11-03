# Intereses y vínculos fuertes desde corridas guardadas

Este análisis es posterior a la simulación y no llama a modelos de lenguaje.
Usa `agents.parquet`, `participation_attempts.parquet`, `config.json`,
`topic_bank.json` y los snapshots GraphML de la red principal de evaluaciones.
Las métricas históricas de densidad y modularidad permanecen intactas.

```bash
python -m homophily_sim.experiments.interest_network_analysis \
  outputs/expressed-tone-v1-scenarios
```

La opción `--image-seed N` elige una semilla presente en los tres escenarios.
De forma predeterminada se usa la menor semilla común. La opción `--output`
permite elegir otro directorio para estos archivos derivados.

## Mapa de calor por corrida

Se guarda una imagen en `interest_network_analysis/heatmaps/` por corrida.
Los ejes son las **categorías de interés del iniciador y del estudiante
expuesto**, no el tema de la conversación. Los tres paneles muestran
exposiciones ponderadas, respuestas ponderadas y respuestas por exposición.
Si un estudiante tiene intereses de varias categorías, cada oportunidad se
reparte entre todas las combinaciones de categorías de ambos agentes. La suma
de las celdas de exposición equivale al total de oportunidades; la suma de
respuestas equivale al total de respuestas. Una celda sin exposiciones no
tiene tasa definida. El archivo `interest_matrix.csv` conserva los valores.

`interest_overlap.csv` contiene una comparación más directa de la hipótesis:
pares con y sin al menos **una etiqueta de interés idéntica**. Para cada
grupo se registran exposiciones, respuestas y su cociente. La tasa
condiciona en haber sido expuesto; los conteos brutos por categoría también
dependen de la composición de la población y del calendario académico.
`interest_overlap_scenario_summary.csv` resume ambas tasas por nivel de
homofilia. `interest_overlap_effect_by_run.csv` guarda la diferencia entre
la tasa con intereses compartidos y la tasa sin ellos en cada corrida;
`interest_overlap_effect_scenario_summary.csv` resume esa diferencia entre
semillas. Una diferencia positiva es compatible con la hipótesis descriptiva,
pero no identifica por sí sola una causa porque la asignación de secciones y
el interés por el tema de cada conversación también influyen.

## Progresión de vínculos

Una arista de evaluación observada es fuerte cuando su peso al cierre del
semestre alcanza `strong_relationship_threshold` de la configuración (0.70
en la base). Se calculan número y densidad de aristas fuertes dirigidas,
fracción de aristas observadas que son fuertes, pares fuertes recíprocos,
altas y bajas respecto al cierre anterior y persistencia de las aristas
fuertes. Un par recíproco requiere que **ambas direcciones** cumplan el
umbral. Se trata de una convención analítica, no de una definición de amistad.

`strong_ties_by_semester.csv` guarda una fila por corrida y semestre.
`strong_ties_scenario_summary.csv` guarda media, desviación, mediana e
intervalo descriptivo de 95 % por escenario y semestre.
`strong_ties_paired_final_differences.csv` compara escenarios con las mismas
semillas al cierre del último semestre. `strong_ties_trajectory.png` muestra
la densidad de aristas fuertes y pares recíprocos por semestre.

La carpeta `networks/` contiene diez imágenes semestrales **solo para una
corrida por escenario**. Las posiciones de los 80 estudiantes permanecen
fijas dentro de cada escenario; gris indica un vínculo fuerte en una sola
dirección y naranja un par fuerte recíproco. Las imágenes se pueden regenerar
desde los GraphML sin volver a correr la simulación. No se generan imágenes
semestrales para las demás semillas.
