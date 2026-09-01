# plan.md

# Plan de implementación por fases

## Objetivo

Construir de forma incremental una simulación basada en agentes en Python para estudiar la evolución de la homofilia conductual en una cohorte sintética de 80 estudiantes durante 10 semestres.

Cada fase debe producir un sistema funcional y verificable.

No completar el proyecto de una sola vez.

---

# Fase 0 — Preparación del repositorio

Estado: completada en el entorno local con CPython 3.14.2.

Verificación: smoke test (1 prueba), `ruff check .`, `mypy`, `pip check`
e importación aislada desde fuera del repositorio satisfactorios. Las versiones
verificadas se registran en `constraints.txt`. La simulación mínima corresponde
a la Fase 8; en Fase 0 se verifica la instalación.

## Objetivo

Dejar un proyecto Python reproducible dentro de `venv`.

## Tareas

1. Crear estructura básica del repositorio.
2. Crear `.gitignore`.
3. Crear `.env.example`.
4. Crear `README.md`.
5. Crear `requirements.txt`.
6. Crear `requirements-dev.txt`.
7. Crear estructura `src/`.
8. Crear estructura `tests/`.
9. Crear carpeta `configs/`.
10. Crear carpetas `data/` y `outputs/`.
11. Configurar pytest.
12. Configurar ruff.
13. Configurar mypy.

## Dependencias iniciales

```text
numpy
pandas
scipy
pydantic
pydantic-settings
python-dotenv
PyYAML
pytest
pytest-cov
ruff
mypy
```

No instalar todavía Gemini, Mesa, NetworkX, matplotlib ni transformers si no se necesitan en esta fase.

## Comandos esperados

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Criterios de aceptación

- entorno virtual funcional;
- paquete importable;
- un smoke test verde;
- no existen secretos versionados.

## Commit sugerido

```text
chore: initialize python project structure
```

---

# Fase 1 — Configuración tipada del modelo

## Objetivo

Centralizar todos los parámetros metodológicos.

## Crear

```text
src/homophily_sim/config.py
configs/base.yaml
configs/homophily_low.yaml
configs/homophily_medium.yaml
configs/homophily_high.yaml
```

## Parámetros base

```text
population_size = 80
years = 5
semesters = 10
weeks_per_semester = 20
days_per_week = 5
courses_per_semester = 6
sessions_per_course_per_week = 2
sections_per_course = 3
exposed_fraction = 0.25

w_interest = 0.70
w_age = 0.10
w_sex = 0.10
w_origin = 0.10

beta_0 = -2.30
beta_E = 0.80
beta_I = 1.40
beta_R = 0.60
lambda_R = 1.00
lambda_S = 1.00

alpha_relationship = 0.20
gamma_section = 0.50

w_agreement = 0.75
w_sentiment = 0.25

epsilon_start = 0.25
initial_relationship = 0.50
```

Escenarios:

```text
low.h = 0.20
medium.h = 0.50
high.h = 0.80
```

## Validaciones

- pesos de similitud suman 1;
- pesos de evaluación suman 1;
- probabilidades y parámetros de mezcla en `[0,1]`;
- población positiva;
- número de secciones válido.

## Tests

Crear tests de carga de YAML y validaciones.

## Commit

```text
feat: add typed simulation configuration
```

---

# Fase 2 — Modelo de dominio

## Objetivo

Crear entidades sin simulación todavía.

## Crear

```text
domain/agent.py
domain/course.py
domain/section.py
domain/topic.py
domain/interaction.py
```

## StudentAgent

Campos principales:

```text
id
age
sex
origin
semester
interests
extraversion
topic_orientations
course_assignments
section_assignments
relationships
```

## Topic

```text
topic_id
category
subcategory
prompt
polarization_level
```

## InteractionRecord

Definir un dataclass/Pydantic model para registrar cada evaluación dirigida.

## Tests

- creación de entidades;
- validaciones de rangos;
- relaciones iniciales en 0.5;
- orientación temática en [-1,1].

## Commit

```text
feat: add core domain models
```

---

# Fase 3 — Banco de temas e intereses

## Objetivo

Crear una taxonomía versionada común para intereses y conversaciones.

