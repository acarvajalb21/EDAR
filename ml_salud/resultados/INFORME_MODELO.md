# Evaluación técnica del modelo de acceso formal a salud

**Fuente:** microdatos anonimizados del CNPV 2018, departamento del Atlántico,
leídos del proyecto local `PROYECTO_DISCAPACIDAD`. El proyecto visible
`DATAVIZ/app_dash` contiene ejercicios de Dash sobre créditos, abejas y
finanzas; no incluye la base ni el EDA de salud. No se modificó el proyecto
original. Los tres archivos originales y sus SHA-256 constan en
`resultados.json`.

## Conclusión

Entre los modelos probados, se seleccionó **HistGradientBoostingClassifier**
con tasa de aprendizaje 0,04, 31 hojas como máximo, mínimo de 30 observaciones
por hoja y 320 iteraciones, sin una partición interna para parada temprana.
Ganó en validación por Average Precision, **AP = 0,346**, y Brier, **0,156**.
En la prueba interna obtuvo **AP = 0,339**, **ROC-AUC = 0,673** y
**Brier = 0,156**. El baseline de prevalencia tiene AP = 0,211. La mejora
permite ordenar perfiles, pero la discriminación es **moderada**. Este
modelo clasifica una conducta declarada en el censo de 2018; no está
validado para decisiones individuales ni para datos actuales.

## Auditoría de datos y etiqueta

- La base de personas tiene 2.342.265 registros. De ellos, 136.114
  reportaron un problema de salud en los 30 días anteriores al censo; 80
  quedaron sin etiqueta clasificable. El análisis utiliza 136.034 personas.
- La etiqueta original `ACCESO_FORMAL_SALUD=1` se asigna a quien acudió a su
  entidad de seguridad social y recibió atención, o a un médico particular.
  `ACCESO_FORMAL_SALUD=0` incluye a quien acudió a la entidad sin recibir
  atención y a quien recurrió a otras alternativas o no hizo nada. El modelo
  invierte la etiqueta: `SIN_ACCESO=1` es la clase de interés.
- Hay 28.650 casos etiquetados «sin acceso formal según la regla del EDA»
  (21,06 %) y 107.384 con acceso (78,94 %). De los 28.650, **1.907
  (6,7 %) acudieron a la EPS y no recibieron atención**, mientras **26.743
  (93,3 %) reportaron otras acciones o ninguna**. Por ello, la etiqueta no
  debe traducirse como «servicio denegado» o «sin ninguna atención».
  Accuracy o un umbral de 0,5, aislados, serían engañosos.
- No hay claves de persona duplicadas. Los 136.034 registros etiquetados
  enlazaron con hogar y vivienda, sin duplicar filas.
- Mayores proporciones de faltantes o códigos no informados entre las 26
  variables usadas: estado civil 15,88 %, nivel educativo 10,05 % y
  alfabetismo 9,75 %. Sus faltantes brutos, antes de contar los códigos de
  «no informa», ocurren en edades en que las preguntas no aplican. En
  hogar/vivienda, agua para cocinar
  y estrato rondan 1,15 % y 1,14 %. El desglose completo está en
  `perfil_calidad.json`.
- Los códigos de no respuesta se mantienen como información de ausencia
  dentro del preprocesamiento. `H_DONDE_PREPALIM=9` se convierte en
  categoría de faltante, al igual que otros códigos de «no informa».
  Los recuentos numéricos con valor 99 se convierten en
  faltantes y se imputan con la mediana del entrenamiento.

La etiqueta mide **conducta declarada de búsqueda y recepción de atención**,
según esta definición del EDA. No mide afiliación al seguro, elegibilidad,
necesidad clínica ni una barrera causal demostrada.
En particular, acudir a un médico particular se clasifica como acceso sin
una pregunta adicional que confirme la atención, según la regla del
notebook original.
La categoría 0 incluye farmacia y prácticas de atención tradicional según
el [diccionario del DANE](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V582?name=P_QUEHIZO_PPAL);
llamarla «sin ninguna atención» sería incorrecto.

## Diseño de validación y control de fuga

Se excluyeron `P_QUEHIZO_PPAL` y `PA_LO_ATENDIERON`, porque construyen la
etiqueta, y `PA1_CALIDAD_SERV`, porque solo se conoce tras usar el
servicio. Los identificadores y las copias de la etiqueta tampoco entran
al modelo. La auditoría retiró además `P_TRABAJO` y `PA_ASISTENCIA`:
se miden en el mismo censo y pueden reflejar consecuencias del episodio
de salud. La versión principal usa **26 variables**. En una sensibilidad
con la misma validación, la versión de 28 obtuvo AP = 0,355 frente a
AP = 0,346 sin las dos variables; se aceptó esa pérdida pequeña para
reducir ambigüedad temporal. Esto no prueba que el resto de covariables
sea anterior al episodio. Los cuatro contrastes exploratorios están en
`sensibilidad_vivienda.json`.

La normalización de códigos es determinista y está incluida en el
artefacto de inferencia. La imputación, codificación categórica y escalado
se ajustan solo con entrenamiento en cada fold.

La partición de 7 folds estratificados por clase y agrupados por **vivienda**
deja 97.167 personas para entrenamiento, 19.433 para validación y 19.434
para prueba. Las prevalencias respectivas son 21,062 %, 21,057 % y
21,061 %. Ninguna vivienda aparece en más de una partición. La búsqueda
de parámetros usa 3 folds dentro del entrenamiento, también agrupados
por vivienda. La validación elige modelo y un umbral para cada candidato;
la prueba se calcula después.

