# Evaluación técnica del modelo vigente (versión 2)

**Fuente:** microdatos anonimizados del CNPV 2018, departamento del Atlántico: personas, hogares, viviendas y `MGN`. Sus SHA-256 constan en `resultados.json`. La versión 1, de 26 variables, y su informe se conservan sin cambios en [`resultados_v1/`](../resultados_v1/INFORME_MODELO.md). La auditoría de datos, etiqueta y fugas de ese informe sigue vigente: la cohorte, la etiqueta y las particiones no cambiaron.

## Conclusión

Entre los modelos probados, se seleccionó **HistGradientBoostingClassifier** con tasa de aprendizaje 0,04, 15 hojas como máximo, mínimo de 30 observaciones por hoja y 500 iteraciones, sin parada temprana. Usa **28 variables**: las 26 de la versión 1 y dos de contexto de salud.

Ganó en validación con **AP = 0,386**. En la prueba interna obtuvo **AP = 0,375**, **ROC-AUC = 0,696** y **Brier = 0,152**, frente a AP 0,339, ROC-AUC 0,673 y Brier 0,156 de la versión 1. La prevalencia da AP = 0,211. La discriminación sigue siendo **moderada**. El modelo clasifica una conducta declarada en el censo de 2018; no está validado para decisiones individuales ni para datos actuales.

## Variables añadidas

- `HOGAR_OTROS_ENFERMOS`: otras personas del mismo hogar con `P_ENFERMO=1`.
- `SECCION_PCT_ENFERMOS`: proporción con `P_ENFERMO=1` entre las personas de la misma sección censal fuera del hogar, con respuesta válida (1 o 2). La sección procede de `CNPV2018_MGN_A2_08.CSV`.

Se calculan en [`contexto.py`](../contexto.py) con todas las personas del archivo censal. No usan `P_QUEHIZO_PPAL`, `PA_LO_ATENDIERON` ni la etiqueta. El artefacto de la versión 1 guarda la huella de `esquema.py`, así que ese archivo no se modificó.

## Cómo se adoptó

El [protocolo](../experimento_contexto/PROTOCOLO.md) se fijó antes de consultar la validación con estas variables. Los resultados están en [`decision.json`](../experimento_contexto/salidas/decision.json). Con los parámetros publicados de la versión 1, el candidato cumplió las cinco condiciones:

| Condición | Regla | Resultado |
|:--|:--|--:|
| Ganancia de AP en validación | ≥ 0,010 | 0,0373 (0,3461 a 0,3834) |
| Intervalo pareado del 95 % | Sobre cero | 0,0260 a 0,0492 |
| Brier en validación | No empeora más de 0,002 | Cumple |
| Ganancia en secciones no vistas (CV) | ≥ 0,010 | 0,0298 (0,3271 a 0,3568) |
| Sensibilidad con dificultad funcional en validación | No cae más de 0,03 | 0,436 a 0,432 |

Después se repitió con 28 variables el protocolo de `entrenar.py`: los mismos enfoques, la misma búsqueda de parámetros y selección en validación. La prueba se consultó una sola vez al final. Esa partición ya se había observado con la versión 1, por lo que es una evaluación interna y no confirmatoria.

## Comparación de modelos

| Modelo | AP CV | AP validación | AP prueba | ROC-AUC prueba | Brier prueba |
|:--|--:|--:|--:|--:|--:|
| Prevalencia | — | 0,211 | 0,211 | 0,500 | 0,166 |
| Regresión logística | 0,359 | 0,369 | 0,369 | 0,677 | 0,154 |
| Random Forest | 0,363 | 0,370 | 0,363 | 0,680 | 0,155 |
| Boosting de histogramas | 0,374 | 0,386 | 0,375 | 0,696 | 0,152 |

El intervalo interno del 95 % del AP del boosting fue **0,352 a 0,396**, por bootstrap de 250 remuestreos por vivienda. La diferencia frente al bosque fue 0,0119, con intervalo de 0,0048 a 0,0199. Estos intervalos no incluyen la incertidumbre de la selección. XGBoost, LightGBM y CatBoost no se evaluaron.

## Umbral y errores

El umbral de **0,2235** se eligió en validación para maximizar F1. En prueba:

