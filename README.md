# MVP de Homofilia Conductual

Este proyecto simula interacciones sociales entre estudiantes ficticios de
Ingenieria en Ciencias de la Computacion usando reglas simples de homofilia
conductual. El objetivo del MVP es probar una idea conceptual: estudiantes con
atributos mas similares tienen mayor probabilidad de interactuar.

## Alcance del MVP

- Crea entre 10 y 20 agentes ficticios.
- Asigna atributos basicos: edad, genero, carrera, semestre, gustos,
  extroversion y responsabilidad.
- Usa un curso compartido como entorno social inicial.
- Simula interacciones por dias durante un periodo corto.
- Registra las interacciones observadas.
- Construye una red social con NetworkX.
- Calcula metricas basicas de la red.
- Genera una visualizacion final en PNG.
- Exporta resultados en archivos CSV.

## Instalacion

```bash
python -m pip install -r requirements.txt
```

## Ejecucion

Desde la raiz del repositorio:

```bash
python mvp/main.py
```

La ejecucion imprime el avance diario de la simulacion, genera la red final y
guarda los resultados en la carpeta `outputs/`.

## Archivos Generados

```text
outputs/interactions.csv
outputs/network_metrics.csv
outputs/network_final.png
```

`interactions.csv` contiene el dia, los agentes evaluados, su similitud y si
ocurrio una interaccion.

`network_metrics.csv` contiene el numero de agentes, interacciones,
conexiones, densidad, grado promedio y componentes conectados.

`network_final.png` muestra la red final; cada nodo representa un estudiante y
el grosor de cada arista representa la frecuencia de interaccion.

## Modelo

Cada estudiante se modela como un agente con atributos sinteticos. La similitud
entre dos agentes aumenta cuando comparten gustos, carrera, semestre, genero y
un nivel parecido de extroversion.

La probabilidad de interaccion usa la formula:

```text
probabilidad_interaccion = probabilidad_base + similitud * peso_homofilia
```

Para esta version inicial se usan estos valores:

```text
probabilidad_base = 0.10
peso_homofilia = 0.50
```

## Estructura

```text
.
├── README.md
├── requirements.txt
└── mvp/
    ├── agent.py
    ├── environment.py
    ├── main.py
    ├── network_analysis.py
    ├── simulation.py
    └── visualization.py
```

## Limitaciones

- Los datos son sinteticos.
- Solo se usa un curso.
- No se modela movilidad real dentro del campus.
- No se incluyen horarios complejos.
- No se incluyen actividades extracurriculares.
- La personalidad se simplifica a pocos atributos.
- La interaccion depende de reglas simples.
- La red no representa datos reales de estudiantes.

Este MVP es una primera prueba conceptual y no una representacion real de la
poblacion estudiantil.
