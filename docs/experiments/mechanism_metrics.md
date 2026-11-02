# Métricas de mecanismos de interacción

## Unidad y orden de observación

Una **oportunidad** es un estudiante expuesto al mensaje inicial de una
conversación. Se guarda una fila en `participation_attempts.parquet` por
oportunidad, haya respuesta o no. Primero se lee el vínculo dirigido del
expuesto hacia el iniciador y se calcula la probabilidad de responder; después
se decide por Bernoulli. Luego el expuesto evalúa el mensaje inicial y se
actualiza ese vínculo. Si responde, el iniciador evalúa la respuesta y
actualiza el vínculo en la dirección contraria. No cambian las ecuaciones de
participación ni de actualización.

`interactions.parquet` guarda una fila por **evaluación dirigida**: todas las
exposiciones y también las respuestas. Por tanto, en cada semestre:

`directed_evaluation_count = exposure_count + response_count`.

La tasa de participación es `response_count / exposure_count`. Los iniciadores
se cuentan por conversación, los respondedores únicos por identificador de
agente y los estudiantes activos únicos como la unión de ambos grupos.

## Comparación de mecanismos

Los promedios `mean_exposed_*` usan todas las oportunidades. Los
`mean_responding_*` usan solo oportunidades con `participated=True`. Los
`mean_evaluation_*` usan todas las evaluaciones dirigidas; las respuestas
cuentan como evaluaciones adicionales. El vínculo previo de una oportunidad
es exactamente el valor utilizado para decidir la respuesta; no incorpora el
cambio producido por evaluar ese mismo mensaje.

Las tasas `repeated_unordered_exposure_rate` y
`repeated_unordered_response_rate` consideran repetido un par no dirigido
cuando tuvo una exposición o respuesta previa, respectivamente, en cualquier
semestre anterior de la misma corrida o antes en el mismo semestre. La cuota
del 10 % de pares más frecuentes se calcula dentro de cada semestre sobre
pares distintos de ese semestre; se selecciona `ceil(0.1 * pares_distintos)`.

`strengthened_evaluation_updates`, `weakened_evaluation_updates` y
`unchanged_evaluation_updates` clasifican cada diferencia
`relationship_after - relationship_before` con tolerancia `1e-9`. La suma de
los tres conteos es `directed_evaluation_count`.

## Persistencia y redes

La red principal continúa siendo la **red de evaluaciones**. Una arista
`observador -> emisor` existe después de la primera evaluación dirigida de
ese par. El valor inicial neutral de una relación potencial no crea arista.
Las métricas históricas (`density`, `modularity`, etc.) conservan esta red y
sus definiciones.

La red complementaria de **respuestas activas** contiene una arista de flujo
de mensaje `respondedor -> iniciador`; su peso es el número acumulado de
respuestas del par dirigido. Sus métricas nuevas tienen prefijo
`active_response_`. Ambas redes se exportan por semestre en GraphML. La
comunidad asignada a cada nodo en ambos archivos proviene de la red principal
al cierre de ese semestre.

`evaluation_activity_persistence_rate` compara los pares dirigidos que
evaluaron mensajes en dos semestres consecutivos. Su denominador son los
pares activos en el semestre previo. `response_activity_persistence_rate`
aplica la misma regla a pares dirigidos de respuesta. Estas tasas son `null`
si no hay pares activos en el semestre previo.

Un vínculo fuerte es una arista de evaluación observada cuyo peso al cierre
del semestre es al menos `strong_relationship_threshold`, registrado en
`config.json` (valor inicial 0.70). La
`strong_relationship_persistence_rate` compara las aristas fuertes en dos
cierres consecutivos; es `null` si antes no había vínculos fuertes. Ese
umbral es una convención analítica, no una definición de amistad.

Las tasas `between_community_evaluation_rate` y
`between_community_response_rate` usan la partición de la red principal al
**cierre del semestre anterior**. En el primer semestre se usa la partición
de su propio cierre solo para describir los contactos y la fila se marca con
`community_mixing_descriptive_only=True`. Las comunidades se calculan sobre
una proyección no dirigida y no ponderada, igual que la métrica histórica.

## Archivos y reconstrucción

Además de `run_metrics.csv`, cada corrida guarda `interaction_summary.csv`,
`relationship_evolution.csv`, `topic_summary.csv`, `student_activity.csv`,
`topic_bank.json` y dos familias de snapshots GraphML. Los agregados por
escenario y las diferencias pareadas usan las mismas semillas y la función
descriptiva existente. Los indicadores sin denominador se guardan como `null`
y no entran en las diferencias de ese semestre.

La reconstrucción lee `config.json`, `run_metadata.json`, agentes,
`participation_attempts.parquet`, `interactions.parquet`, las métricas de red
históricas y la copia del banco de temas. No invoca al proveedor de lenguaje:

```bash
python -m homophily_sim.experiments.rebuild_mechanisms outputs/mechanism-scenarios
```

Las corridas históricas que no tienen `participation_attempts.parquet` no
pueden reconstruir con garantía las decisiones individuales de participación
y se conservan como resultados de la versión anterior.
