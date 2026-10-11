# Simulación de homofilia conductual

Modelo exploratorio basado en agentes para estudiar cómo la homofilia conductual
influye en redes de interacción de una cohorte sintética de 80 estudiantes de
Computación de la Universidad del Valle de Guatemala, durante 10 semestres.
Los agentes no representan personas reales y el modelo no predice amistades reales.
Los parámetros iniciales son operacionales, no estimaciones empíricamente calibradas.

## Estado

Fase 13: generación lingüística opcional con Gemini 2.5 Flash-Lite y caché SQLite.
La Fase 12 integró el flujo semanal en un modelo de Mesa.
La Fase 11 añadió visualizaciones PNG y ejecución completa local con proveedores simulados.
La Fase 10 añadió una red dirigida dinámica con NetworkX, métricas y snapshots independientes.
La Fase 9 añadió persistencia de ejecuciones en JSON y Parquet, con trazabilidad de
semilla, revisión Git, versiones de software y recursos del modelo.
La Fase 8 añadió un motor de conversaciones reproducible con lenguaje y sentimiento
simulados. Cada clase de cada sección produce un evento de conversación.
La Fase 7 añadió la inscripción balanceada en secciones por curso.
La Fase 6 añadió el calendario académico reproducible de 10 semestres.
La Fase 5 añadió ecuaciones sociales puras para similitud, participación,
evaluación y actualización de relaciones. La Fase 4 añadió la población sintética reproducible
con perfiles demográficos versionados.
La Fase 3 añadió un banco de 36 temas y una taxonomía común de intereses.
La Fase 2 añadió entidades validadas de estudiante, curso, sección, tema e interacción.
La Fase 1 añadió la configuración tipada y los escenarios de homofilia. Los YAML
comparten una base y solo modifican `h` y el nombre del escenario.

Las reglas metodológicas están en [AGENTS.md](AGENTS.md) y el orden de implementación
en [PLAN.md](PLAN.md).

## Instalación local

Se requiere Python 3.14 o superior. Entorno verificado con Python 3.14.2.
Desde la raíz del repositorio, en Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

En Windows PowerShell, activar con `.venv\Scripts\Activate.ps1`.
La instalación editable permite importar `homophily_sim` sin configurar `PYTHONPATH`.
`requirements-runtime.txt` contiene las dependencias del paquete; `requirements.txt`
instala también el proyecto y `requirements-dev.txt` agrega las herramientas de desarrollo.
Ambos usan `constraints.txt` para fijar las versiones directas y transitivas
verificadas en Linux x86_64 con CPython 3.14.2. Otros sistemas no se han validado;
las herramientas de construcción se resuelven por separado durante la instalación.

## Verificación

Con el entorno activado:

```bash
pytest
ruff check .
mypy
pytest tests/smoke
python -c "import homophily_sim; print(homophily_sim.__doc__)"
python -m pip check
```

El smoke test comprueba que el paquete se puede localizar e importar.
Las pruebas no requieren internet ni credenciales.

## Estructura

```text
src/homophily_sim/  Paquete Python; módulos por responsabilidad en fases posteriores
configs/           Configuraciones del modelo (Fase 1)
data/demographics/ Datos de referencia demográfica
data/topics/      Banco de temas versionado (Fase 3)
tests/unit/        Pruebas unitarias
tests/integration/ Pruebas de integración
tests/smoke/       Comprobación mínima de instalación
outputs/           Resultados locales, excluidos de Git
```

La lógica de simulación, datos, red, lenguaje, sentimiento, visualización y
persistencia se mantiene en módulos separados conforme avanza el plan.

## Variables de entorno y resultados

`.env.example` documenta `GEMINI_API_KEY`, `GEMINI_MODEL` y la ruta de caché.
Puede copiarse a `.env` y configurarse localmente para usar Gemini; los pilotos
con mocks no necesitan una API key.
`.env`, sus variantes locales, el entorno virtual, las cachés y los resultados en
`outputs/` nuevos están excluidos de Git; `outputs/.gitkeep` conserva la carpeta.
Los resultados del MVP que ya estaban versionados no quedan excluidos
retroactivamente: su eliminación previa en el árbol de trabajo queda fuera del
commit de la Fase 0.
El clasificador de sentimiento con `transformers` se incorporará en su fase.

## Configuración

```python
from homophily_sim.config import load_config

config = load_config("configs/homophily_medium.yaml")
print(config.h)  # 0.5
```

