# agents.md

# Proyecto: Simulación de homofilia conductual en redes estudiantiles

## 1. Propósito de este archivo

Este archivo define las instrucciones permanentes para cualquier agente de Codex que trabaje en este repositorio.

El proyecto implementa en Python una simulación basada en agentes de una cohorte sintética de 80 estudiantes de Ingeniería en Ciencia de la Computación y Tecnologías de la Información de la Universidad del Valle de Guatemala, seguida desde primer año hasta quinto año.

El objetivo del software es estudiar cómo distintos niveles de homofilia conductual afectan la formación y evolución de redes de interacción estudiantil.

No se busca predecir el comportamiento de estudiantes reales. El modelo es exploratorio y utiliza datos sintéticos.

---

# 2. Reglas de trabajo para Codex

1. Trabajar por fases pequeñas y verificables.
2. No implementar fases futuras antes de que la fase actual cumpla sus criterios de aceptación.
3. Cada fase debe poder corresponder a uno o varios commits pequeños y coherentes. Tu solo realiza los commits, no tienes permiso de realizar push a menos que se te indique.
4. No modificar decisiones metodológicas centrales sin dejar una justificación escrita.
5. Mantener separadas:
   - lógica de simulación;
   - generación de datos;
   - lógica de red;
   - integración con LLM;
   - análisis de sentimiento;
   - visualización;
   - persistencia de resultados.
6. Ninguna llamada real a una API debe ejecutarse durante pruebas unitarias.
7. Toda aleatoriedad debe depender de semillas registradas.
8. Toda simulación debe guardar su configuración completa.
9. Las ecuaciones del modelo deben implementarse en funciones pequeñas, puras y testeables siempre que sea posible.
10. No usar el LLM para decidir directamente las reglas matemáticas del sistema.
11. El LLM genera lenguaje; la simulación controla probabilidades, relaciones y transiciones de estado.
12. No introducir nuevas variables del agente si no tienen una función explícita dentro del modelo.
13. No agregar nivel socioeconómico, inteligencia general ni rasgos de personalidad adicionales en la primera versión.
14. Mantener comentarios y docstrings claros, pero evitar comentarios redundantes.
15. Preferir type hints en todo el código de dominio.
16. Mantener compatibilidad con ejecución local dentro de `venv`.
17. Antes de cerrar una fase:
    - ejecutar tests;
    - ejecutar lint;
    - comprobar una simulación mínima;
    - actualizar documentación si cambió el comportamiento.

---

# 3. Alcance científico del modelo

## 3.1 Población

- 80 agentes.
- Una única cohorte.
- Se sigue la misma cohorte desde primer año hasta quinto año.
- 5 años.
- 10 semestres.
- 20 semanas por semestre.
- 5 días académicos por semana.
- Todos los agentes aprueban sus cursos y avanzan al siguiente semestre.
- No se modela deserción.
- No se incorporan nuevas cohortes.

## 3.2 Organización académica

Configuración inicial:

- 6 cursos por semestre.
- 2 sesiones semanales por curso.
- 12 períodos de clase por semana.
- Entre 2 y 3 clases por día.
- Un mismo curso no puede impartirse dos veces el mismo día.
- Cada curso tiene 3 secciones.
- Las secciones contienen 26 o 27 estudiantes.
- El horario se genera al inicio del semestre y permanece fijo durante sus 20 semanas.

## 3.3 Asignación de secciones

Primer semestre:

- asignación aleatoria balanceada.

Semestres posteriores:

- asignación semi-aleatoria;
- se considera el vínculo promedio del agente con estudiantes ya asignados;
- se respeta siempre el balance de las secciones;
- el peso de las relaciones previas se controla mediante `gamma_section`.

Valor inicial:

```text
gamma_section = 0.50
```

Este parámetro debe poder modificarse en análisis de sensibilidad.

---

# 4. Estado de cada agente

Cada agente contiene inicialmente:

```text
id
age
sex
origin
semester
courses
sections
interests
extraversion
topic_orientations
relationships
```

## 4.1 Edad

Variable demográfica sintética.

## 4.2 Sexo

Variable basada en sexo y no identidad de género.

La distribución podrá calibrarse usando estadísticas externas de educación superior de Guatemala, sin afirmar que representa exactamente a estudiantes de Computación de UVG.

