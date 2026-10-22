# Fase 18: comparación de escenarios de homofilia

## Diseño reproducible

- 80 agentes sintéticos durante 10 semestres en cada corrida.
- 30 semillas (`1` a `30`) compartidas entre `h = 0.20`, `0.50` y `0.80`:
  90 corridas completas y 900 registros semestrales.
- Solo cambian `h` y el nombre del escenario. Cada corrida guarda su
  configuración, metadatos, interacciones y métricas de 10 semestres.
- Lenguaje y sentimiento simulados; sin llamadas API. Los insumos y el código
  del modelo tienen huellas SHA-256 en `experiment_plan.json`.
- Revisión que generó las corridas: `768e93c76561c32ef2eca9199e00f4ca7fb41207`.

## Resultados observados

| Indicador, media de 30 semillas | h=0.20 | h=0.50 | h=0.80 |
| --- | ---: | ---: | ---: |
| Interacciones por corrida | 63 809 | 66 120 | 68 653 |
| Densidad, semestre 1 | 0.5625 | 0.5719 | 0.5816 |
| Reciprocidad, semestre 1 | 0.7623 | 0.7825 | 0.8028 |
| Peso medio de vínculos, semestre 10 | 0.6059 | 0.6071 | 0.6084 |
| Densidad, semestre 10 | 0.9995 | 0.9994 | 0.9997 |
| Similitud media de aristas, semestre 10 | 0.212293 | 0.212293 | 0.212302 |
| Comunidades, semestre 10 | 1 | 1 | 1 |
| Modularidad, semestre 10 | 0 | 0 | 0 |
| Aislados, semestre 10 | 0 | 0 | 0 |

Con las mismas semillas pareadas, la diferencia `h=0.80 − h=0.20` en densidad
media fue `0.01905` en el primer semestre, con intervalo descriptivo del 95 %
`[0.01840, 0.01971]`. Al décimo semestre se redujo a `0.000185`
`[0.000014, 0.000355]` porque las redes están casi completas. La diferencia
final de peso medio de vínculos fue `0.002457` `[0.001991, 0.002923]`.
La diferencia final de similitud media de aristas fue `0.0000088`, con intervalo
`[-0.0000003, 0.0000179]`, que incluye cero. Las assortatividades por sexo y
procedencia tampoco muestran una separación apreciable entre escenarios al
finalizar.

El modelo produce más interacciones y vínculos algo más altos al aumentar `h`.
La red casi completa limita la utilidad de densidad, comunidades y modularidad
en los últimos semestres. Estos resultados no demuestran una mayor similitud
final entre los extremos de las aristas. Las cifras describen las reglas y
parámetros operacionales de un modelo exploratorio, no estudiantes reales.

Los intervalos se calcularon con la distribución t de Student y desviación
estándar muestral. Para cada diferencia final se restaron resultados de la
misma semilla; no se usaron pares de semillas distintas. Son resúmenes
descriptivos, sin ajuste por comparaciones múltiples. El detalle de medias,
desviaciones estándar, medianas, tamaños de muestra e intervalos para cada
métrica y semestre está en los CSV.

## Archivos para análisis y presentación

En `outputs/phase-18-scenarios/` están:

- `experiment_plan.json`: semillas, parámetros, versiones y huellas de insumos.
- `runs/`: 90 carpetas con configuración, metadatos, agentes, interacciones,
  relaciones y métricas semestrales de cada corrida.
- `run_inventory.csv` y `run_metrics.csv`: conteos y métricas por corrida.
- `scenario_summary.csv`: estadísticos e intervalos por escenario y semestre.
- `paired_final_differences.csv`: 30 resúmenes de diferencias pareadas al
  décimo semestre.
- `community_size_distribution.csv`: frecuencia de tamaños de comunidades.
- `experiment_summary.json` y `report.md`: agregados en formatos reutilizables.
- `density_by_scenario.png`, `relationship_by_scenario.png` y
  `similarity_by_scenario.png`: trayectorias con bandas de confianza.

`outputs/phase-18-scenarios-summary.zip` contiene las tablas agregadas, el
informe y las figuras para la presentación. Las 90 carpetas completas quedan
en `outputs/phase-18-scenarios/runs/` y no están dentro de ese ZIP resumido.
`outputs/` está excluido de Git; este documento conserva las cifras clave.
