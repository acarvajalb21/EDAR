# Auditoría y mejora del modelo censal de salud

**Fecha:** 27 de octubre de 2026. **Decisión:** conservar el boosting de histogramas original. Ninguno de los cambios evaluados demostró una mejora de Average Precision (AP) consistente y suficiente para sustituirlo. Este trabajo no cambió los resultados originales, Bookdown, Dash ni Cloud Run.

## Alcance y referencia reproducida

Se leyeron los CSV originales de personas, hogares y viviendas en `PROYECTO_DISCAPACIDAD/data`, los dos notebooks del mismo proyecto, `ml_salud/entrenar.py`, `ml_salud/auditoria_sensibilidad.py`, `ml_salud/esquema.py`, el diccionario de `bookdown_salud/data/diccionario_modelo.csv`, las fuentes Bookdown y los JSON que alimentan Dash. No existe un repositorio Git en la carpeta DATAVIZ; por eso los ensayos se aislaron aquí y los archivos de `ml_salud/resultados/` permanecieron intactos.

Las tres huellas SHA-256 de los CSV coinciden con `resultados.json`. Se reprodujeron **2.342.265** personas fuente, **136.114** con problema de salud declarado, **80** sin etiqueta clasificable y **136.034** en la cohorte. La clase operativa positiva tiene **28.650** casos (21,06 %). Los **136.034** registros enlazan a un hogar y una vivienda con cardinalidad muchos a uno; no hay claves de persona duplicadas. Las particiones reproducidas tienen **97.167/19.433/19.434** personas y **63.927/12.718/12.695** viviendas en entrenamiento/validación/prueba, sin viviendas compartidas. Las medianas numéricas del artefacto coinciden con las calculadas solo en entrenamiento.

La [auditoría adicional de claves fuente](salidas/claves_fuente.json) halló **cero claves duplicadas** en los tres CSV. Fuera de la cohorte, `P_NROHOG` está vacío en 5.831 filas de personas y `H_NROHOG` en 261 filas de hogares; esos vacíos no se ocultaron ni imputaron para el modelo. Entre las **136.114** personas que declararon el problema de salud, **ninguna** tiene una clave de unión incompleta. Las claves de vivienda por tupla y por el identificador de grupo construido dieron ambas **89.394 viviendas** en esa población, sin colisiones observadas. Los componentes de la clave de vivienda están completos en el archivo de viviendas. Por tanto, los vacíos de hogar en el universo fuente no contaminan esta evaluación.

El artefacto original devolvió en validación AP **0,3460616070**, ROC-AUC **0,6723277641** y Brier **0,1557329315**, iguales al JSON archivado. Al reajustar el boosting original en entrenamiento, la máxima diferencia absoluta entre probabilidades de validación y el artefacto fue **0,0**. La prueba histórica también reprodujo AP **0,3387606364**, ROC-AUC **0,6728291332** y Brier **0,1560337452**. Se trata de una prueba interna **ya expuesta** en el proyecto, no de una evaluación externa confirmatoria.

## Diagnóstico del pipeline original