## 4.3 Procedencia

Variable categórica:

```text
GUATEMALA_DEPARTMENT
REST_OF_COUNTRY
```

## 4.4 Intereses

Cada agente posee entre 1 y 5 intereses.

Los intereses y los temas de conversación usan la misma taxonomía.

Ejemplos de categorías:

```text
technology
programming
artificial_intelligence
videogames
sports
football
music
cinema
series
anime
literature
science
astronomy
art
photography
exercise
cooking
travel
animals
university_life
```

La taxonomía definitiva puede ampliarse, pero debe permanecer versionada.

## 4.5 Extroversión

Variable continua:

```text
0 <= extraversion <= 10
```

Para ecuaciones se normaliza:

```text
E_i = extraversion_i / 10
```

No representa personalidad completa.

## 4.6 Orientación temática

Cada tema específico `T` tiene una orientación estable por agente:

```text
-1 <= O_i(T) <= 1
```

Interpretación:

```text
-1  orientación/postura fuertemente negativa
 0  neutral
+1  orientación/postura fuertemente positiva
```

Los intereses representan afinidad con una categoría.

La orientación representa la postura o preferencia del agente respecto a un tema específico.

La generación textual del LLM debe respetar `O_i(T)`.

---

# 5. Banco de temas

Los intereses y temas deben compartir una taxonomía común.

Cada tema debe tener como mínimo:

```text
topic_id
category
subcategory
prompt
polarization_level
```

Valores de polarización iniciales:

```text
LOW
MEDIUM
HIGH
```

La primera versión debe usar principalmente temas `LOW` y `MEDIUM`.

Ejemplo conceptual:

```yaml
topic_id: tech_ai_jobs
category: technology
subcategory: artificial_intelligence
prompt: "¿Crees que la inteligencia artificial cambiará positivamente el trabajo de los programadores?"
polarization_level: MEDIUM
```

No guardar el banco directamente dentro de funciones Python. Mantenerlo como recurso versionado, por ejemplo:

```text
data/topics/topics_v1.yaml
```

---

# 6. Similitud entre agentes

La similitud no crea directamente un vínculo.

Solo representa cuánto se parecen dos agentes según atributos seleccionados.

Definición:

```text
Sim_ij = w_I * J_ij
       + w_A * A_ij
       + w_S * S_ij
       + w_P * P_ij
```

Pesos iniciales:

```text
w_interest = 0.70
w_age = 0.10
w_sex = 0.10
w_origin = 0.10
```

Debe cumplirse:

```text
w_interest + w_age + w_sex + w_origin = 1
```

## 6.1 Intereses: Jaccard

```text
J_ij = |Interests_i ∩ Interests_j| / |Interests_i ∪ Interests_j|
```

## 6.2 Edad

```text
A_ij = 1 - abs(age_i - age_j) / max_age_difference
```

Limitar siempre a `[0, 1]`.

## 6.3 Sexo

```text
S_ij = 1 si coinciden
S_ij = 0 si no coinciden
```

## 6.4 Procedencia

```text
P_ij = 1 si coinciden
P_ij = 0 si no coinciden
```

La similitud debe quedar:

```text
0 <= Sim_ij <= 1
```

---

# 7. Eventos de conversación

Cada reunión de una sección genera inicialmente un evento principal de conversación.

No crear una conversación independiente por cada estudiante.

Flujo:

1. seleccionar iniciador;
2. seleccionar tema;
3. generar opinión inicial;
4. seleccionar estudiantes expuestos;
5. calcular probabilidad de participación para cada expuesto;
6. decidir participación;
7. generar respuestas;
8. evaluar respuestas;
9. actualizar vínculos;
10. registrar todos los eventos.

---

# 8. Selección del iniciador

La extroversión aumenta la probabilidad de iniciar, pero ningún agente debe tener probabilidad cero.

Usar inicialmente un peso suavizado:

```text
start_weight_i = epsilon_start + (1 - epsilon_start) * E_i
```

Valor inicial:

```text
epsilon_start = 0.25
```

Normalizar los pesos entre todos los estudiantes presentes en la sección antes de seleccionar.

---

# 9. Estudiantes expuestos

Si una sección tiene `N` estudiantes:

```text
n_exposed = ceil(N / 4)
```

