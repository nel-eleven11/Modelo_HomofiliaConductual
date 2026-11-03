# Batería de 90 corridas con tono expresado v1

Fecha de ejecución: 2 de noviembre de 2026. Revisión de código:
`75d3524a01ba8d36c83322a506c61adfff8e688e`. Resultados locales en
`outputs/expressed-tone-v1-scenarios/` (ignorados por Git). No hubo llamadas
a Gemini ni uso del clasificador de Transformers.

## Diseño

- Tres escenarios: homofilia baja `h=0.20`, media `h=0.50` y alta `h=0.80`.
- Treinta semillas compartidas, de 1 a 30: 90 corridas completas.
- Cada corrida: 80 estudiantes, 10 semestres, 20 semanas por semestre y
  7,200 conversaciones de sección.
- Regla de tono: `interest_conditioned`, `p0=0.70`, `k=0.40`,
  `w_sentiment=0.25`, `w_agreement=0.75`.
- El resto de parámetros está en `experiment_plan.json` y en cada
  `runs/<run_id>/config.json`.

## Integridad y alcance

`validation_90_runs.json` registra una auditoría satisfactoria de los 90
directorios: 900 filas semestrales únicas, 30 corridas por escenario, diez
semestres por corrida, archivos de mensajes, exposiciones, evaluaciones,
resúmenes y grafos presentes. La auditoría comprobó los conteos y que cada
evaluación enlaza un mensaje guardado con la misma valencia.

| Registro | Total |
| --- | ---: |
| Conversaciones | 648,000 |
| Mensajes únicos | 2,069,992 |
| Exposiciones | 4,536,000 |
| Respuestas activas | 1,421,992 |
| Evaluaciones dirigidas | 5,957,992 |

Las tasas observadas de tono neutral por interés del emisor fueron 69.94 %
para interés 0, 49.98 % para 0.5 y 29.98 % para 1, cercanas a las
probabilidades configuradas de 70 %, 50 % y 30 %. Los tonos positivos y
negativos mantuvieron proporciones similares en cada nivel de interés.

## Resultados descriptivos del semestre 10

Cada celda es la media de 30 corridas. Las definiciones completas y los
intervalos de confianza están en `scenario_summary.csv`.

| Métrica | h=0.20 | h=0.50 | h=0.80 |
| --- | ---: | ---: | ---: |
| Tasa de participación | 0.2712 | 0.3186 | 0.3714 |
| Similitud de pares que respondieron | 0.2143 | 0.2152 | 0.2166 |
| Vínculo previo de pares que respondieron | 0.6095 | 0.6112 | 0.6132 |
| Repetición de respuestas entre pares | 0.9725 | 0.9848 | 0.9908 |
| Permanencia de vínculos fuertes | 0.7353 | 0.7219 | 0.7145 |
| Densidad de la red de evaluaciones | 0.9993 | 0.9995 | 0.9996 |
| Modularidad | 0 | 0 | 0 |

La diferencia pareada alta menos baja al cierre fue 0.00239 en similitud
de pares que respondieron (IC 95 %: 0.00140 a 0.00339), 0.00377 en vínculo
previo (0.00277 a 0.00477) y 0.01829 en repetición de respuestas
(0.01659 a 0.02000). La permanencia de vínculos fuertes mostró la dirección
contraria: −0.02085 (−0.03115 a −0.01055). Estas son comparaciones del
modelo exploratorio con semillas pareadas; no son estimaciones sobre
estudiantes reales.

## Límite de interpretación

La red principal de evaluaciones se densifica hasta casi completarse.
En el semestre 6, las 90 corridas tienen modularidad cero; en el semestre 10
la densidad media es aproximadamente 0.9995. La tasa de respuestas entre
comunidades es cero en las 90 corridas desde el semestre 5 porque la
partición de referencia del semestre anterior deja de distinguir comunidades.
Por ello, modularidad y mezcla entre comunidades no aportan contraste útil
al final de esta batería. La repetición de respuestas también se aproxima
a uno a medida que se agotan los pares nuevos posibles. No debe presentarse
ninguna de estas tendencias como confirmación de toda la hipótesis.

## Archivos para análisis y presentación

- `run_inventory.csv`: una fila por corrida, con duración de simulación.
- `run_metrics.csv`: 900 filas semestrales individuales.
- `scenario_summary.csv`: medias, dispersión e intervalos por escenario y semestre.
- `paired_final_differences.csv`: contrastes pareados al cierre.
- `interaction_summary.csv`, `relationship_evolution.csv`, `tone_summary.csv`
  y `tone_by_interest.csv`: mecanismos detallados.
- `tone_trends.png`: evolución de tasas y valencias de tono.
- `runs/<run_id>/`: configuración, metadatos, Parquet y grafos GraphML de
  cada corrida para recalcular indicadores sin generar nuevos mensajes.
- `execution.log` y `validation_90_runs.json`: avance e integridad.

El conjunto ocupa aproximadamente 2.5 GB. Los archivos de salida permanecen
fuera de Git; este documento conserva el diseño y los resultados principales.
