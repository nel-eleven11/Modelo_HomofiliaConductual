# Simulación de homofilia conductual

Modelo exploratorio basado en agentes para estudiar cómo la homofilia conductual
influye en redes de interacción de una cohorte sintética de 80 estudiantes de
Computación de la Universidad del Valle de Guatemala, durante 10 semestres.
Los agentes no representan personas reales y el modelo no predice amistades reales.
Los parámetros iniciales son operacionales, no estimaciones empíricamente calibradas.

## Estado

Fase 5: ecuaciones sociales puras para similitud, participación, evaluación
y actualización de relaciones. La Fase 4 añadió la población sintética reproducible
con perfiles demográficos versionados.
La Fase 3 añadió un banco de 36 temas y una taxonomía común de intereses.
La Fase 2 añadió entidades validadas de estudiante, curso, sección, tema e interacción.
La Fase 1 añadió la configuración tipada y los escenarios de homofilia. Los YAML comparten una
base y solo modifican `h` y el nombre del escenario. La simulación de conversaciones
corresponde a la Fase 8.

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
persistencia se implementará en módulos separados conforme avance el plan.

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
