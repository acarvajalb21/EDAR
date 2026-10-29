# Protocolo de revisión del modelo (27 de octubre de 2026)

Este documento se fijó antes de entrenar candidatos nuevos. Los resultados de `ml_salud/resultados/` se conservan sin cambios. No hay repositorio Git en la carpeta DATAVIZ; por eso el código y las salidas nuevas permanecen en `ml_salud/experimentos_2026_10/`. Los CSV fuente se leen desde `PROYECTO_DISCAPACIDAD/data` sin copiarlos.

## Pregunta y población

Se conserva la cohorte y la regla original de `SIN_ACCESO=1`. La etiqueta mezcla acudir a la EPS sin atención con otras acciones o ninguna. No se interpreta como denegación de servicio ni como necesidad clínica insatisfecha. Se excluyen los componentes de la etiqueta, variables posteriores, identificadores, `P_TRABAJO` y `PA_ASISTENCIA` del modelo principal.

## Evaluación

- **Métrica principal:** `average_precision_score` (AP no interpolada) de `SIN_ACCESO=1`.
- **Secundarias:** ROC-AUC, Brier, precisión, sensibilidad, F1, matriz de confusión, calibración y precisión/sensibilidad/lift al priorizar 5 %, 10 % y 20 %. AP es distinta del área trapezoidal de la curva PR.
- **Particiones:** exactamente las del experimento original, con `StratifiedGroupKFold(7, shuffle=True, random_state=42)` por vivienda: pliegues 2–6 para entrenamiento, 1 para validación y 0 para prueba. Para comparar candidatos se usa CV agrupada de 3 pliegues en entrenamiento, semilla 43. Todas las transformaciones aprendidas se ajustan dentro del pipeline y de cada pliegue.
- **Referencia:** primero se recalculan huellas, cohorte, claves, grupos y predicciones del artefacto original; después se reentrena el boosting original con sus parámetros publicados y se comparan sus predicciones con el artefacto. No se modifica el artefacto original.
- **Presupuesto de candidatos:** un cambio de preprocesamiento/codificación, una variable `personas_por_dormitorio` y combinaciones acotadas con boosting de histogramas; otros paquetes de boosting solo si están disponibles en el entorno local sin alterar el entorno global. Se registrarán todos los ensayos, incluidos los desfavorables, tiempo y versiones. No se usa SMOTE ni se modifica la población o la etiqueta.
- **Selección:** la CV de entrenamiento ordena candidatos por AP media. La validación separada corrobora. Para proponer sustitución se requiere una ganancia de AP en validación de al menos 0,010 sobre el modelo original, un intervalo percentil 95 % de la diferencia pareada por bootstrap de viviendas enteramente por encima de cero, y un Brier que no empeore más de 0,002. Además se inspeccionan subgrupos y calibración; una ganancia numérica aislada no basta. Si no se cumplen esos criterios, se conserva el modelo original.
- **Umbral:** el umbral F1 original se documenta como referencia histórica. Cualquier umbral nuevo se fija en validación; los escenarios por capacidad son exploratorios porque no hay costos ni capacidad operativa definidos. Empates en top-k: puntuación descendente y, a igualdad, posición estable original ascendente.
- **Prueba histórica:** ya fue consultada por el proyecto y **no es confirmatoria**. Se consulta una vez tras fijar la selección para describir una comparación interna exploratoria. Repartir de nuevo estos datos no restauraría una prueba intacta.
- **Incertidumbre:** comparación pareada mediante bootstrap de viviendas completas con semilla 44 y 250 réplicas, sobre las mismas observaciones. Sus intervalos condicionan en modelos fijos y no incluyen incertidumbre de entrenamiento ni selección. Para subgrupos se mostrarán denominadores, positivos e intervalos binomiales Wilson cuando el tamaño lo permita.
- **Territorio:** dejar municipios fuera responde a transferencia geográfica y se reporta por separado de la generalización a viviendas nuevas de municipios representados. Se hará una sensibilidad acotada si la distribución de municipios permite estimar AP de manera interpretable.
- **Calibración:** cualquier calibrador se ajustará con predicciones fuera de pliegue o un subconjunto separado del entrenamiento, nunca con prueba. Mejorar Brier no garantiza mejorar AP.

Los scripts y el registro de resultados de este directorio deben indicar claramente qué se ejecutó y qué quedó pendiente. No actualizan Dash, Bookdown ni Cloud Run.

## Ampliación predefinida tras la primera ronda

El usuario pidió continuar buscando el mejor modelo. Antes de ejecutar una segunda ronda se fijan **tres** variantes adicionales sobre el mismo entrenamiento y los mismos tres pliegues agrupados: boosting con regularización L2=1, boosting con fracción de variables `max_features=0.7`, y boosting más lento (`learning_rate=0.025`, 500 iteraciones). Se añade **una** mezcla fija 75 % boosting original y 25 % regresión logística original, sin ajustar el peso con validación. Cada variante se compara con la referencia en CV y se evalúa en validación una vez. La misma regla de sustitución de arriba sigue vigente. La prueba histórica no se consulta para seleccionar esta ampliación; el uso repetido de validación hace que cualquier ventaja sea exploratoria, incluso si cruzara la regla numérica. No se amplía la búsqueda de forma adaptativa tras ver estos resultados.
