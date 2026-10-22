# Fase 19: sensibilidad local de parámetros

## Diseño y reproducibilidad

Se ejecutaron 225 simulaciones completas: tres escenarios de homofilia
(`h = 0.20, 0.50, 0.80`), cinco semillas pareadas (`1` a `5`) y 15
configuraciones por escenario (una base y dos cambios para cada uno de los
siete parámetros). Cada simulación siguió a 80 agentes sintéticos durante
10 semestres. Hay 2250 registros semestrales.

Se modificó **un parámetro por vez** dentro de cada escenario. Los valores
probados fueron:

| Parámetro | Bajo | Base | Alto |
| --- | ---: | ---: | ---: |
| `alpha_relationship` | 0.10 | 0.20 | 0.40 |
| `w_interest` | 0.50 | 0.70 | 0.80 |
| `beta_I` | 1.00 | 1.40 | 1.80 |
| `beta_E` | 0.40 | 0.80 | 1.20 |
| `beta_R` | 0.30 | 0.60 | 0.90 |
| `w_agreement` | 0.60 | 0.75 | 0.90 |
| `gamma_section` | 0.25 | 0.50 | 0.75 |

Al variar `w_interest` se reescalaron proporcionalmente `w_age`, `w_sex` y
`w_origin`, conservando la suma unitaria. Al variar `w_agreement`, se fijó
`w_sentiment = 1 - w_agreement`. Todos los demás parámetros permanecieron
en su valor base. Se usaron proveedores simulados de lenguaje y sentimiento,
sin llamadas API. El plan congelado registra las semillas, configuraciones,
versiones y huellas SHA-256 de los insumos. Revisión de la implementación
usada para ejecutar el experimento:
`3a493a767386aad82486eef9459e02301e421440`.

## Resultados observados

La tabla muestra diferencias medias respecto a la configuración base con la
**misma semilla y el mismo `h = 0.50`**. Los intervalos son descriptivos del
95 % basados en cinco diferencias pareadas.

| Parámetro | Cambio bajo / alto: peso medio de vínculos, semestre 10 | Cambio bajo / alto: densidad, semestre 1 |
| --- | ---: | ---: |
| `alpha_relationship` | -0.02831 / +0.01476 | cercano a 0 |
| `w_interest` | +0.00039 / -0.00047 | +0.00263 / -0.00146 |
| `beta_I` | -0.00018 / +0.00057 | -0.00462 / +0.00468 |
| `beta_E` | -0.00103 / +0.00072 | -0.00829 / +0.00867 |
| `beta_R` | -0.00056 / +0.00110 | -0.00636 / +0.00655 |
| `w_agreement` | -0.02184 / +0.02170 | cercano a 0 |
| `gamma_section` | +0.00051 / -0.00034 | 0 / 0 |

El peso medio final responde sobre todo a `alpha_relationship` y
`w_agreement`. Para `alpha_relationship = 0.10`, la diferencia fue
`-0.02831` con intervalo `[-0.02996, -0.02667]`; para
`alpha_relationship = 0.40`, `+0.01476` `[+0.01368, +0.01585]`.
Para `w_agreement = 0.60` fue `-0.02184`
`[-0.02352, -0.02016]`; para `w_agreement = 0.90`, `+0.02170`
`[+0.01952, +0.02389]`. Los otros cambios en este indicador fueron mucho
menores. En el primer semestre, la densidad respondió más a `beta_E`,
`beta_R` y `beta_I`, que actúan en la probabilidad de participación.
`gamma_section` no cambia la asignación del primer semestre, por lo que su
efecto allí es exactamente cero. Las figuras incluyen los tres valores de
`h` y los intervalos para cada parámetro.

Las medias base de densidad en el semestre 1 fueron `0.5608`, `0.5701` y
`0.5798` para `h = 0.20`, `0.50` y `0.80`, respectivamente. En el semestre
10 estuvieron entre `0.9992` y `0.9997`: la red casi completa reduce la
capacidad de la densidad, las comunidades y la modularidad para distinguir
efectos tardíos. Cinco semillas permiten una lectura exploratoria, pero no
una conclusión robusta sobre todos los parámetros ni sobre estudiantes reales.
Los intervalos no tienen corrección por comparaciones múltiples.

## Similitud de extremos con una escala fija

`mean_edge_similarity` usa los pesos de similitud de **cada configuración**.
Por eso, al cambiar `w_interest`, su diferencia frente a la base incorpora
un cambio en la propia regla de medición. Para comparar la composición de
aristas se recalculó la similitud de todos los extremos con los pesos base
fijos (`0.70, 0.10, 0.10, 0.10`) y la misma población guardada de cada
corrida. La métrica base recalculada coincide con la original, con error
máximo de `5.55e-17`.

Con `h = 0.50`, el cambio fijo para `w_interest = 0.50` fue `+0.000079`
`[-0.000068, +0.000227]` en el semestre 1 y `+0.000020`
`[-0.000013, +0.000052]` en el semestre 10. Para `w_interest = 0.80`
fue `-0.000070` `[-0.000210, +0.000071]` y `+0.000018`
`[-0.000025, +0.000061]`, respectivamente. Estos resultados no muestran
una diferencia clara en la composición de aristas para esas variaciones.
La figura de similitud usa esta escala fija; los CSV de sensibilidad
originales conservan la métrica calculada con los pesos de cada corrida.

## Archivos y reproducción

En `outputs/phase-19-sensitivity/` se guardan:

- `sensitivity_plan.json`: diseño y huellas de los insumos.
- `runs/`: 225 carpetas con configuración, metadatos, agentes,
  interacciones, relaciones y métricas de cada corrida.
- `run_inventory.csv` y `run_metrics.csv`: inventario y 2250 mediciones.
- `sensitivity_summary.csv`/`.json` y `paired_deltas.csv`: resúmenes e
  intervalos por escenario, parámetro, semestre y métrica.
- `fixed_similarity_by_run.csv`, `fixed_similarity_summary.csv` y
  `fixed_similarity_paired_deltas.csv`: comparación de aristas con pesos
  base fijos.
- `sensitivity_relationship.png`, `sensitivity_density_early.png` y
  `sensitivity_similarity_early.png`: cambios pareados con intervalos del
  95 % en los tres escenarios.

Los archivos de resumen y las figuras también están en
`outputs/phase-19-sensitivity-summary.zip`; las corridas completas siguen
en `runs/`. `outputs/` está excluido de Git, mientras que este documento
preserva el diseño y las cifras principales.

```bash
python -m homophily_sim.experiments.sensitivity
python scripts/analyze_phase19_reference.py
python scripts/plot_phase19.py
```

La primera orden reanuda las corridas existentes si coincide el plan
congelado. Las dos últimas regeneran las tablas de escala fija y las
figuras desde los datos guardados.