1. **Etiqueta y uso.** El notebook y `load_data()` aplican la misma regla. `SIN_ACCESO=1` agrupa **1.907** personas que acudieron a la EPS y no recibieron atención, y **26.743** que reportaron otra acción principal o ninguna. La [pregunta del DANE sobre tratamiento](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V582?name=P_QUEHIZO_PPAL) incluye farmacia, terapias, curanderos, remedios caseros y autorreceta; la etiqueta no mide una denegación general ni ausencia de toda atención. La base local contiene 61 valores `P_QUEHIZO_PPAL=0` no clasificables y ningún 99 entre quienes declararon problema, mientras la ficha del DANE lista 99 como «No Informa». Se conservaron fuera de la cohorte según la regla original; esta diferencia de codificación del archivo debe documentarse, no recodificarse sin evidencia.
2. **Uniones y fuga.** Las claves incluyen departamento, municipio, clase, encuesta, vivienda, hogar y persona según corresponde. El código valida la unicidad de hogar/vivienda y exige cruces completos. Los componentes de la etiqueta (`P_QUEHIZO_PPAL`, `PA_LO_ATENDIERON`) y `PA1_CALIDAD_SERV` quedan excluidos, junto con identificadores y `P_ENFERMO`; `P_TRABAJO` y `PA_ASISTENCIA` continúan fuera del modelo principal. No se detectó fuga directa en las 26 entradas. La simultaneidad del censo impide asegurar temporalidad previa para todas las covariables.
3. **Validación y transformaciones.** `StratifiedGroupKFold` conserva viviendas completas tanto en la partición de 7 pliegues como en la CV de 3 pliegues dentro de entrenamiento. `ColumnTransformer`, imputación y codificación forman parte de cada pipeline ajustado en los pliegues. En boosting, `OrdinalEncoder` produce índices de categoría y `categorical_features` le indica al estimador que son nominales; el modelo no trata municipio o sexo como magnitudes numéricas. `P_EDADR` sí entra como edad ordenada. El campo archivado `pr_auc` contiene `average_precision_score`, **no** el área trapezoidal PR; conviene renombrarlo `average_precision` en una futura versión de resultados, sin reescribir el archivo histórico.
4. **Faltantes.** El preprocesamiento original reúne blancos y centinelas explícitos en una categoría para variables nominales. En la cohorte, por ejemplo, `P_EST_CIVIL` tiene **21.377** blancos y **220** códigos explícitos 9; `P_ALFABETA` tiene **12.977** blancos y **290** códigos 9. El [cuestionario del DANE](https://microdatos.dane.gov.co/catalog/643) aplica alfabetismo desde los 5 años y estado civil desde los 10, por lo que un blanco puede reflejar «no aplica». Se ensayó separar el centinela explícito del blanco sin asumir que todo blanco tuviera una sola causa. Ese cambio no mejoró la validación. Para recuentos, `SimpleImputer(add_indicator=True)` conserva una señal de ausencia y aprende la mediana solo en entrenamiento.

## Protocolo y resultados nuevos

El [protocolo fijado antes de entrenar](PROTOCOLO.md) prioriza AP, usa semilla 42 para la partición y 43 para los tres pliegues agrupados. Cada variante cambia un aspecto acotado; el entrenamiento principal conserva la misma población y etiqueta. Todos los modelos nuevos son `HistGradientBoostingClassifier` sin parada temprana: tasa 0,04, mínimo 30 por hoja y, salvo la variante regularizada, 31 hojas y 320 iteraciones. La variante regularizada usa 15 hojas y 240 iteraciones. `personas_por_dormitorio` divide tamaño del hogar por dormitorios del hogar, dos campos definidos en el [diccionario de hogares del DANE](https://microdatos.dane.gov.co/index.php/catalog/643/data-dictionary/F9?file_name=HOGARES); denominadores cero o no informados producen faltante, imputado dentro de cada pliegue. No se utilizaron SMOTE, pesos automáticos ni codificación por objetivo.

La comparación original archivada, verificada contra sus archivos, fue:

| Modelo original | AP CV | AP validación | AP prueba histórica | Brier prueba |
|:--|--:|--:|--:|--:|
| Prevalencia | — | 0,211 | 0,211 | 0,166 |
| Regresión logística | 0,321 | 0,329 | 0,330 | 0,158 |
| Random Forest | 0,329 | 0,334 | 0,328 | 0,158 |
| Boosting de histogramas | 0,336 | 0,346 | 0,339 | 0,156 |

| Ensayo | AP CV (3 pliegues) | AP validación | Brier validación | Tiempo ensayo |
|:--|--:|--:|--:|--:|
| Boosting original reproducido | 0,336373 | 0,346062 | 0,155733 | 17,5 s |
| Centinela explícito separado del blanco | 0,336684 | 0,345238 | 0,155786 | 26,4 s |
| Personas por dormitorio | 0,335236 | 0,344768 | 0,155816 | 23,0 s |
| Ambos cambios | 0,334843 | 0,344067 | 0,155880 | 24,9 s |
| Edad como categoría + personas por dormitorio | 0,333616 | 0,344691 | 0,155874 | 26,4 s |
| Boosting más regularizado | 0,334843 | 0,344802 | 0,155907 | 16,4 s |

El registro completo contiene AP de cada pliegue, parámetros, versiones y tiempos en [`salidas/experimentos.json`](salidas/experimentos.json). La ejecución completa duró **232,0 segundos** en este equipo. La [tabla CSV](salidas/comparacion_modelos.csv) distingue el protocolo original archivado (prevalencia, logística, Random Forest y boosting) de los ensayos nuevos y señala la partición. CatBoost, LightGBM y XGBoost no estaban instalados; la [comprobación de dependencias](DEPENDENCIAS.md) sin modificar el entorno falló porque la conexión local a PyPI estaba bloqueada. No se atribuye a ellos ningún resultado.

La mejor variante nueva por AP media de CV fue separar blancos y centinelas, con una ventaja de apenas **0,000311** en CV. En validación obtuvo **0,345238**, es decir, **−0,000823** respecto al original. Un bootstrap pareado de **250** remuestreos de viviendas completas dio intervalo percentil 95 % **[−0,003495; 0,001741]** para esa diferencia. La regla predefinida pedía ganancia de al menos 0,010, límite inferior del intervalo por encima de cero y Brier sin empeoramiento superior a 0,002. No se cumplió. La calibración Platt, ajustada con predicciones fuera de pliegue **solo del entrenamiento**, dejó AP igual y cambió Brier en validación de **0,155733** a **0,155738**; tampoco se adoptó. No se usó la prueba histórica para escoger entre variantes.

### Segunda ronda solicitada

Se fijó una [ampliación del protocolo](PROTOCOLO.md) antes de ejecutarla: tres ajustes del boosting y una mezcla de peso fijo con logística. Se conservaron la misma cohorte, los mismos pliegues de entrenamiento y la misma regla de sustitución. Los [resultados íntegros](salidas/ampliacion.json) registran parámetros, semillas, versiones, pliegues y tiempos; la ejecución duró **284,8 segundos**.

| Variante adicional | AP CV | AP validación | Brier validación | Tiempo ensayo |
|:--|--:|--:|--:|--:|
| Regularización L2=1 | 0,335610 | 0,345646 | 0,155749 | 23,6 s |
| Fracción de variables 0,7 | 0,336378 | 0,346899 | 0,155641 | 21,8 s |
| Tasa 0,025 y 500 iteraciones | 0,335307 | 0,345564 | 0,155666 | 32,7 s |
| Mezcla fija: 75 % boosting, 25 % logística | 0,336895 | 0,346437 | 0,155694 | 37,6 s |

La fracción de variables 0,7 obtuvo el mayor AP numérico de validación, **solo 0,000838** por encima del original, mientras su media de CV fue prácticamente idéntica. La mezcla ganó por AP media de CV, con diferencia **+0,000522**; en validación mejoró **+0,000376**. El bootstrap pareado por vivienda para la mezcla dio intervalo 95 % **[−0,001699; 0,002167]**. La ventaja es pequeña e incierta, lejos del mínimo predefinido de 0,010. No se consultó la prueba histórica para elegir en esta ronda y se conserva el original. Dado que esta segunda ronda se solicitó después de observar la primera validación, cualquier ganancia sería exploratoria incluso si hubiera superado una regla numérica.

## Utilidad, calibración y grupos

Al conservar el original, la comparación final sobre la prueba histórica vuelve a medir el mismo modelo. La precisión-recall, calibración, matriz de confusión y umbral se mantienen iguales a las cifras archivadas. El umbral **0,201219** se eligió en validación por F1 y aquí solo sirve para describir errores: en prueba, precisión **0,297**, sensibilidad **0,674**, F1 **0,412**, TN **8.806**, FP **6.535**, FN **1.335** y TP **2.758**. Señalaría **9.293** de **19.434** personas. No se declara óptimo para una intervención sin capacidad ni costos definidos.

Como alternativas exploratorias de priorización, ordenar por probabilidad y resolver empates por la posición original produce:

| Fracción revisada | Personas revisadas | Positivos hallados | Precisión | Sensibilidad | Lift sobre prevalencia |
|--:|--:|--:|--:|--:|--:|
| 5 % | 972 | 427 | 0,439 | 0,104 | 2,086 |
| 10 % | 1.944 | 801 | 0,412 | 0,196 | 1,956 |
| 20 % | 3.887 | 1.418 | 0,365 | 0,346 | 1,732 |

La [figura original de ROC, precisión-recall y calibración](../resultados/curvas.png) y los deciles están en [`salidas/comparacion_historica.json`](salidas/comparacion_historica.json). En el decil superior se predijo **0,407** y se observó **0,412**; esto no demuestra calibración prospectiva. El Brier en prueba fue **0,1560**, frente al **0,1663** de prevalencia.

El [CSV de subgrupos](salidas/subgrupos_prueba_historica.csv) informa denominador, positivos, AP, precisión, sensibilidad e intervalo Wilson de 95 % por dificultad, sexo, grupo de edad quinquenal y municipio cuando hay al menos 50 personas y 10 positivos. Los intervalos Wilson describen variación binomial de cada grupo y no ajustan dependencia dentro de vivienda ni selección previa del modelo. Ejemplos importantes:

- **Dificultad funcional declarada:** 3.448 personas, 544 positivas, sensibilidad **0,430** [0,389; 0,472]; sin dificultad: 15.986 personas, 3.549 positivas, sensibilidad **0,711** [0,696; 0,726].
- **Sexo registrado:** código 1, 8.311 personas y 1.911 positivas, sensibilidad **0,710** [0,689; 0,730]; código 2, 11.123 personas y 2.182 positivas, sensibilidad **0,642** [0,622; 0,662].
- **Municipios mayores en prueba:** código 1, 9.061 personas y 1.992 positivas, sensibilidad **0,686** [0,666; 0,706]; código 758, 3.757 personas y 837 positivas, **0,675** [0,643; 0,706]. Las tasas de municipios pequeños tienen mucha más incertidumbre y deben leerse con sus denominadores.

La [revisión de la brecha por edad](salidas/brecha_dificultad.json) y su [figura con denominadores](salidas/brecha_dificultad.png) muestran que la sensibilidad cruda entre los dos grupos de dificultad difiere **28,1 puntos porcentuales**. Al estandarizar descriptivamente por la distribución de edad de los positivos en tres bandas, queda **0,498** frente a **0,695**, una brecha de **19,7 puntos**. Por ejemplo, entre mayores de 60 años, la sensibilidad es baja en ambos grupos: 14/161 (0,087) y 43/392 (0,110). La composición por edad explica parte de la diferencia, pero no toda. El análisis no permite inferir causa ni concluir discriminación con una sola métrica; merece una revisión específica antes de cualquier uso operativo.

## Transferencia territorial y límites

Una [sensibilidad separada](salidas/territorio.json) retiró del ajuste, uno por uno, los tres municipios más numerosos del entrenamiento histórico; el modelo omitió `U_MPIO` para no usar una categoría territorial desconocida. Se obtuvo AP **0,297** frente a prevalencia **0,213** en municipio código 1 (n=44.834), AP **0,306** frente a **0,219** en código 758 (n=19.065) y AP **0,349** frente a **0,283** en código 433 (n=6.042). Las ROC-AUC respectivas fueron **0,622**, **0,630** y **0,606**. El experimento duró **84,8 segundos**; semilla y versiones constan en el JSON. Cambian tamaño de ajuste, prevalencia y población; estas cifras responden a transferencia a municipios no vistos y **no son directamente comparables** con el test habitual de viviendas nuevas dentro de municipios representados.

Los intervalos pareados de AP condicionan en predicciones de modelos fijos; no incluyen incertidumbre por ajuste, búsqueda y selección. La prueba histórica se había observado en una revisión anterior. No hay validación externa, temporal ni costo de errores definido. Por ello, incluso una pequeña ganancia interna no bastaría para decisiones sobre personas actuales.

## Reproducción e integración futura

Desde la raíz de DATAVIZ, con el entorno `.venv` y los CSV originales disponibles:

```powershell
$datos = 'C:\Users\Alejandro Carvajal\OneDrive\Documents\PROYECTO_DISCAPACIDAD\data'
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.ejecutar --data-dir $datos
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.auditar_claves --data-dir $datos
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.ampliacion --data-dir $datos
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.territorio --data-dir $datos
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.brecha_dificultad --data-dir $datos
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.graficar_brecha
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.resumir
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.verificar_artefacto --data-dir $datos
.\.venv\Scripts\python.exe -m ml_salud.experimentos_2026_10.pruebas
```

El [artefacto candidato separado](salidas/candidato_separado.joblib) contiene el clasificador seleccionado, su transformación desde los 26 códigos censales brutos y, si se adopta, el calibrador; en esta ejecución contiene el **modelo original**, porque ninguna variante pasó la regla de sustitución. Se carga con `joblib.load` únicamente desde esta fuente confiable y con versiones compatibles; `artefacto['predictor'].predict_proba(entrada_bruta)[:, 1]` devuelve la probabilidad de `SIN_ACCESO=1`.

Si un candidato futuro superara el protocolo y una revisión metodológica, habría que regenerar `dash_salud/data/modelo.json` con `dash_salud/generar_datos.py`, actualizar `bookdown_salud/05-modelo.Rmd` y las tablas de `bookdown_salud/scripts/preparar_resumen.py`, renderizar el libro, verificar las visualizaciones y recién entonces decidir una nueva publicación. Aquí no se reemplazó ni desplegó el modelo público.
