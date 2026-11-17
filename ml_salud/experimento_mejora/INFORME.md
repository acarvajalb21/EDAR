# Búsqueda de mejora material del modelo de acceso (noviembre de 2026)

## 1. Protocolo (fijado el 2026-11-12 a las 17:45, antes de consultar la validación)

Esta sección se escribió antes de ejecutar ningún modelo nuevo y no se modifica después.

**Pregunta.** ¿Puede el modelo vigente (versión 2, boosting de histogramas con 28 variables, AP de validación archivada 0,386) mejorar de forma material con otro algoritmo o con información territorial nueva sin fuga?

**Población, etiqueta y particiones.** Las mismas de `entrenar.py`: cohorte de 136.034 personas, clase positiva `SIN_ACCESO=1`, `load_data(..., with_context=True)`, `prepare_features_v2`, `group_ids` y `split_three` (semilla 42). La **prueba no se consulta**. La selección usa CV de 3 pliegues `StratifiedGroupKFold` agrupada por vivienda dentro de entrenamiento (semilla 43, los mismos pliegues para todos los candidatos). La validación solo compara el candidato preseleccionado con la v2 y describe las demás variantes.

**Métrica principal.** Average Precision (`average_precision_score`, no área trapezoidal). Secundarias: ROC-AUC y Brier.

**Familia de variantes (exploratoria).**

1. *LightGBM con categóricas nativas* sobre las 28 variables v2. Rejilla: `num_leaves` {15, 31, 63} × `learning_rate` {0,02; 0,05} × `min_child_samples` {20, 100} × `class_weight` {None, balanced} × `n_estimators` {200, 400, 700, 1000} (evaluados por predicción escalonada del mismo ajuste). Fijos: `colsample_bytree=0,8`, `reg_lambda=1`, semilla 42.
2. *Codificación por objetivo territorial*: tasa suavizada de `SIN_ACCESO` en la sección censal (F1) y además en la manzana (F2), con su conteo de base. Se calcula solo con etiquetas del conjunto de ajuste: para filas de ajuste, fuera de pliegue con 5 pliegues internos por vivienda (semilla 45), de modo que nunca entra la propia vivienda ni su hogar; para filas evaluadas, con todo el conjunto de ajuste. Suavizado bayesiano `(S + m·p)/(N + m)` con `m = 20` y `p` la prevalencia de la fuente.
3. *Agregados territoriales sin etiqueta* calculados con todo el censo, excluyendo la propia vivienda: % con dificultad funcional, nivel educativo medio, % de 60 años o más, estrato medio, % con internet y tamaño (log) de la sección, más % con problema de salud en la manzana. F3 = F2 + agregados; F4 = v2 + agregados (sin etiquetas).

Cada conjunto F0–F4 se evalúa con el boosting de la v2 (mismos hiperparámetros) y con las 3 mejores configuraciones LightGBM de la rejilla 1 por AP media de CV.

**Candidato único para la decisión.** El de mayor AP media en CV por vivienda entre todas las combinaciones. Se ajusta en todo el entrenamiento y se compara con la v2 reproducida en validación.

**Regla de adopción (del proyecto, sin cambios).** Se recomienda una versión 3 solo si se cumplen todas:

1. Ganancia de AP en validación (candidato − v2; positivo favorece al candidato) ≥ 0,010.
2. Intervalo percentil 95 % de esa diferencia por bootstrap pareado de viviendas completas (semilla 44, 250 réplicas, AP recalculado en cada réplica) enteramente sobre cero.
3. Brier de validación del candidato no peor que el de la v2 en más de 0,002.

Se informan además, sin ser condición nueva: sensibilidad del grupo con dificultad funcional (regla anterior: no cae más de 0,03), CV agrupada por **sección censal** del candidato y de la v2 (dependencia espacial) y métricas con umbral F1 elegido en validación. Ese umbral se elige y mide en la misma validación, por lo que esas cifras son optimistas.

