# Perfiles demográficos sintéticos v1

`profiles_v1.yaml` contiene probabilidades operacionales provisionales, no
estadísticas de UVG ni estimaciones nacionales. Los nombres `national_reference`
y `department_reference` reservan perfiles para una calibración posterior; los
valores actuales son supuestos sintéticos explícitos. El perfil `custom` es la
selección inicial de `configs/base.yaml`. Cambiar estas probabilidades requiere
registrar una nueva versión del archivo para conservar la reproducibilidad.

La edad se muestrea de `age_probabilities`; sexo y procedencia se muestrean de
Bernoulli independientes. Los intereses se extraen de la taxonomía v1, la
extroversión de una normal truncada y las orientaciones uniformemente en [-1,1].