## Crear

```text
data/topics/topics_v1.yaml
data/topics/README.md
src/homophily_sim/data/topics.py
```

## Primera versión

Crear entre 30 y 50 temas distribuidos en categorías como:

```text
technology
programming
artificial_intelligence
videogames
sports
music
cinema
anime
literature
science
art
exercise
travel
animals
university_life
```

Preferir polarización baja y media.

## Funciones

```text
load_topics()
validate_topic_bank()
related_categories()
topic_interest_score()
```

## Regla de interés

```text
exact match = 1.0
related category = 0.5
unrelated = 0.0
```

## Tests

- IDs únicos;
- categorías válidas;
- puntuación determinista;
- no existen temas sin categoría.

## Commit

```text
feat: add versioned topic and interest taxonomy
```

---

# Fase 4 — Generación de población sintética

## Objetivo

Crear 80 agentes reproducibles.

## Crear

```text
data/demographics.py
data/population.py
data/demographics/README.md
```

## Demografía

Variables:

```text
age
sex
origin
```

La implementación debe aceptar probabilidades configurables.

No codificar afirmaciones como si fueran distribuciones reales de UVG.

Permitir perfiles:

```text
national_reference
department_reference
custom
```

## Variables sintéticas

### Intereses

- mínimo 1;
- máximo 5;
- distribución truncada configurable.

### Extroversión

- normal truncada en [0,10].

### Orientaciones temáticas

- valores reproducibles en [-1,1];
- usar RNG derivado de la semilla principal.

## Reproducibilidad

La misma semilla debe crear exactamente la misma población.

## Tests

- exactamente 80 agentes;
- IDs únicos;
- intereses 1–5;
- extroversión 0–10;
- misma seed => mismos datos.

## Commit

```text
feat: generate reproducible synthetic student population
```

---

# Fase 5 — Matemática social pura

## Objetivo

Implementar las ecuaciones sin Mesa, red ni LLM.

## Crear

```text
social/similarity.py
social/participation.py
social/evaluation.py
social/relationships.py
```

## Similitud

```text
Sim_ij = 0.70*J
       + 0.10*A
       + 0.10*S
       + 0.10*P
```

Implementar pesos desde config, no hardcodearlos.

## Jaccard

```text
J = intersection / union
```

## Edad

```text
A = 1 - abs(age_i-age_j)/max_age_difference
```

clip `[0,1]`.

## Participación

```text
P_ij = sigmoid(
    beta_0
    + beta_E*E_j
    + beta_I*I_j(T)
    + (beta_R + lambda_R*h)*R_ji
    + lambda_S*h*Sim_ij
)
```

## Acuerdo

```text
A_ij = 1 - abs(O_i(T)-O_j(T))/2
```

## Sentimiento

```text
V = p_positive + 0.5*p_neutral
```

## Evaluación

```text
s_ij = 0.75*A_ij + 0.25*V
```

## Relación

```text
R_new = (1-alpha)*R_old + alpha*s
```

## Tests obligatorios

- todos los resultados acotados;
- mayor similitud aumenta P cuando los demás factores son iguales;
- mayor vínculo aumenta P;
- aumentar `h` amplifica influencia de similitud y vínculo;
- relación negativa reduce R;
- relación positiva aumenta R;
- asimetría R_ij/R_ji válida.

## Commit

```text
feat: implement homophily interaction equations
```

---

# Fase 6 — Calendario académico

## Objetivo

Simular la estructura temporal de 10 semestres.

## Crear

```text
simulation/calendar.py
```

## Restricciones

Por semestre:

```text
20 weeks
5 days/week
6 courses
2 sessions/course/week
12 sessions/week
2 or 3 classes/day
same course cannot occur twice in one day
schedule fixed for semester
```

Una distribución válida:

```text
2, 2, 2, 3, 3
```

en orden aleatorio por semana base.

## Tests

- cada curso aparece exactamente dos veces;
- nunca dos veces el mismo día;
- exactamente 12 períodos semanales;
- todos los días tienen 2 o 3 períodos.

## Commit

```text
feat: generate valid semester schedules
```

---

# Fase 7 — Cursos y asignación de secciones

