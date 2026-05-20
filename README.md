# MVP de Homofilia Conductual

Este proyecto contiene una primera version funcional para simular interacciones
sociales entre estudiantes ficticios usando reglas simples de homofilia
conductual.

El MVP se construira de forma incremental. La version inicial define la
estructura base del proyecto y separa las responsabilidades principales en
modulos de agentes, entorno, simulacion, analisis de red y visualizacion.

## Estructura

```text
homofilia_mvp/
├── README.md
├── requirements.txt
├── main.py
├── agent.py
├── environment.py
├── simulation.py
├── network_analysis.py
└── visualization.py
```

## Uso inicial

```bash
python main.py
```

En los siguientes pasos se agregaran agentes, reglas de interaccion, una red
social con NetworkX, visualizacion y exportacion de resultados.
