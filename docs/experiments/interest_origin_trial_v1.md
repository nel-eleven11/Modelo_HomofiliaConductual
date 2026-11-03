# Prueba conjunta de homofilia y pesos de similitud

Diseño autorizado: una corrida completa de diez semestres por escenario,
con la semilla compartida 1, cohorte de 80 agentes y generación local de
lenguaje y tono. Se usa la configuración de tono `interest_conditioned`
vigente y se guarda todo en `outputs/interest-origin-trial-v1-seed001/`.

| Escenario | h | w_I | w_A | w_S | w_P |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baja | 0.20 | 0.30 | 0.25 | 0.25 | 0.20 |
| Media | 0.50 | 0.50 | 0.15 | 0.15 | 0.20 |
| Alta | 0.80 | 0.70 | 0.05 | 0.05 | 0.20 |

Los pesos suman uno en cada escenario. El remanente tras fijar `w_I` y
`w_P` se reparte por igual entre edad y sexo. Las configuraciones completas
se guardan en el plan del experimento y en cada directorio de corrida.

```bash
python -m homophily_sim.experiments.runner \
  --seed-count 1 \
  --similarity-weights-file configs/interest_origin_trial_v1.json \
  --output outputs/interest-origin-trial-v1-seed001

python -m homophily_sim.experiments.interest_network_analysis \
  outputs/interest-origin-trial-v1-seed001 --only-seed 1
```

Esta prueba cambia `h` y `w_I` simultáneamente; por ello, una diferencia
entre escenarios no identifica el efecto aislado de la homofilia ni del
peso de intereses. La comparación con el piloto anterior tampoco aísla un
solo peso, porque `w_P`, `w_A` y `w_S` cambian a la vez. Sus resultados son
exploratorios y se deben leer junto con las configuraciones guardadas.

## Ejecución y comprobación

Las tres corridas de la semilla 1 terminaron con 80 agentes, diez semestres
y 7200 conversaciones cada una. Se generaron 3 mapas de calor, 30 imágenes
semestrales de red y 30 filas de progresión de vínculos. Los resultados
locales ocupan aproximadamente 93 MB y se mantienen fuera de Git.
Se comprobaron las configuraciones guardadas, los diez snapshots por
corrida, los conteos de imágenes, las sumas ponderadas de 50 400
exposiciones por escenario y las densidades calculadas sobre 6320 pares
dirigidos y 3160 pares no dirigidos posibles.

## Respuesta e intereses

En la tabla, «ventaja» es la tasa de respuesta entre pares con al menos
una etiqueta de interés idéntica menos la tasa entre pares sin ninguna.
La columna «antes» usa el piloto original con la misma semilla y pesos
de similitud `(0.70, 0.10, 0.10, 0.10)` en todos los escenarios.

| Escenario | Respuesta, antes | Respuesta, ahora | Ventaja de interés, antes | Ventaja de interés, ahora |
| --- | ---: | ---: | ---: | ---: |
| Baja | 27.04 % | 28.23 % | +0.79 pp | +0.50 pp |
| Media | 32.44 % | 33.51 % | +2.09 pp | +2.50 pp |
| Alta | 37.62 % | 37.44 % | +3.61 pp | +3.16 pp |

El promedio de similitud ponderada entre quienes respondieron cambia
por construcción cuando cambian sus pesos; por ello, **no** debe usarse
como comparación directa con el piloto anterior. Para comparar intereses
sin esa confusión se calculó por separado el Jaccard de las etiquetas de
interés entre pares que respondieron en el semestre 10:

| Escenario | Jaccard, antes | Jaccard, ahora |
| --- | ---: | ---: |
| Baja | 0.03355 | 0.02922 |
| Media | 0.03095 | 0.03360 |
| Alta | 0.03378 | 0.03293 |

Los cambios del Jaccard son pequeños y tampoco uniformes. La comparación
de tasas de respuesta condicionadas a exposición es más directamente
interpretable para el mecanismo de participación. En la nueva prueba,
las tasas con y sin interés compartido son 27.74 % frente a 27.25 % en
homofilia baja, 34.53 % frente a 32.04 % en media y 38.53 % frente a
35.38 % en alta.

## Vínculos con umbral 0.70

| Escenario | Semestre | Aristas observadas | Fuertes dirigidas | Pares fuertes recíprocos |
| --- | ---: | ---: | ---: | ---: |
| Baja | 1 | 3494 | 6 | 0 |
| Baja | 5 | 6200 | 210 | 18 |
| Baja | 10 | 6314 | 513 | 73 |
| Media | 1 | 3543 | 5 | 0 |
| Media | 5 | 6213 | 226 | 26 |
| Media | 10 | 6316 | 541 | 79 |
| Alta | 1 | 3585 | 6 | 0 |
| Alta | 5 | 6208 | 224 | 19 |
| Alta | 10 | 6317 | 533 | 92 |

Frente al piloto original, las aristas fuertes dirigidas del semestre 10
cambiaron de 561 a 513 en baja, de 521 a 541 en media y de 561 a 533 en
alta. Los pares recíprocos cambiaron de 84 a 73, de 78 a 79 y de 98 a
92, respectivamente. Las nuevas densidades de aristas fuertes dirigidas
son 0.0812, 0.0856 y 0.0843. Las densidades de pares fuertes recíprocos
son 0.0231, 0.0250 y 0.0291. La red observada vuelve a estar casi
saturada al final, mientras que el filtro de vínculos fuertes conserva
un contraste útil.

Se usó una sola semilla por escenario. Las medias por escenario en los
CSV representan una sola corrida y no tienen intervalos de confianza
entre semillas definidos. Estas diferencias no establecen tendencias
estables ni efectos causales aislados de un parámetro.