- F1 **0,428**; precisión **0,331**; sensibilidad **0,606**; especificidad **0,673**.
- **10.324** verdaderos negativos, **5.017** falsos positivos, **1.613** falsos negativos y **2.480** verdaderos positivos.
- Marca a **7.497 de 19.434 personas (38,6 %)**, frente a 47,8 % de la versión 1.

Con 0,5, la sensibilidad es de apenas 0,052. Un programa con capacidad limitada debería escoger su umbral según costos y recursos, que este proyecto no define. Como referencia exploratoria:

| Se revisa | Personas | De la clase | Precisión | Sensibilidad | Lift |
|--:|--:|--:|--:|--:|--:|
| 5 % | 972 | 493 | 0,507 | 0,120 | 2,41 |
| 10 % | 1.944 | 906 | 0,466 | 0,221 | 2,21 |
| 20 % | 3.887 | 1.561 | 0,402 | 0,381 | 1,91 |

## Calibración y variables

El Brier de 0,152 mejora el 0,166 del baseline. En el decil de mayor riesgo se predijo 45,3 % y se observó 46,6 %.

La importancia por permutación en validación, medida como caída de AP, sitúa primero municipio (0,054), otras personas del hogar con problema de salud (0,052), edad (0,044) y proporción en la sección (0,030). Lugar de preparación de alimentos, educación y estrato quedan alrededor de 0,01. Es importancia predictiva, no efecto causal.

## Qué significan las variables nuevas

La clase operativa pasa de 15,7 % sin otras personas enfermas en el hogar a 33,5 % con tres o más. Lo que más sube es la autorreceta, de 7,2 % a 18,0 %; «no hizo nada» casi no cambia (2,2 % a 2,6 %).

La proporción de personas con problema de salud varía mucho entre secciones, más de lo que cabría esperar solo por morbilidad. **Hipótesis no comprobada:** estas variables pueden captar también problemas más leves o diferencias en quién respondió y cómo se recogió el dato. El censo no permite separar esas explicaciones. No deben leerse como barreras ni como causas. Se miden en el mismo censo que la respuesta: no revelan la acción de la persona, pero tampoco son previas al episodio.

## Subgrupos

Con su umbral, la sensibilidad fue **0,379** con dificultad funcional (n=3.448) y **0,641** sin ella (n=15.986). Ajustada por edad, 0,445 y 0,626. Entre personas de 60 años o más fue 0,116, frente a 0,682 entre menores de 60.

Frente a la versión 1, estas sensibilidades bajan porque el umbral marca a menos personas. La comparación justa usa el mismo número de marcadas:

| Escenario | Marcadas | Precisión | Sensibilidad | Con dificultad | Sin dificultad | 60 años o más |
|:--|--:|--:|--:|--:|--:|--:|
| Versión 1, su umbral | 9.293 | 0,297 | 0,674 | 0,430 | 0,711 | 0,103 |
| Versión 2, mismas marcadas | 9.293 | 0,306 | 0,695 | 0,498 | 0,725 | 0,193 |
| Versión 2, su umbral | 7.497 | 0,331 | 0,606 | 0,379 | 0,641 | 0,116 |

La versión 2 mejora en todos los grupos al marcar a las mismas personas, pero la brecha por dificultad funcional persiste y la sensibilidad entre mayores de 60 sigue siendo baja. Estas comparaciones son descriptivas y usan la prueba ya expuesta.

## Inferencia y límites

El artefacto `modelo_sin_acceso.joblib` acepta las 28 columnas, normaliza y valida la entrada. Requiere `ml_salud` en `PYTHONPATH`. Un formulario tendría que obtener `SECCION_PCT_ENFERMOS` sin publicar cifras de secciones pequeñas. La salida sería una puntuación experimental de 2018, no una decisión clínica.

La separación por vivienda mide generalización a otras viviendas de los mismos municipios y del mismo censo. No hay validación temporal, geográfica externa ni clínica. Antes de cualquier uso prospectivo se necesitarían datos más recientes y una revisión por grupos.

Versiones: Python 3.12.10, pandas 3.0.5, numpy 2.5.2 y scikit-learn 1.9.1.