**Límites declarados.** El intervalo bootstrap está condicionado a modelos ya entrenados: no incluye la variabilidad del entrenamiento ni la de la selección entre variantes. La desviación entre pliegues no es un intervalo. La codificación por sección presupone que, al usar el modelo, se conocen etiquetas de otras viviendas de la misma sección del mismo censo; no aplica a secciones sin etiquetas ni a otro año. Presupuesto aproximado: 40 minutos de cómputo.

## 2. Resultados (ejecutados el 2026-11-12; la prueba no se consultó)

La v2 reproducida coincide con lo archivado: AP de CV 0,37417 y AP de validación 0,386054 (comprobación automática con tolerancia 1e-9). La ejecución principal duró 1.454 s: carga y agregados 137 s, rejilla 801 s, conjuntos 418 s, validación y bootstrap 77 s, CV por sección 23 s. Se evaluaron 149 combinaciones en CV; en validación se ajustaron 10 (por conjunto, la HGB y la mejor LightGBM en CV) más la prevalencia.

| Variante | AP CV (media ± de) | AP val. | ROC-AUC val. | Brier val. |
|:--|--:|--:|--:|--:|
| Prevalencia | — | 0,211 | 0,500 | 0,1662 |
| **F0 v2 (HGB, referencia)** | 0,374 ± 0,004 | 0,386 | 0,701 | 0,1514 |
| F0 LightGBM (nl63, lr 0,02, mc100, 400) | 0,378 ± 0,006 | 0,389 | 0,705 | 0,1509 |
| F1 +TE sección, HGB | 0,392 ± 0,001 | 0,406 | 0,722 | 0,1483 |
| F1 +TE sección, LightGBM | 0,394 ± 0,004 | 0,408 | 0,723 | 0,1482 |
| F2 +TE sección y manzana, HGB | 0,407 ± 0,002 | 0,427 | 0,741 | 0,1453 |
| F2 +TE sección y manzana, LightGBM | 0,410 ± 0,004 | 0,428 | 0,741 | 0,1451 |
| F3 F2 + agregados, HGB | 0,410 ± 0,001 | 0,426 | 0,741 | 0,1453 |
| **F3 F2 + agregados, LightGBM (candidato)** | **0,413 ± 0,005** | **0,429** | **0,742** | **0,1450** |
| F4 v2 + agregados sin etiqueta, HGB | 0,395 ± 0,001 | 0,406 | 0,717 | 0,1489 |
| F4 v2 + agregados sin etiqueta, LightGBM | 0,402 ± 0,002 | 0,414 | 0,727 | 0,1474 |

La desviación entre pliegues describe dispersión, no es un intervalo. En la rejilla, `class_weight=balanced` nunca mejoró la AP de CV y `min_child_samples=100` fue mejor en todas las combinaciones.

**Comparación preregistrada** (candidato F3-LightGBM `num_leaves=31, learning_rate=0,02, min_child_samples=100, n_estimators=400`, menos v2): ΔAP = **+0,0429**, IC 95 % **[0,0318; 0,0539]**; ΔROC-AUC +0,041 [0,033; 0,048]; ΔBrier −0,0064 [−0,0076; −0,0052]. Se remuestrearon 12.718 viviendas en 250 réplicas (semilla 44), sin réplicas fallidas. El intervalo está condicionado a los modelos entrenados: no incluye la variabilidad del entrenamiento ni la de la selección entre 149 combinaciones. **Las tres condiciones se cumplen.**

**Umbral F1 elegido y medido en la misma validación (optimista):**

| Modelo | Umbral | Precisión | Sensibilidad | F1 | Exactitud | Exact. balanceada | Especificidad | Marcados |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| v2 | 0,2235 | 0,335 | 0,613 | 0,433 | 0,662 | 0,644 | 0,675 | 38,6 % |
| Candidato | 0,2307 | 0,370 | 0,648 | 0,471 | 0,693 | 0,677 | 0,705 | 36,9 % |