Ejemplo:

```text
N = 27
n_exposed = 7
```

Seleccionar los estudiantes expuestos al azar entre los demás estudiantes presentes.

La exposición no implica participación.

---

# 10. Interés temático

Para receptor `j` y tema `T`:

```text
I_j(T) = 1.0 si el tema coincide directamente con un interés
I_j(T) = 0.5 si pertenece a una categoría relacionada
I_j(T) = 0.0 si no existe afinidad
```

Mantener:

```text
0 <= I_j(T) <= 1
```

El interés afecta principalmente la decisión de participar, no directamente la calidad del vínculo.

---

# 11. Factor de homofilia

Variable experimental principal:

```text
h
```

Escenarios iniciales:

```text
LOW    = 0.20
MEDIUM = 0.50
HIGH   = 0.80
```

El factor de homofilia controla cuánto influyen:

- la similitud entre agentes;
- la relación acumulada previa;

sobre la probabilidad de interacción.

No modificar `alpha_relationship` automáticamente cuando cambie `h`.

---

# 12. Probabilidad de participación

Para una conversación iniciada por `i` y un posible participante `j`:

```text
P_ij(t) = sigmoid(
    beta_0
    + beta_E * E_j
    + beta_I * I_j(T)
    + (beta_R + lambda_R * h) * R_ji(t)
    + lambda_S * h * Sim_ij
)
```

Función sigmoide:

```text
sigmoid(x) = 1 / (1 + exp(-x))
```

Parámetros iniciales:

```text
beta_0 = -2.30
beta_E = 0.80
beta_I = 1.40
beta_R = 0.60
lambda_R = 1.00
lambda_S = 1.00
```

La participación se decide mediante Bernoulli:

```text
participates ~ Bernoulli(P_ij)
```

Nunca convertir `P_ij` en una regla determinista de umbral fijo.

---

# 13. Generación lingüística

Proveedor inicial:

```text
Google Gemini API
```

Modelo inicial:

```text
gemini-2.5-flash-lite
```

Debe configurarse mediante variable de entorno:

```text
GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash-lite
```

No escribir API keys en el repositorio.

Usar el SDK oficial:

```text
google-genai
```

La integración con LLM debe implementar una interfaz desacoplada.

Ejemplo conceptual:

```python
class LanguageModelProvider(Protocol):
    def generate_utterance(self, request: UtteranceRequest) -> UtteranceResult:
        ...
```

Implementaciones:

```text
MockLanguageModelProvider
GeminiLanguageModelProvider
```

Tests y simulaciones rápidas deben usar `MockLanguageModelProvider`.

El prompt del LLM debe incluir solo información necesaria:

```text
tema
orientación temática
intereses relevantes
nivel de extroversión cuando aporte al estilo
mensaje previo si se trata de una respuesta
restricción de longitud
idioma español
```

El LLM NO decide:

```text
Sim_ij
P_ij
s_ij
R_ij
homofilia
selección de sección
métricas de red
```

Debe existir caché local para evitar llamadas duplicadas.

La clave de caché debe depender, como mínimo, de:

```text
model
prompt_version
agent_id
topic_id
orientation
previous_message_hash
```

---

# 14. Acuerdo temático

Para agentes `i` y `j` respecto al tema `T`:

```text
A_ij(T) = 1 - abs(O_i(T) - O_j(T)) / 2
```

Debe cumplirse:

```text
0 <= A_ij(T) <= 1
```

Interpretación:

```text
1.0 = orientación idéntica
0.0 = orientación completamente opuesta
```

---

# 15. Sentimiento

La respuesta textual debe analizarse con un componente separado del LLM generador.

Interfaz esperada:

```python
class SentimentAnalyzer(Protocol):
    def analyze(self, text: str) -> SentimentResult:
        ...
```

Salida:

```text
p_negative
p_neutral
p_positive
```

Debe cumplirse aproximadamente:

```text
p_negative + p_neutral + p_positive = 1
```

Convertir sentimiento a valencia:

```text
V_ij = p_positive + 0.5 * p_neutral
```

Por tanto:

```text
0 <= V_ij <= 1
```

La primera etapa puede usar un analizador simulado para tests.

La integración final puede usar un clasificador multilingüe local mediante `transformers`.

---

