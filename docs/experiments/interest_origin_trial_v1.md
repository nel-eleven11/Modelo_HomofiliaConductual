# Prueba conjunta de homofilia y pesos de similitud

Diseño autorizado: una corrida completa de diez semestres por escenario,
con la semilla compartida 1, cohorte de 80 agentes y generación local de
lenguaje y tono. Se usa la configuración de tono `interest_conditioned`
vigente y se guarda todo en `outputs/interest-origin-trial-v1-seed001/`.

| Escenario | h | w_I | w_A | w_S | w_P |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baja | 0.20 | 0.30 | 0.25 | 0.25 | 0.20 |
| Media | 0.50 | 0.50 | 0.15 | 0.15 | 0.20 |
| Alta | 0.80 | 0.70 | 0.05 | 0.05 | 0.20 |

Los pesos suman uno en cada escenario. El remanente tras fijar `w_I` y
`w_P` se reparte por igual entre edad y sexo. Las configuraciones completas
se guardan en el plan del experimento y en cada directorio de corrida.

```bash
python -m homophily_sim.experiments.runner \
  --seed-count 1 \
  --similarity-weights-file configs/interest_origin_trial_v1.json \
  --output outputs/interest-origin-trial-v1-seed001

python -m homophily_sim.experiments.interest_network_analysis \
  outputs/interest-origin-trial-v1-seed001 --only-seed 1
```

Esta prueba cambia `h` y `w_I` simultáneamente; por ello, una diferencia
entre escenarios no identifica el efecto aislado de la homofilia ni del
peso de intereses. La comparación con el piloto anterior tampoco aísla un
solo peso, porque `w_P`, `w_A` y `w_S` cambian a la vez. Sus resultados son
exploratorios y se deben leer junto con las configuraciones guardadas.
