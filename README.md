# Simulación de homofilia conductual

Modelo exploratorio basado en agentes para estudiar cómo la homofilia conductual
influye en redes de interacción de una cohorte sintética de 80 estudiantes de
Computación de la Universidad del Valle de Guatemala, durante 10 semestres.
Los agentes no representan personas reales y el modelo no predice amistades reales.
Los parámetros iniciales son operacionales, no estimaciones empíricamente calibradas.

## Estado

Fase 19: sensibilidad local de siete parámetros, uno por vez, en los tres
escenarios de homofilia. Consulte [análisis de sensibilidad](docs/experiments/phase_19_sensitivity.md).
Fase 18: comparación pareada de homofilia baja, media y alta con 30 semillas
compartidas y métricas agregadas por semestre. Consulte
[experimento de escenarios](docs/experiments/phase_18_scenarios.md).
Fase 17: piloto longitudinal de los 10 semestres, con insumos congelados,
instantáneas persistidas y verificación de reproducibilidad por repetición.
Consulte [Piloto longitudinal](docs/pilots/pilot_3_longitudinal.md).
Fase 16: piloto de 80 agentes y 20 semanas, con métricas guardadas y una muestra
independiente de Gemini. Fase 15: primer piloto pequeño con resultados conservados
para presentación. Consulte [Piloto 2](docs/pilots/pilot_2.md) y
[Piloto 1](docs/pilots/pilot_1.md).
Fase 14: clasificador multilingüe local de sentimiento, opcional y validado con
un conjunto pequeño de frases españolas etiquetadas manualmente.
La Fase 13 añadió generación lingüística opcional con Gemini 3.5 Flash-Lite y caché SQLite.
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
Para usar el analizador local de sentimiento, instale además `requirements-nlp.txt`.
En Linux, la variante de PyTorch para CPU evita descargar bibliotecas de GPU:

```bash
python -m pip install 'torch==2.14.1+cpu' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-nlp.txt
```

El resto del proyecto puede ejecutarse sin esas dependencias opcionales.

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
El clasificador local de la Fase 14 se activa explícitamente; las ejecuciones
rápidas y los tests conservan el analizador simulado.

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

## Sentimiento local

`TransformersSentimentAnalyzer` usa por defecto
`cardiffnlp/twitter-xlm-roberta-base-sentiment` para obtener probabilidades
`negative`, `neutral` y `positive`. El modelo se ejecuta localmente con PyTorch;
la primera carga descarga sus pesos y las siguientes usan la caché de Hugging Face.
Las probabilidades se normalizan y la valencia sigue siendo
`p_positive + 0.5 * p_neutral`. La simulación registra el nombre del clasificador
en `run_metadata.json` y las versiones de `torch` y `transformers`.

Para inspeccionar su desempeño en nueve frases españolas etiquetadas a mano:

```bash
python -m homophily_sim.experiments.sentiment_pilot
```

El fixture está en `data/sentiment/validation_es_v1.json`. En la ejecución local
inicial coincidió con 9/9 etiquetas; este conjunto pequeño no estima precisión
general ni garantiza que interprete correctamente conversaciones universitarias.
El modelo fue entrenado con lenguaje de redes sociales y sus errores pueden
alterar la valencia. Para usarlo en el piloto del modelo Mesa:

```bash
python -m homophily_sim.experiments.mock_mvp --smoke --sentiment
```

`--gemini` y `--sentiment` pueden activarse por separado.

## Piloto 1 y archivos para presentación

La Fase 15 ejecuta el escenario medio con 20 agentes, una semana del primer
semestre y una del segundo, semilla 42, lenguaje simulado y sentimiento local.
Ejecutar desde la raíz del repositorio:

```bash
python -m homophily_sim.experiments.pilot_1 --run-id pilot-1-medium-seed-42-final
```