## Objetivo

Asignar 80 estudiantes a 3 secciones por curso.

## Primer semestre

Asignación aleatoria balanceada:

```text
27
27
26
```

en orden variable.

## Semestres siguientes

Usar asignación semi-aleatoria.

Puntuación conceptual:

```text
score(i,k) =
    gamma_section * mean_relationship_to_section(i,k)
    + (1-gamma_section) * random_component
```

Aplicar restricción dura de capacidad.

## Reglas

- cada estudiante exactamente en una sección por curso;
- todas las secciones reciben 26 o 27;
- `gamma_section` configurable;
- `gamma_section` no cambia entre escenarios principales.

## Tests

Exhaustivos sobre varias semillas.

## Commit

```text
feat: add balanced relationship-aware section assignment
```

---

# Fase 8 — Motor mínimo de conversaciones sin LLM

## Objetivo

Completar una simulación funcional sin servicios externos.

## Crear

```text
simulation/conversation.py
llm/base.py
llm/mock.py
nlp/base.py
nlp/mock.py
```

## Flujo

Por sección/clase:

1. seleccionar iniciador;
2. seleccionar tema;
3. Mock LLM genera opinión;
4. seleccionar `ceil(N/4)` expuestos;
5. calcular `P_ij`;
6. muestrear participación;
7. generar respuestas mock;
8. analizar sentimiento mock;
9. calcular `s`;
10. actualizar `R`;
11. registrar interacciones.

## Iniciador

```text
start_weight_i =
epsilon_start + (1-epsilon_start)*E_i
```

Normalizar antes de seleccionar.

## Criterio de aceptación

Simular:

```text
20 agents
1 week
```

sin errores y sin internet.

## Commit

```text
feat: add deterministic mock conversation engine
```

---

# Fase 9 — Persistencia y trazabilidad

## Objetivo

Guardar todo lo necesario para reproducir ejecuciones.

## Crear

```text
io/results.py
io/metadata.py
```

## Guardar

```text
config.json
agents.parquet
interactions.parquet
relationships.parquet
run_metadata.json
```

## Metadata

```text
run_id
seed
scenario
git_commit
software_versions
prompt_version
topic_bank_version
model_name
```

## Tests

- escritura/lectura roundtrip;
- no perder tipos importantes.

## Commit

```text
feat: persist reproducible simulation outputs
```

---

# Fase 10 — NetworkX

## Objetivo

Construir la red dinámica.

## Dependencia

Agregar:

```text
networkx
```

## Crear

```text
network/builder.py
network/metrics.py
network/snapshots.py
```

## Grafo

```python
nx.DiGraph()
```

80 nodos.

Aristas dirigidas con:

```text
weight = R_ij
interaction_count
last_interaction
```

## Snapshots

```text
semester_end
year_end
final
```

## Métricas

```text
density
in/out degree
in/out strength
reciprocity
isolates
components
clustering on projection
communities
modularity
assortativity
mean edge similarity
```

## Tests

- 80 nodos;
- pesos coinciden con matriz de relaciones;
- snapshot no muta snapshots previos.

## Commit

```text
feat: build dynamic directed social network analysis
```

---

# Fase 11 — Visualización básica

## Objetivo

Producir resultados visibles antes de integrar Gemini.

## Dependencia

Agregar:

```text
matplotlib
```

## Crear

```text
visualization/network_plots.py
visualization/metric_plots.py
```

## Salidas

```text
network_semester_01.png
network_semester_10.png
network_final.png
density_over_time.png
assortativity_over_time.png
modularity_over_time.png
relationship_distribution.png
```

## Criterio de aceptación

El MVP debe poder ejecutarse completo con mocks y producir red + métricas + PNG.

## Commit

```text
feat: add network and metric visualizations
```

---

# Fase 12 — MVP completo con Mesa

## Objetivo

Integrar el flujo dentro de un modelo basado en agentes formal.

## Dependencia

Agregar:

```text
mesa
```

## Crear

```text
simulation/model.py
```

Mesa administra:

```text
agents
simulation state
time progression
data collection when useful
```

No mover la matemática social a métodos opacos de Mesa.

Mantener funciones matemáticas independientes.

