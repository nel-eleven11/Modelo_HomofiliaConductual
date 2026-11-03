# Cambio metodológico: tono emocional expresado v1

La corrida principal local asigna un tono negativo, neutral o positivo a cada
mensaje, después de seleccionar emisor y tema y antes de generar el texto.
La orientación temática determina la postura; el tono determina la forma de
expresarla. Un desacuerdo puede ser amable y un acuerdo puede expresarse con
frustración. El tono es igual para todos los receptores del mismo mensaje.

Para interés temático del emisor `I` en `{0, 0.5, 1}`:

```text
p_neutral = p0 - k * I
p_negative = p_positive = (1 - p_neutral) / 2
p0 = 0.70; k = 0.40
V_negative = 0; V_neutral = 0.5; V_positive = 1
s_ij = w_agreement * A_ij + w_sentiment * V
R_ij(t+1) = (1-alpha) * R_ij(t) + alpha * s_ij
```

El interés del receptor y su probabilidad de participación permanecen según
la metodología anterior. La participación se decide con el vínculo acumulado
inmediatamente anterior a la evaluación actual. Después se actualiza el vínculo
del receptor hacia el emisor; una respuesta posterior es evaluada por el
iniciador en la dirección contraria.

Se usa una semilla derivada por mensaje con el identificador de sesión,
emisor, rol y semilla de corrida. El sorteo del tono no consume el flujo de
iniciación, tema, exposición o participación. El valor esperado de V es 0.5
para cualquier interés, por simetría de tonos positivos y negativos.

`sentiment_rule=neutral_constant` reproduce el control de valencia 0.5;
`fixed_random` usa probabilidades constantes con `p_neutral=p0`;
`interest_conditioned` aplica la regla principal. Las corridas históricas
con Gemini o neutralidad constante no se mezclan en resúmenes con esta versión.

La configuración completa, `messages.parquet`, `interactions.parquet` y
`participation_attempts.parquet` permiten recalcular los nuevos resúmenes sin
volver a generar lenguaje. `mean_expressed_valence` pondera cada mensaje una
vez; `mean_evaluated_valence` pondera cada evaluación dirigida. El nombre
correcto de este componente es simulación probabilística del tono emocional.
