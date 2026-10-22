# Fase 21: tablas y figuras finales para la tesis

## Alcance y fuentes

Este paquete presenta los resultados sintéticos de las fases 18 y 19 sin
repetir simulaciones ni cambiar parámetros. La comparación principal utiliza
30 semillas pareadas por cada escenario de homofilia (`h = 0.20`, `0.50`,
`0.80`): 90 corridas completas de 80 agentes y 10 semestres. La sensibilidad
local usa cinco semillas pareadas para cada perturbación de siete parámetros.
Las figuras longitudinales muestran medias e intervalos descriptivos del 95 %.

El generador lee los agregados y las corridas guardadas, comprueba que las
90 trayectorias tengan los 10 semestres y las mismas semillas, y verifica
que las redes finales reconstruidas desde las interacciones coincidan con
las relaciones persistidas. `manifest.json` incluye huellas SHA-256 de las
tablas, planes, código de análisis y archivos de red empleados.

## Lectura de las figuras

| Figura | Contenido | Interpretación |
| --- | --- | --- |
| `network_evolution` | Semestres 1, 5 y 10 de `h = 0.50`, semilla 1 | Muestra visual de vínculos dirigidos |
| `network_final_scenarios` | Semestre 10 de los tres escenarios, semilla 1 | Misma cohorte y posiciones entre paneles |
| `assortativity` | Sexo y procedencia por semestre | Métricas de la red dirigida completa |
| `modularity` | Modularidad por semestre | Proyección no dirigida explícita |
| `density` | Densidad por semestre | Fracción de aristas dirigidas posibles |
| `relationship_weight` | Peso medio de vínculos por semestre | Media de relaciones dirigidas existentes |
| `communities` | Número de comunidades y tamaño de la mayor | Proyección no dirigida explícita |
| `edge_similarity` | Similitud media de extremos por semestre | Pesos de similitud comunes entre escenarios |
| `relationship_distribution` | Distribución final de pesos dirigidos | Agrupa todas las aristas de 30 semillas por escenario |
| `sensitivity_*` | Efectos de parámetros en los tres valores de `h` | Diferencias respecto a la base con semillas pareadas |
| `llm_usage` | Solicitudes y tokens registrados | Corridas mock frente a una muestra Gemini independiente |

Las figuras de red dibujan **hasta los tres vínculos salientes más fuertes
por agente** para que sean legibles. Los títulos informan el número de
aristas y la densidad de la red completa. Las posiciones de los 80 agentes
son fijas entre paneles y provienen de un diseño con semilla 42; se usa
la misma cohorte con semilla de simulación 1 en los tres escenarios. El
filtro solo afecta la visualización: métricas y tablas usan todas las
aristas. El color indica el sexo sintético.

En `relationship_distribution`, los histogramas normalizan por el número
de aristas de cada escenario. `relationship_weight_bins.csv` conserva
recuentos y fracciones por intervalo. Las figuras de sensibilidad muestran
cinco pares por condición, y la figura de similitud usa los pesos base
fijos para comparar la composición de aristas cuando cambia `w_interest`.

## Tablas y resultados centrales

`configuration_base.csv` enumera todos los parámetros base;
`scenario_parameters.csv` contiene la configuración completa de cada
escenario. Entre esos tres escenarios cambian únicamente `h` y el nombre.
`final_metrics.csv` guarda la media y el intervalo del 95 % al semestre 10
para diez métricas. `sensitivity.csv` reúne 252 estimaciones pareadas de
seis combinaciones de métrica y semestre por cada nivel, parámetro y `h`.
`llm_usage.csv` separa las 90 corridas mock de la muestra Gemini.

| Indicador final, media de 30 semillas | h = 0.20 | h = 0.50 | h = 0.80 |
| --- | ---: | ---: | ---: |
| Densidad | 0.99947 | 0.99942 | 0.99965 |
| Peso medio de vínculos | 0.60593 | 0.60706 | 0.60839 |
| Similitud media de aristas | 0.212293 | 0.212293 | 0.212302 |
| Modularidad | 0 | 0 | 0 |
| Comunidades | 1 | 1 | 1 |

La red dirigida llega a densidad cercana a uno, de modo que las medidas
finales de densidad y comunidades apenas separan escenarios. El peso medio
de vínculos aumenta ligeramente con `h`; la similitud final de extremos
cambia muy poco. La sensibilidad mostró efectos mayores de
`alpha_relationship` y `w_agreement` en el peso final, y de `beta_E`,
`beta_R` y `beta_I` en la densidad temprana. Los números describen este
modelo exploratorio; no predicen vínculos de estudiantes reales.

Las 90 corridas longitudinales utilizaron proveedores simulados y no
hicieron solicitudes a Gemini: su costo de API es USD 0. La muestra
independiente del piloto 2 registró cinco solicitudes lógicas al SDK,
850 tokens de entrada y 158 de salida. No se guardó el monto facturado
de esa muestra; la tabla deja el costo monetario sin valor en vez de
inferirlo de una tarifa externa.

## Estado de la validación

Por instrucción del usuario, la fase 20 de validación interna queda en
espera. `validation_status.csv` marca esa tabla como pendiente. Las
pruebas y comprobaciones técnicas de esta fase verifican generación y
consistencia de los artefactos, pero no sustituyen los experimentos
controlados ni la comparación con literatura previstos en la fase 20.

## Reproducción y entrega

Desde el entorno virtual del repositorio, con las salidas previas en
`outputs/`, ejecute:

```bash
python scripts/generate_phase21.py
```

El comando crea `outputs/phase-21-thesis/` y
`outputs/phase-21-thesis.zip`. La carpeta contiene tablas CSV, figuras
PNG y PDF, y el manifiesto. El ZIP reúne esos archivos y este informe
para trasladarlos a la presentación. Los datos de las corridas completas
siguen en `outputs/phase-18-scenarios/` y
`outputs/phase-19-sensitivity/`. `outputs/` no se versiona en Git.