El cargador valida rangos, pesos y estructura académica. `max_age_difference=10`
es un límite operacional para la similitud por edad y puede ajustarse en sensibilidad.

## Temas e intereses

`data/topics/topics_v1.yaml` contiene los temas, categorías, subcategorías y
relaciones entre categorías. `load_topics(path)` valida el banco.
`topic_interest_score(interests, topic, bank)` devuelve 1.0 por coincidencia
directa, 0.5 por categoría relacionada y 0.0 sin afinidad.

## Población sintética

`generate_population(config, bank, profile, seed)` crea los mismos 80 agentes
para una configuración, banco, perfil y semilla iguales. Los perfiles de
`data/demographics/profiles_v1.yaml` son supuestos sintéticos provisionales;
sus nombres no implican calibración empírica. La distribución de cantidades de
intereses y la normal truncada de extroversión se configuran en `configs/base.yaml`.

## Ecuaciones sociales

`social/` implementa las ecuaciones documentadas en AGENTS.md. La probabilidad
de participación se calcula sin umbral; el muestreo Bernoulli pertenece al motor
de conversaciones de la Fase 8. `h` modifica la influencia de similitud y
relación previa, mientras `alpha_relationship` se mantiene independiente.

## Calendario académico

`generate_academic_calendar(config, run_seed)` crea 10 horarios semestrales.
Cada uno repite un horario semanal fijo durante 20 semanas, con 12 períodos
repartidos en cinco días (2, 2, 2, 3 y 3); cada curso se reúne dos veces en
días distintos. El calendario define encuentros de clase, no conversaciones;
el motor de conversaciones llega en la Fase 8.

## Inscripción en secciones

`enroll_semester(students, schedule, config, run_seed)` asigna cada estudiante
una vez a cada curso del semestre y guarda sus cursos y secciones en el agente.
Con 80 estudiantes y tres secciones, los tamaños por curso son 27, 27 y 26.
El primer semestre usa una asignación aleatoria balanceada. Después, cada
estudiante elige entre secciones con cupo mediante
`gamma_section * vínculo_promedio + (1 - gamma_section) * componente_aleatorio`.
El vínculo es dirigido desde el estudiante hacia los miembros ya asignados;
para una sección vacía se usa `initial_relationship`. El cupo siempre se respeta.

## Conversaciones simuladas

`simulate_week(...)` ejecuta un evento por reunión de sección. Selecciona un
iniciador con peso suavizado por extroversión y expone a `ceil(N/4)` compañeros.
Cada expuesto decide si responde mediante Bernoulli usando la probabilidad del
modelo. El expuesto evalúa el mensaje inicial y, si responde, el iniciador evalúa
su respuesta. Cada evaluación actualiza un vínculo dirigido y crea un
`InteractionRecord`. Los timestamps se derivan del calendario simulado.

El proveedor `MockLanguageModelProvider` produce texto breve en español y
`MockSentimentAnalyzer` devuelve una valencia neutral fija. Son componentes
deterministas para pilotos sin internet; `utterance_max_words` se configura en
`configs/base.yaml`. Una simulación mínima de 20 agentes y una semana se comprueba
con `pytest tests/smoke/test_mock_week.py`.

## Persistencia y trazabilidad

`make_run_metadata(...)` registra identificador, semilla, escenario, revisión Git,
versiones de Python y dependencias, modelo, versión del prompt y versiones de
los datos. Las fechas de inicio y fin se suministran explícitamente.
`save_run(output_root, config=..., agents=..., interactions=..., metadata=...)`
escribe `config.json`, `run_metadata.json`, `agents.parquet`,
`interactions.parquet` y `relationships.parquet` bajo `output_root/run_id`.
`config.json` conserva todos los parámetros operacionales; la semilla y las
versiones de datos están en `run_metadata.json`. El guardado rechaza un
`run_id` existente para evitar sobrescribir resultados.

`load_run(path)` reconstruye los modelos tipados y verifica que la tabla de
vínculos dirigidos coincida con los agentes. Solo se guardan vínculos que ya
aparecen explícitamente en el estado de los agentes; los demás conservan el
valor inicial definido por la configuración. Los intereses, orientaciones y
asignaciones se codifican como JSON dentro de Parquet para preservar su tipo.

## Red social