Los resultados de la ejecución final se guardan en
`outputs/pilot-1-medium-seed-42-final/`. Los archivos
`pilot_1_summary.json`, `pilot_1_network_metrics.csv` y `pilot_1_report.md`
concentran las métricas; `pilot_1_conversations.csv` guarda exposiciones y
respuestas por conversación; `metrics_by_semester.json`, las tablas Parquet y los PNG
conservan el detalle y las figuras. El [resumen del Piloto 1](docs/pilots/pilot_1.md)
registra las cifras principales dentro de Git. La carpeta `outputs/` permanece
excluida de Git y debe conservarse o copiarse si se necesitan las tablas y
gráficos originales para la presentación.

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
# Piloto 2: 80 agentes durante un semestre

Ejecute la cohorte completa durante las 20 semanas del primer semestre, con
lenguaje y sentimiento simulados:

```bash
python -m homophily_sim.experiments.pilot_2 --run-id pilot-2-medium-seed-42
```

El directorio `outputs/pilot-2-medium-seed-42/` conserva la configuración,
metadatos, agentes, interacciones y relaciones en Parquet; métricas semanales
en CSV; métricas de red y resumen en JSON; y un informe Markdown con figuras.
La configuración guardada contiene el horizonte del modelo (10 semestres),
pero el resumen indica explícitamente el único semestre ejecutado.

Para generar cinco mensajes de Gemini de agentes del piloto, con una segunda
lectura de cada mensaje que mide los aciertos de caché, ejecute por separado:

```bash
python -m homophily_sim.experiments.pilot_2 --probe-gemini outputs/pilot-2-medium-seed-42
```

La muestra de Gemini requiere `GEMINI_API_KEY` en `.env`. Queda registrada en
`gemini_probe.json`, junto con solicitudes API, aciertos de caché y tokens que
informe el proveedor. No modifica el resultado de la simulación.

## Piloto longitudinal: 10 semestres

Para completar la cohorte de 80 agentes con `h = 0.50` y semilla 42:

```bash
python -m homophily_sim.experiments.longitudinal_pilot \
  --run-id pilot-3-longitudinal-seed-42
```

El piloto guarda la configuración y las versiones, las huellas SHA-256 de los
insumos, las tablas finales, los 10 cierres semestrales, los 5 anuales y el
final. Repite la corrida con la misma semilla y compara huellas del estado de
agentes, interacciones e instantáneas. Usa proveedores simulados, sin llamadas
API, para que la verificación sea reproducible en local.

## Experimento de escenarios pareados

Para ejecutar las 30 semillas en cada escenario de homofilia (90 corridas):

```bash
python -m homophily_sim.experiments.runner
```

El directorio `outputs/phase-18-scenarios/` guarda cada corrida con su
configuración, metadatos, interacciones y métricas semestrales. En la raíz
del experimento se crean `run_metrics.csv`, `scenario_summary.csv`,
`paired_final_differences.csv`, `community_size_distribution.csv`,
`experiment_summary.json` y `report.md`. Una nueva ejecución del mismo
comando reanuda corridas ya guardadas si sus insumos congelados siguen
iguales. Las comparaciones usan las mismas semillas en los tres escenarios
y estiman intervalos descriptivos del 95 % con la distribución t.

Para regenerar las tres figuras de trayectorias desde los agregados:

```bash
python scripts/plot_phase18.py
```

## Sensibilidad local de parámetros

Para evaluar los siete parámetros previstos en `AGENTS.md`, con cinco
semillas compartidas entre los tres escenarios de homofilia:

```bash
python -m homophily_sim.experiments.sensitivity
```

El directorio `outputs/phase-19-sensitivity/` guarda cada corrida y sus
configuraciones, las métricas por semestre, promedios e intervalos de confianza
y diferencias pareadas respecto al valor base del mismo escenario y semilla.
Una nueva ejecución retoma corridas ya guardadas si los insumos coinciden.
La sensibilidad cambia un parámetro por vez. Cuando varía `w_interest`, los
otros pesos de similitud se reescalan proporcionalmente para sumar uno; cuando
varía `w_agreement`, `w_sentiment` toma su complemento.