La separación comprueba generalización a **otras viviendas de los mismos
municipios y del mismo censo**. No demuestra transferencia a nuevos
municipios, otro año o una muestra clínica. Como esta auditoría siguió
a una primera evaluación de prueba con otro protocolo, las cifras finales
son una evaluación interna revisada, no una prueba confirmatoria externa
intocada. Antes de desplegar el modelo se necesita validación externa.

## Comparación de modelos

La métrica primaria es **Average Precision (AP)** de `SIN_ACCESO=1`,
calculada con `average_precision_score` de scikit-learn. El campo
`pr_auc` del JSON guarda este valor no interpolado, no el área trapezoidal
de la curva precisión–recall. Con prevalencia de 21,06 %, se probaron
pesos de clase en la logística; no se aplicó sobremuestreo sintético.
La regresión logística regularizada,
con edad codificada por categorías, obtuvo AP de 0,321 en validación
cruzada, 0,329 en validación y 0,330 en prueba. Su ROC-AUC y Brier en
prueba fueron 0,657 y 0,158.

El Random Forest obtuvo AP 0,329 en validación cruzada, 0,334 en
validación y 0,328 en prueba; ROC-AUC 0,658 y Brier 0,158 en prueba.
Los mejores parámetros fueron profundidad máxima 20 y mínimo de 10 muestras
por hoja, con 120 árboles.

El boosting de histogramas obtuvo AP 0,336 en validación cruzada,
0,346 en validación y 0,339 en prueba; ROC-AUC 0,673 y Brier 0,156
en prueba. Superó a los otros candidatos en ranking y error
probabilístico en las dos particiones de evaluación. La diferencia
de AP de prueba frente al bosque fue **0,0112**; un bootstrap de 250
remuestreos por vivienda dio intervalo percentil 95 % de **0,0035 a
0,0183** para esa diferencia. El AP del boosting tuvo intervalo
**0,322 a 0,357**. Estos intervalos describen incertidumbre interna
en 2018; no prueban superioridad universal ni transferencia temporal.
XGBoost, LightGBM y CatBoost no estaban disponibles en el entorno.

## Umbral y errores

El umbral de 0,2012 se eligió en validación para maximizar F1 de la clase
operativa «sin acceso formal». Cada modelo recibió su propio umbral,
elegido con la misma regla en validación, antes de comparar sus métricas
de clasificación en prueba.
En prueba produjo:

- F1: **0,412**; precision: **0,297**; recall: **0,674**;
  especificidad: **0,574**.
- Matriz de confusión con filas reales y columnas predichas: **8.806**
  verdaderos negativos, **6.535** falsos positivos, **1.335** falsos
  negativos y **2.758** verdaderos positivos.
- Se marcarían **9.293 de 19.434 personas (47,8 %)**; cerca de 3 de cada 10
  marcadas corresponden a la clase «sin acceso».

Con 0,5, el mismo modelo casi nunca marca la clase minoritaria: recall
0,016 y F1 0,030 en prueba. Un programa con capacidad limitada debería
escoger su
umbral según costo, cobertura y recursos, no adoptar automáticamente el
umbral que maximiza F1. Por ejemplo, el decil de mayor riesgo contiene
aproximadamente **41,2 %** de casos etiquetados sin acceso formal frente
a **21,1 %** en la base completa, pero cubre solo cerca de una quinta
parte de todos los casos.

## Calibración, variables y subgrupos

El Brier de 0,156 mejora el 0,166 del baseline. Los deciles de probabilidad
predicha siguen de cerca sus frecuencias observadas; en el decil de mayor
riesgo el modelo predijo 40,7 % y se observó 41,2 %. La gráfica
`curvas.png` contiene ROC, precisión-recall y calibración.

La importancia por permutación medida en validación, expresada como caída de
AP, sitúa primero municipio (0,055), edad agrupada (0,050), lugar de
preparación de alimentos (0,020), nivel educativo (0,013), estrato (0,012)
y tamaño del hogar (0,011). Es **importancia predictiva**, no efecto
causal. La influencia del municipio indica que
parte del rendimiento podría depender de patrones territoriales de 2018.

En prueba, el recall para personas con dificultad funcional fue **0,430**
(n=3.448), frente a **0,711** para quienes no la reportaron (n=15.986). También
varió por sexo y municipio. Algunos municipios tienen muy pocos casos
positivos, por lo que sus tasas son inestables. Estas diferencias requieren
revisión antes de usar un umbral común en intervenciones.

## Recomendaciones para Bookdown y Dash

En Bookdown, documentar la definición exacta de la etiqueta, población
elegible, faltantes, claves de unión, exclusiones por fuga, partición por
vivienda, tuning, métricas de prueba y límites de interpretación. Citar el
diccionario oficial del DANE y aclarar que «sin acceso formal» incluye
conductas declaradas que no necesariamente prueban imposibilidad de acceso.

En Dash, mostrar prevalencias y métricas **agregadas**, curvas ROC/PR y
calibración, matriz de confusión y un control de umbral con los costos de
falsos positivos y negativos. Si se ofrece predicción, usar la lista de
variables, transformación y versión del modelo serializado, junto con
validación de entradas y una explicación de que no es una decisión clínica.
El artefacto `modelo_sin_acceso.joblib` acepta las 26 columnas en códigos
censales brutos e incorpora la normalización. El paquete `ml_salud` debe
estar instalado o disponible en `PYTHONPATH` donde se cargue.
Antes de un uso prospectivo, conseguir datos más recientes, validar por
periodo y geografía y revisar sesgos por grupo.

**Referencias:** [ficha CNPV 2018](https://microdatos.dane.gov.co/catalog/643),
[pregunta sobre tratamiento](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V582?name=P_QUEHIZO_PPAL),
[pregunta sobre atención](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V583?name=PA_LO_ATENDIERON),
[pregunta sobre enfermedad](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V581?name=P_ENFERMO).
