# Simulación de homofilia conductual

Modelo exploratorio basado en agentes para estudiar cómo la homofilia conductual
influye en redes de interacción de una cohorte sintética de 80 estudiantes de
Computación de la Universidad del Valle de Guatemala, durante 10 semestres.
Los agentes no representan personas reales y el modelo no predice amistades reales.
Los parámetros iniciales son operacionales, no estimaciones empíricamente calibradas.

## Estado

Fase 9: persistencia de ejecuciones en JSON y Parquet, con trazabilidad de
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

`.env.example` documenta las variables previstas. Para una futura integración,
puede copiarse a `.env` y configurarse localmente; la Fase 0 no necesita una API key.
`.env`, sus variantes locales, el entorno virtual, las cachés y los resultados en
`outputs/` nuevos están excluidos de Git; `outputs/.gitkeep` conserva la carpeta.
Los resultados del MVP que ya estaban versionados no quedan excluidos
retroactivamente: su eliminación previa en el árbol de trabajo queda fuera del
commit de la Fase 0.
Gemini, Mesa, NetworkX, matplotlib y transformers se incorporarán en sus fases.

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