# 16. Evaluación instantánea de una interacción

La evaluación que el receptor `i` realiza de un mensaje generado por `j` es:

```text
s_ij(t) = w_agreement * A_ij(T)
        + w_sentiment * V_ij(t)
```

Pesos iniciales:

```text
w_agreement = 0.75
w_sentiment = 0.25
```

Debe cumplirse:

```text
w_agreement + w_sentiment = 1
0 <= s_ij <= 1
```

El interés temático NO se vuelve a incluir en `s_ij`, porque ya influye en `P_ij`.

---

# 17. Relación acumulada

`R_ij` representa cómo el agente `i` percibe su vínculo con `j`.

La red es dirigida:

```text
R_ij != R_ji
```

Valor inicial:

```text
R_ij(0) = 0.50
```

Interpretación:

```text
0.0 = vínculo muy negativo
0.5 = neutral / sin historia suficiente
1.0 = vínculo muy positivo
```

Actualización:

```text
R_ij(t+1) = (1 - alpha) * R_ij(t)
          + alpha * s_ij(t)
```

Valor inicial:

```text
alpha_relationship = 0.20
```

Por tanto, inicialmente:

```text
80% historia
20% interacción nueva
```

Mantener `alpha_relationship` independiente de `h`.

---

# 18. Registro de interacciones

Registrar una interacción dirigida cada vez que un agente procesa una intervención de otro agente.

Como mínimo:

```text
run_id
seed
semester
week
day
course_id
section_id
conversation_id
topic_id
sender_id
receiver_id
sender_text
receiver_interest
similarity
relationship_before
participation_probability
agreement
sentiment_valence
interaction_score
relationship_after
timestamp_simulation
```

Preferir almacenamiento tabular en Parquet para ejecuciones grandes y CSV para exportaciones simples.

---

# 19. Red social

Usar:

```python
networkx.DiGraph
```

Nodo:

```text
student agent
```

Arista:

```text
directed accumulated relationship
```

Peso:

```text
R_ij
```

Snapshots principales:

```text
end_of_semester
end_of_year
final
```

---

# 20. Métricas

Calcular, cuando aplique:

```text
network density
in-degree
out-degree
weighted in-strength
weighted out-strength
reciprocity
isolates
connected/weakly connected components
clustering on an undirected projection
communities
modularity
attribute assortativity
mean edge similarity
relationship-weight distribution
community sizes
```

La homofilia debe analizarse particularmente mediante assortatividad y similitud de los extremos de las aristas.

No aplicar una métrica de red dirigida a una función que solo acepte grafos no dirigidos sin construir explícitamente una proyección documentada.

---

# 21. Escenarios experimentales

Escenario principal:

```text
homophily_low
h = 0.20
```

```text
homophily_medium
h = 0.50
```

```text
homophily_high
h = 0.80
```

Todos los demás parámetros deben permanecer iguales al comparar los tres escenarios.

Ejecutar inicialmente al menos:

```text
30 replications per scenario
```

Cada repetición usa una semilla distinta.

Para comparaciones pareadas, preferir las mismas semillas entre escenarios:

```text
seed 1 low
seed 1 medium
seed 1 high
```

---

# 22. Sensibilidad

Variable experimental principal:

```text
h
```

Parámetros secundarios de sensibilidad:

```text
alpha_relationship: 0.10, 0.20, 0.40
w_interest_similarity: 0.50, 0.70, 0.80
beta_I: 1.00, 1.40, 1.80
beta_E: 0.40, 0.80, 1.20
beta_R: 0.30, 0.60, 0.90
w_agreement: 0.60, 0.75, 0.90
gamma_section: 0.25, 0.50, 0.75
```

Cuando `w_agreement` cambie:

```text
w_sentiment = 1 - w_agreement
```

No variar múltiples parámetros simultáneamente en la primera sensibilidad local salvo que una fase posterior especifique un diseño factorial.

---

# 23. Reproducibilidad

Cada ejecución debe guardar:

```text
run_id
git_commit
seed
scenario
all_parameters
model_name
prompt_version
topic_bank_version
demographic_calibration_version
start_time
end_time
software_versions
```

Guardar configuraciones en:

```text
outputs/<run_id>/config.json
```

No depender de estado global aleatorio.

Usar generadores explícitos:

```python
numpy.random.Generator
random.Random
```

con semillas derivadas del `run_seed`.

---

# 24. Estructura propuesta del repositorio

```text
.
├── agents.md
├── plan.md
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── data/
│   ├── demographics/
│   └── topics/
│       └── topics_v1.yaml
├── configs/
│   ├── base.yaml
│   ├── homophily_low.yaml
│   ├── homophily_medium.yaml
│   └── homophily_high.yaml
├── src/
│   └── homophily_sim/
│       ├── __init__.py
│       ├── config.py
│       ├── domain/
│       │   ├── agent.py
│       │   ├── course.py
│       │   ├── section.py
│       │   ├── topic.py
│       │   └── interaction.py
│       ├── data/
│       │   ├── demographics.py
│       │   ├── population.py
│       │   └── topics.py
│       ├── social/
│       │   ├── similarity.py
│       │   ├── participation.py
│       │   ├── evaluation.py
│       │   └── relationships.py
│       ├── llm/
│       │   ├── base.py
│       │   ├── mock.py
│       │   ├── gemini.py
│       │   ├── prompts.py
│       │   └── cache.py
│       ├── nlp/
│       │   ├── base.py
│       │   ├── mock.py
│       │   └── sentiment.py
│       ├── simulation/
│       │   ├── model.py
│       │   ├── calendar.py
│       │   ├── enrollment.py
│       │   └── conversation.py
│       ├── network/
│       │   ├── builder.py
│       │   ├── metrics.py
│       │   └── snapshots.py
│       ├── experiments/
│       │   ├── runner.py
│       │   ├── scenarios.py
│       │   └── sensitivity.py
│       ├── analysis/
│       │   ├── summaries.py
│       │   └── statistics.py
│       ├── visualization/
│       │   ├── network_plots.py
│       │   └── metric_plots.py
│       └── io/
│           ├── results.py
│           └── metadata.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
└── outputs/
    └── .gitkeep
```

---

# 25. Ambiente local

Crear un entorno virtual:

```bash
python -m venv .venv
```

Activación Linux/macOS:

```bash
source .venv/bin/activate
```

Activación Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Actualizar pip:

```bash
python -m pip install --upgrade pip
```

Dependencias iniciales sugeridas:

```text
mesa
networkx
numpy
pandas
scipy
matplotlib
pydantic
pydantic-settings
python-dotenv
PyYAML
google-genai
pyarrow
```

Dependencias NLP que se incorporan en su fase:

```text
transformers
torch
```

Desarrollo:

```text
pytest
pytest-cov
ruff
mypy
```

No añadir librerías hasta la fase que las necesita.

---

# 26. Variables de entorno

`.env.example`:

```text
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
HOMOPHILY_LOG_LEVEL=INFO
```

`.env` debe estar en `.gitignore`.

---

# 27. Pruebas obligatorias

Crear tests para, como mínimo:

```text
similarity is bounded [0,1]
interest Jaccard is correct
participation probability is bounded [0,1]
higher h increases similarity influence
relationship updates stay [0,1]
R_ij and R_ji can differ
section capacities remain balanced
80 students are always assigned exactly once per course
no course occurs twice in same day
every course has two weekly sessions
topic interest scoring is deterministic
same seed reproduces synthetic population
same seed reproduces schedule
LLM mock requires no network
network contains 80 nodes
edge weights match relationships
```

---

# 28. Definición de terminado

Una fase está terminada únicamente cuando:

1. criterios de aceptación cumplidos;
2. tests verdes;
3. `ruff check .` sin errores;
4. smoke test ejecutable;
5. README/documentación actualizados si corresponde;
6. no hay secretos en git;
7. outputs generados no se versionan salvo fixtures pequeños;
8. commit claro y de alcance limitado.

---

# 29. Restricciones metodológicas

No afirmar que:

- los agentes representan individuos reales;
- el modelo predice amistades reales;
- las distribuciones nacionales son distribuciones de UVG;
- los pesos iniciales están empíricamente calibrados;
- Gemini reproduce fielmente cognición humana.

Los pesos iniciales son parámetros operacionales que deben evaluarse mediante pilotos y análisis de sensibilidad.

La finalidad es estudiar comportamientos emergentes bajo reglas explícitas y reproducibles.