`build_graph(agents, interactions)` crea un `networkx.DiGraph` con un nodo por
estudiante. Una arista `i → j` representa el vínculo que `i` percibe hacia `j`;
su peso es `R_ij`. Solo los vínculos explícitos crean aristas. Cada registro
dirigido incrementa `interaction_count` y actualiza `last_interaction` en la
arista del receptor hacia el emisor. `capture_snapshot(...)` construye un grafo
nuevo para `semester_end`, `year_end` o `final`, sin compartir sus aristas con
snapshots anteriores.

`compute_metrics(graph, agents, config)` calcula densidad, grados, fuerzas
ponderadas, reciprocidad, aislados, componentes débiles y fuertes,
assortatividad por sexo y procedencia, similitud media de extremos y
distribución de pesos. Para clustering, comunidades y modularidad construye
una proyección no dirigida: basta una arista en cualquier dirección y esas
tres métricas usan aristas sin peso. Métricas indefinidas por ausencia de
aristas o variación se representan con `None`.

## Modelo Mesa e informe visual con mocks

`HomophilyModel` registra cada estudiante como `StudentMesaAgent` y conserva su
estado validado en `StudentAgent`. Cada llamada a `model.step()` ejecuta una
semana académica; Mesa lleva el reloj y registra por semana el semestre,
semana, número de conversaciones e interacciones. Al terminar cada semestre
se calculan un snapshot y métricas; al terminar el año y la simulación se
guardan también los snapshots correspondientes. La matemática social y la
generación de conversaciones siguen en sus módulos independientes.

Desde la raíz del repositorio, el piloto reducido ejecuta 20 agentes, dos
semestres y una semana por semestre sin llamadas externas:

```bash
python -m homophily_sim.experiments.mock_mvp --smoke
```

Sin `--smoke`, el comando ejecuta el modelo Mesa con la configuración completa de 80 agentes, diez
semestres y veinte semanas por semestre. `--seed`, `--run-id`, `--config` y
`--output` permiten controlar la ejecución. Cada `run_id` debe ser nuevo;
los resultados quedan en `outputs/<run_id>/` junto con las tablas y metadatos
de la Fase 9. Además de `metrics_by_semester.json`, el informe produce:

```text
network_semester_01.png    network_semester_10.png    network_final.png
density_over_time.png     assortativity_over_time.png
modularity_over_time.png  relationship_distribution.png
```

El piloto reducido nombra su última red `network_semester_02.png`. Las redes
comparten posiciones calculadas con la semilla y la red final. Las figuras
usan Matplotlib sin depender de una pantalla; las salidas generadas no se
versionan.

## Generación opcional con Gemini

`GeminiLanguageModelProvider` implementa la misma interfaz que el proveedor
mock. Lee `GEMINI_API_KEY` y, por defecto, usa `gemini-3.5-flash-lite`.
El modelo previsto originalmente, `gemini-2.5-flash-lite`, ya no está
disponible para proyectos nuevos; por eso se cambió el valor predeterminado
sin modificar las reglas sociales. Si `.env` contiene `GEMINI_MODEL`, actualice
esa línea: su valor tiene prioridad sobre el predeterminado del código.
El prompt versionado `student-spanish-v1` transmite solo el tema, la
orientación temática, intereses relevantes, extroversión para el estilo y
mensaje previo. Gemini escribe el texto; la simulación conserva el control
de probabilidades, relaciones y estados. La temperatura inicial es `0.3`,
el límite es 128 tokens de salida y el texto se recorta a `max_words`.

La caché SQLite en `outputs/llm_cache.sqlite3` evita llamadas duplicadas y
puede configurarse con `HOMOPHILY_LLM_CACHE_PATH`. Su clave incorpora el modelo,
la versión del prompt, el agente, tema, orientación, contexto previo, semilla
y parámetros de generación. El cliente usa timeout y reintentos para errores
transitorios, incluidos límites de tasa. Sin clave o respuesta válida, informa
el error; los tests usan un cliente simulado y no contactan la API.

Después de configurar la clave, el piloto manual realiza cinco solicitudes
reales y permite hasta diez con `--count`:

```bash
python -m homophily_sim.experiments.gemini_pilot --count 5
```

Para sustituir el lenguaje mock dentro del modelo Mesa y generar el mismo
informe visual, añada `--gemini` al comando `mock_mvp`; el sentimiento sigue
siendo simulado hasta la Fase 14:

```bash
python -m homophily_sim.experiments.mock_mvp --smoke --gemini
```