## Smoke test

```text
20 agents
4 weeks
mock LLM
mock sentiment
```

## Commit

```text
feat: integrate simulation workflow with Mesa
```

---

# Fase 13 — Integración Gemini 2.5 Flash-Lite

## Objetivo

Reemplazar generación textual mock por Gemini sin cambiar la matemática social.

## Dependencia

Agregar:

```text
google-genai
```

## Variables

```text
GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash-lite
```

## Crear

```text
llm/gemini.py
llm/prompts.py
llm/cache.py
```

## Cliente

Usar SDK oficial `google-genai`.

No exponer clave.

## Prompt

Crear prompt versionado.

Ejemplo de información permitida:

```text
student synthetic id
topic
topic orientation
relevant interests
extraversion for style only
previous message
Spanish
one short response
```

No decir al modelo que calcule el vínculo.

## Caché

SQLite o archivos JSONL/Parquet indexados.

Clave:

```text
hash(
    model
    prompt_version
    agent_id
    topic_id
    orientation
    previous_message
)
```

## Configuración inicial

- respuestas breves;
- temperatura baja/moderada;
- límite estricto de salida;
- misma configuración en todos los escenarios.

## Manejo de errores

Implementar:

```text
timeout
retry with exponential backoff
rate limit handling
empty response handling
cache fallback
```

## Tests

Mockear SDK.

No llamar API durante CI.

## Prueba manual

Ejecutar un script pequeño con 5–10 prompts reales.

## Commit

```text
feat: integrate gemini flash-lite language generation
```

---

# Fase 14 — Analizador de sentimiento real

## Objetivo

Sustituir el mock por un modelo local multilingüe.

## Dependencias

Agregar cuando se elija el modelo final:

```text
transformers
torch
```

## Crear

```text
nlp/sentiment.py
```

Salida normalizada:

```text
negative
neutral
positive
```

Calcular:

```text
V = positive + 0.5*neutral
```

## Validación

Crear un fixture pequeño de frases manualmente etiquetadas en español.

No asumir que un modelo preentrenado es perfecto.

## Commit

```text
feat: add multilingual sentiment analysis
```

---

# Fase 15 — Piloto 1

## Objetivo

Verificar lógica completa.

## Configuración

```text
10–20 agents
1–4 weeks
1 scenario
Gemini optional
```

## Revisar

- distribución de P;
- cantidad de participantes;
- evolución de R;
- cantidad de aristas;
- errores;
- costo/llamadas LLM;
- coherencia de logs.

## Ajustes permitidos

Corregir parámetros que causen:

```text
cero interacción
participación casi universal
relaciones saturadas en 0 o 1
red completa inmediata
red permanentemente vacía
```

Registrar todo cambio.

## Commit

```text
test: complete first simulation pilot
```

---

# Fase 16 — Piloto 2

## Objetivo

Escalar a población completa.

## Configuración

```text
80 agents
1 semester
mock + selected Gemini subset
```

## Medir

```text
runtime
memory
API requests
token usage if available
cache hit rate
interaction count
network metrics
```

## Commit

```text
test: validate full-cohort semester pilot
```

---

# Fase 17 — Simulación completa de 10 semestres

## Objetivo

Probar viabilidad longitudinal.

## Configuración

```text
80 agents
10 semesters
h = 0.50
one or few seeds
```

Antes de ejecutar:

- congelar parámetros;
- congelar prompt;
- congelar banco de temas;
- registrar versiones.

## Criterio

La simulación debe terminar de forma reproducible y producir los snapshots esperados.

## Commit

```text
test: complete longitudinal simulation pilot
```

---

# Fase 18 — Escenarios experimentales

## Objetivo

Comparar homofilia.

## Escenarios

```text
h=0.20
h=0.50
h=0.80
```

## Diseño

Inicialmente:

```text
30 seeds
3 scenarios
90 runs
```

Usar las mismas seeds entre escenarios.

No cambiar otros parámetros.

## Resultados agregados

Por métrica:

```text
mean
standard deviation
median when useful
confidence interval
```

## Comparaciones

Priorizar:

```text
assortativity
modularity
mean relationship weight
community count
community size distribution
isolates
reciprocity
density
```

