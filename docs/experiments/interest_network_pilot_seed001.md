# Prueba de intereses y vínculos fuertes: semilla 1

Fecha: 3 de noviembre de 2026. Se reconstruyeron resultados de tres
corridas ya guardadas en `outputs/expressed-tone-v1-scenarios/`, una para
cada nivel de homofilia. No se repitió la simulación ni se llamó a una API.
Cada corrida contiene 80 estudiantes, diez semestres y 50 400 oportunidades
de respuesta. Los derivados están en
`outputs/expressed-tone-v1-scenarios/interest_network_pilot_seed001/`.

## Intereses compartidos y respuesta

La coincidencia exige al menos una etiqueta de interés idéntica entre
iniciador y estudiante expuesto. La tasa es respuestas divididas entre
exposiciones del grupo, y la diferencia se expresa en puntos porcentuales.

| Homofilia | Sin interés compartido | Con interés compartido | Diferencia |
| --- | ---: | ---: | ---: |
| Baja, 0.20 | 26.27 % | 27.06 % | +0.79 pp |
| Media, 0.50 | 30.82 % | 32.92 % | +2.09 pp |
| Alta, 0.80 | 35.69 % | 39.30 % | +3.61 pp |

Los tres mapas de calor desglosan las oportunidades y respuestas por
categoría de interés del iniciador y del expuesto. Las celdas reparten
fraccionalmente cada oportunidad entre las categorías que poseen ambos
estudiantes; el total ponderado permanece en 50 400 por corrida. El mapa
incluye también la tasa de respuesta condicionada a la exposición.

## Red de evaluaciones y vínculos fuertes

El umbral configurado es `R >= 0.70`. Las aristas observadas pertenecen a
la red histórica de evaluaciones; las aristas fuertes son solo el subconjunto
que supera el umbral. Un par fuerte recíproco exige ambas direcciones.

| Homofilia | Semestre | Aristas observadas | Aristas fuertes dirigidas | Pares fuertes recíprocos |
| --- | ---: | ---: | ---: | ---: |
| Baja | 1 | 3483 | 6 | 0 |
| Baja | 5 | 6187 | 220 | 18 |
| Baja | 10 | 6313 | 561 | 84 |
| Media | 1 | 3528 | 6 | 0 |
| Media | 5 | 6220 | 212 | 17 |
| Media | 10 | 6318 | 521 | 78 |
| Alta | 1 | 3591 | 6 | 0 |
| Alta | 5 | 6204 | 227 | 19 |
| Alta | 10 | 6317 | 561 | 98 |

Al cierre, la densidad de evaluaciones se aproxima a 1 porque casi todos
los pares dirigidos fueron observados al menos una vez. La densidad de
aristas **fuertes** es 0.0888, 0.0824 y 0.0888 para homofilia baja, media y
alta, respectivamente. La densidad de pares **fuertes recíprocos** es
0.0266, 0.0247 y 0.0310. Así, el umbral recupera contraste estructural que
la densidad histórica saturada ya no muestra. El número de aristas fuertes
dirigidas no aumenta monótonamente con la homofilia en esta semilla.

## Archivos y comprobación

Se generaron tres PNG de mapas de calor, diez PNG de red por escenario,
`strong_ties_trajectory.png` y CSV con matriz de intereses, coincidencia,
progresión semestral, resumen por escenario y diferencias pareadas. El
directorio ocupa aproximadamente 12 MB. Se comprobó que las 30 filas
semestrales están presentes, que cada escenario tiene diez imágenes de red,
que los conteos ponderados coinciden con exposiciones y respuestas, y que
las densidades corresponden a 6320 pares dirigidos y 3160 pares no dirigidos
posibles entre 80 estudiantes.

Esta prueba usa **una sola semilla**. Los intervalos de confianza entre
semillas no están definidos y las diferencias observadas no deben
interpretarse como un patrón estable hasta procesar las demás corridas.