Con un umbral de 0,5, la sensibilidad es 0,051 en la v2 y 0,119 en el candidato. La sensibilidad con dificultad funcional, cada modelo con su umbral, pasa de 0,388 a 0,473.

**Dependencia espacial (CV de 3 pliegues por sección censal dentro de entrenamiento):** v2 0,359 ± 0,016; candidato F3 **0,350** ± 0,010. En un complemento exploratorio decidido tras ver la validación (`complemento.py`), F4-HGB obtuvo 0,362 y F4-LightGBM 0,360. En secciones sin etiquetas el candidato **empeora** (−0,009) y los agregados sin etiqueta apenas suman (+0,002 o +0,003). La regla 4 del protocolo de octubre (ganancia ≥ 0,010 con secciones no vistas) **no se cumpliría**.

## 3. Interpretación

Toda la mejora material procede de la información territorial fina: la conducta declarada por otras viviendas de la misma manzana o sección. Se calcula sin fuga respecto de la persona y de su vivienda, y la CV (+0,039) concuerda con la validación (+0,043). Sin embargo, esa información no se transfiere a secciones sin etiquetas. Los agregados sin etiqueta tampoco ayudan fuera de su sección: probablemente funcionan como huella de una sección ya vista. Por tanto, el candidato mide sobre todo un **efecto de conglomerado** dentro del mismo censo. Puede reflejar oferta local de servicios, pero también la forma de empadronar o de responder en cada zona. El censo no permite separar esas explicaciones.

LightGBM aporta poco por sí mismo (+0,003 en validación). La dificultad está en los datos: la etiqueta mezcla autorreceta, farmacia y no hacer nada, y no hay gravedad del problema ni oferta de servicios. En el encabezado de personas tampoco se observó una variable de afiliación. Además, el porcentaje es 21 %, por lo que una AP de 0,39 a 0,43 equivale a 1,8 a 2 veces la prevalencia. La sensibilidad de 0,05 con umbral 0,5 es un efecto del umbral, no una ausencia de señal.

**Recomendación.** Una versión 3 con codificación territorial solo se justifica si el uso declarado es ordenar personas **del mismo censo de 2018 en zonas con etiquetas conocidas**. Debe documentarse como tal y repetir antes el protocolo completo de `entrenar.py`. Para cualquier uso en zonas nuevas o en otro período, la v2 ya está cerca del techo de estas variables.

Límites adicionales: en las filas de ajuste, el conteo `N_*` usa el 80 % del conjunto (pliegues internos) y en las evaluadas el 100 %. No se probaron otros valores de `m` ni XGBoost o CatBoost. Este informe no modifica `resultados/`, Bookdown ni Dash.

## 4. Archivos y reproducción

Desde `proyecto_salud/`:

```powershell
ml_salud\.venv\Scripts\python.exe -m pip install lightgbm==4.7.0   # única dependencia nueva
ml_salud\.venv\Scripts\python.exe -m ml_salud.experimento_mejora.ejecutar --data-dir datos
ml_salud\.venv\Scripts\python.exe -m ml_salud.experimento_mejora.complemento --data-dir datos
```

Salidas en `salidas/`: `cv_rejilla_lightgbm.json`, `cv_todas.json` (AP por pliegue de las 149 combinaciones), `validacion.json` (tabla, bootstrap, umbrales y criterios), `cv_seccion.json`, `cv_seccion_complemento.json`, `ejecucion.json` (semillas, versiones, huellas y tiempos), `registro.txt` y `predicciones_validacion.csv.gz`. Este último contiene la fila de la cohorte, un índice de vivienda sin claves censales, la etiqueta y las probabilidades de la v2 y del candidato, para revisión estadística. Versiones: Python 3.12.10, pandas 3.0.5, numpy 2.5.2, scikit-learn 1.9.1 y LightGBM 4.7.0.