## Commit

```text
feat: run paired homophily scenario experiments
```

---

# Fase 19 — Análisis de sensibilidad

## Objetivo

Determinar robustez.

## Parámetros

Uno por vez inicialmente:

```text
alpha_relationship
w_interest
beta_I
beta_E
beta_R
w_agreement
gamma_section
```

Mantener `h` como variable experimental central.

## Salidas

Crear tablas y gráficos que muestren la sensibilidad de las principales métricas.

## Commit

```text
feat: add local parameter sensitivity experiments
```

---

# Fase 20 — Validación interna

## Objetivo

Documentar que el modelo hace lo que se diseñó para hacer.

## Nivel 1: verificación

Tests e invariantes.

## Nivel 2: validación lógica

Pruebas controladas:

```text
h = 0
h very high
all students same interests
all students different interests
R fixed neutral
extreme extraversion distributions
```

Comprobar direcciones esperadas.

## Nivel 3: literatura

Comparar tendencias generales con hallazgos de homofilia conocidos.

No ajustar el modelo exclusivamente para copiar resultados externos.

## Nivel 4: estabilidad

Analizar variación entre semillas.

## Commit

```text
test: document model verification and internal validation
```

---

# Fase 21 — Análisis final y visualización

## Objetivo

Generar las figuras y tablas de tesis.

## Figuras sugeridas

1. evolución de la red por semestre;
2. red final por escenario;
3. assortatividad vs semestre;
4. modularidad vs semestre;
5. densidad vs semestre;
6. fuerza media del vínculo;
7. número y tamaño de comunidades;
8. distribución de vínculos;
9. sensibilidad de parámetros;
10. costo y cantidad de llamadas del LLM.

## Tablas sugeridas

1. configuración base;
2. parámetros por escenario;
3. métricas finales;
4. sensibilidad;
5. validación.

## Commit

```text
feat: generate final thesis analysis artifacts
```

---

# Fase 22 — Documentación y cierre

## Objetivo

Dejar un repositorio reproducible.

## README

Debe explicar:

```text
research goal
methodology summary
architecture
venv setup
API setup
how to run mocks
how to run Gemini
how to run one simulation
how to run scenarios
how to run sensitivity
how to reproduce figures
```

## Comandos finales deseados

Ejemplos conceptuales:

```bash
python -m homophily_sim.cli simulate --config configs/homophily_medium.yaml --seed 42
python -m homophily_sim.cli experiment --scenario all --seeds 1:30
python -m homophily_sim.cli sensitivity --config configs/base.yaml
python -m homophily_sim.cli analyze outputs/experiment_id
```

Si no existe CLI todavía, implementarla antes del cierre.

## Commit

```text
docs: finalize reproducible project documentation
```

---

# Orden estricto recomendado

No integrar Gemini antes de disponer de:

```text
population
equations
calendar
sections
mock conversation engine
persistence
network
basic visualizations
```

La simulación debe funcionar completamente sin Gemini.

Gemini es una capa de generación lingüística, no el motor de la dinámica social.

---

# Política de commits

Preferir commits como:

```text
chore: initialize python project structure
feat: add typed simulation configuration
feat: add core domain models
feat: generate reproducible synthetic student population
feat: implement homophily interaction equations
test: add participation probability edge cases
fix: preserve balanced section capacities
docs: describe synthetic demographic calibration
```

Evitar:

```text
update stuff
finish simulation
many changes
final
```

---

# Resultado final esperado

El repositorio debe permitir:

1. crear 80 estudiantes sintéticos;
2. seguirlos durante 10 semestres;
3. asignar cursos y secciones;
4. simular conversaciones;
5. calcular probabilidades de participación;
6. actualizar vínculos dirigidos;
7. generar redes dinámicas;
8. comparar homofilia baja, media y alta;
9. ejecutar múltiples semillas;
10. realizar sensibilidad;
11. validar internamente el modelo;
12. generar figuras y métricas reproducibles;
13. usar Gemini 2.5 Flash-Lite sin acoplarlo a la lógica social;
14. ejecutar pruebas sin acceso a internet ni consumo de API.
