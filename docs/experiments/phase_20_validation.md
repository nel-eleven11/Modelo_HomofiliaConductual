# Fase 20: verificación y validación interna

## Alcance

Esta fase comprueba que la implementación sigue sus reglas declaradas y
examina si los cambios controlados producen las direcciones esperadas. No
calibra pesos con datos de estudiantes ni demuestra validez predictiva o
externa. Las ejecuciones usaron lenguaje y sentimiento simulados, semillas
registradas y las configuraciones completas guardadas en `outputs/`.

## Nivel 1: tests e invariantes

La suite automatizada cubre las ecuaciones de similitud, participación,
evaluación y actualización dirigida, además de asignación de secciones,
calendario, red, persistencia y reproducción por semilla. La auditoría
adicional recorrió las **90 corridas completas** de la fase 18, con
**900 mediciones semestrales y 5 957 451 interacciones dirigidas**.
Comprobó límites `[0,1]` de las variables de interacción, coherencia de
la ecuación de actualización, ausencia de autoevaluaciones, 80 agentes
únicos por corrida y coincidencia entre las últimas actualizaciones y los
pesos de la red guardada. Las 90 redes conservaron al menos un par de
vínculos recíprocos asimétricos. El mayor error numérico observado en la
ecuación de actualización fue `0.0` con la aritmética almacenada. La
auditoría confirmó el proveedor mock en el plan experimental.

Esta auditoría comprueba la consistencia de los resultados guardados;
no equivale a una verificación formal de todos los posibles estados.

## Nivel 2: casos controlados

Se evaluaron siete sondas de ecuaciones y **80 simulaciones de una semana**:
ocho condiciones por diez semillas pareadas (`1` a `10`), con 20 agentes.
La semana pequeña permite observar decisiones estocásticas sin repetir los
10 semestres del experimento principal. Cada corrida guarda su configuración,
semilla, metadatos y resultado. Se examinó `h=0`, `h=1`, intereses iguales
o disjuntos, `alpha_relationship=0`, y extroversión uniforme en `0` o `10`.

Para comparar intereses iguales contra disjuntos se fijó `beta_I=0` en
ambas condiciones, aislando el término de similitud de la probabilidad de
participación. Las edades, sexo, procedencia y orientaciones se mantuvieron
por semilla. Las pruebas de `h` y extroversión conservaron el resto de
parámetros base. Los contrastes son **descriptivos**, no pruebas de
significancia ni estimaciones de efecto en personas.

| Contraste pareado, 10 semillas | Diferencia media | IC descriptivo 95 % | Semillas con dirección positiva |
| --- | ---: | ---: | ---: |
| `h=1` − `h=0`: probabilidad media de participación | +0.13964 | [0.13589, 0.14339] | 10/10 |
| Intereses iguales − disjuntos: similitud media, `beta_I=0` | +0.70000 | [0.70000, 0.70000] | 10/10 |
| Intereses iguales − disjuntos: probabilidad media, `beta_I=0` | +0.16010 | [0.15910, 0.16111] | 10/10 |
| Extroversión 10 − 0: probabilidad media | +0.15512 | [0.15393, 0.15631] | 10/10 |
| Vínculo con `alpha_relationship=0`: desviación máxima de 0.5 | 0 | [0, 0] | 0/10 |

En las sondas puras, `h=0` anuló exactamente el efecto de similitud; al
subir `h` aumentaron los efectos de similitud y relación previa. Con
`alpha_relationship=0`, el vínculo permaneció en 0.5 aun ante evaluaciones
extremas. Extroversión cero conservó una probabilidad positiva de iniciar
por `epsilon_start=0.25`. Las siete sondas y los cinco contrastes cumplieron
sus direcciones declaradas. La tasa real de participación sigue siendo
estocástica; se comprobó la dirección de su **probabilidad media**.

## Nivel 3: contraste con literatura

[McPherson, Smith-Lovin y Cook (2001)](https://www.annualreviews.org/content/journals/10.1146/annurev.soc.27.1.415)
describen la homofilia como una pauta de relaciones entre personas similares
y subrayan el papel del contexto de contacto y la disolución diferencial de
vínculos. [Kossinets y Watts (2009)](https://www.journals.uchicago.edu/doi/10.1086/599247)
encuentran en una comunidad universitaria que los pares similares tienen
mayor propensión a formar vínculos, pero que el cierre triádico y las
oportunidades de contacto también restringen la formación. En una cohorte
universitaria observada en Facebook,
[Wimmer y Lewis (2010)](https://www.journals.uchicago.edu/doi/abs/10.1086/653658)
distinguen la homofilia de mecanismos como reciprocidad y proximidad.

El mecanismo local del modelo es **compatible en dirección** con la
preferencia por similitud: subir `h` aumenta su aporte a la probabilidad,
y el experimento pareado de fase 18 obtuvo más interacciones y más densidad
temprana. Sin embargo, el modelo **no reprodujo una separación fuerte por
similitud entre escenarios al final**: las redes alcanzaron densidades
`0.9994–0.9997`, y la diferencia final de similitud media de extremos
entre `h=0.80` y `h=0.20` fue `0.0000088`, con intervalo
`[-0.0000003, 0.0000179]`. Sexo y procedencia tampoco mostraron una
separación final apreciable.

La comparación con esos artículos es cualitativa. Sus poblaciones, tipos
de vínculo y mecanismos no son equivalentes a los de esta cohorte
sintética. Este modelo acumula aristas sin eliminarlas y no implementa
cierre triádico explícito; esos mecanismos ausentes limitan la comparación.
No se ajustó ningún peso para imitar resultados externos. La saturación
de la red es un hallazgo interno que debe acompañar cualquier afirmación
sobre homofilia emergente.

## Nivel 4: estabilidad entre semillas

Se reutilizaron las **30 semillas compartidas** de los tres escenarios
completos. `seed_stability.csv` da media, desviación estándar, rango e
intervalo por escenario, semestre y métrica. Por ejemplo, en el primer
semestre la densidad media y desviación estándar fueron `0.5625 ± 0.0068`
para `h=0.20` y `0.5816 ± 0.0069` para `h=0.80`. La diferencia pareada
`h=0.80 − h=0.20` fue positiva en **30/30** semillas, media `0.01905`
e intervalo `[0.01840, 0.01971]`.

En el semestre 10, la diferencia de densidad fue positiva en 17 semillas,
negativa en 10 e igual a cero en 3; la saturación hace que esa comparación
sea menos estable. El peso medio final fue mayor con `h=0.80` en 30/30
semillas (diferencia media `0.002457`). La similitud media final fue mayor
en 19 y menor en 11; su intervalo pareado incluye cero. Por tanto, el
signo del resultado de similitud final no es estable entre semillas.

## Archivos y reproducción

```bash
python -m homophily_sim.experiments.validation
```

En `outputs/phase-20-validation/` quedan `validation_summary.json`,
`logical_probes.csv`, `controlled_runs.csv`, `controlled_contrasts.csv`,
`seed_stability.csv`, `paired_seed_signs.csv` y las 80 carpetas
`runs/` con configuración y metadatos. El archivo
`outputs/phase-20-validation-summary.zip` reúne las tablas, el resumen y
este informe; las carpetas individuales permanecen fuera del ZIP.
Las huellas SHA-256 de los insumos principales están en el resumen JSON.
`outputs/` está excluido de Git.
