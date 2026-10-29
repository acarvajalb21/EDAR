# Modelo de acceso formal a salud — CNPV 2018, Atlántico

Este directorio contiene un experimento de clasificación reproducible sobre los
microdatos de personas, hogares y viviendas del CNPV 2018. El proyecto original
se leyó en modo de solo lectura desde
`C:\Users\Alejandro Carvajal\OneDrive\Documents\PROYECTO_DISCAPACIDAD`.
La app `app_dash/` de este repositorio es un ejemplo académico de créditos y
no forma parte del análisis de salud.

## Problema y población

La unidad es una persona del Atlántico que reportó un problema de salud en los
30 días previos al censo, sin hospitalización. Se reproduce exactamente la
definición de `ACCESO_FORMAL_SALUD` del notebook original:

- Acceso: acudió a la entidad de seguridad social y fue atendida, o acudió a un
  médico particular.
- Sin acceso: acudió a la entidad y no fue atendida, usó otra alternativa o no
  hizo nada.
- Los casos sin etiqueta definida se excluyen del entrenamiento y evaluación.

Para las métricas, la clase positiva es **`SIN_ACCESO=1`**, equivalente a
`ACCESO_FORMAL_SALUD=0`. Es una definición operativa de **no uso de EPS
atendida o médico particular**. La mayoría de ese grupo eligió otras acciones
o ninguna; la etiqueta no demuestra que un servicio les fuera negado.
Precision y recall describen la identificación de esta etiqueta.

La finalidad es **explorar asociaciones y ordenar perfiles para análisis**.
Como los datos son transversales de 2018, el modelo no establece causas ni
demuestra desempeño prospectivo para personas actuales.

## Variables y fugas

Se usan 26 variables de persona (edad agrupada, sexo, dificultad funcional,
educación, parentesco, etnia, municipio y clase), hogar (cuartos,
dormitorios, tamaño y condiciones de cocina) y vivienda (materiales, estrato,
servicios e internet). Los cruces se validan como muchos a uno.

Se excluyen `P_QUEHIZO_PPAL`, `PA_LO_ATENDIERON` y
`PA1_CALIDAD_SERV`, porque revelan directamente la respuesta o se conocen
después de la atención. Los identificadores, `P_ENFERMO` y cualquier copia de
la respuesta tampoco entran al modelo. `P_TRABAJO` y `PA_ASISTENCIA` se
excluyen del modelo principal: se miden en el mismo censo que la respuesta y
pueden reflejar consecuencias del episodio. El análisis de sensibilidad
compara su inclusión. La temporalidad de otras variables censales tampoco
está demostrada, de modo que el modelo sigue siendo retrospectivo.

Los códigos explícitos de «no informa» y los faltantes estructurales se
conservan como señal de ausencia, mediante un marcador o una categoría
explícita; los recuentos numéricos se imputan con la mediana calculada solo
en entrenamiento. Las categorías se codifican dentro de
cada pipeline, evitando aprender transformaciones con validación o prueba.

## Evaluación

La partición es estratificada y agrupada por vivienda: cinco séptimos para
entrenamiento, un séptimo para validación y un séptimo para prueba. La búsqueda
de hiperparámetros usa tres folds estratificados y agrupados **dentro del
entrenamiento**. Se optimiza Average Precision (AP) para la clase de interés;
el umbral que maximiza F1 se elige con validación. La prueba se consulta
después de seleccionar modelo y umbral.

Se comparan baseline de prevalencia, regresión logística regularizada,
Random Forest y boosting de histogramas. XGBoost, LightGBM y CatBoost no estaban
instalados en el entorno observado. El campo `pr_auc` del JSON es AP no
interpolada de scikit-learn, no el área trapezoidal de la curva. El informe
registra ROC-AUC, AP, F1,
precision, recall, matriz de confusión, Brier, calibración, importancia por
permutación y resultados por subgrupo. La importancia mide caída predictiva al
alterar una variable; no debe interpretarse causalmente.

## Ejecución

`requirements.txt` registra las versiones usadas con Python 3.14.6.
Instálalas en un entorno virtual antes de repetir el experimento.

```powershell
.\.venv\Scripts\python.exe -m ml_salud.entrenar --data-dir 'C:\Users\Alejandro Carvajal\OneDrive\Documents\PROYECTO_DISCAPACIDAD\data' --output-dir ml_salud\resultados
```

Los tres CSV originales se mantienen fuera de este directorio. Para repetir
el experimento en otro equipo, descargue los microdatos oficiales del DANE y
pase la carpeta con los archivos `CNPV2018_5PER_A2_08.CSV`,
`CNPV2018_2HOG_A2_08.CSV` y `CNPV2018_1VIV_A2_08.CSV` mediante
`--data-dir`. No distribuya los microdatos mediante un repositorio o Dash.

Los resultados quedan en `resultados/resultados.json`, las curvas en
`resultados/curvas.png` y el modelo serializado en
`resultados/modelo_sin_acceso.joblib`. El análisis detallado está en
`resultados/INFORME_MODELO.md` y el perfil de faltantes en
`resultados/perfil_calidad.json`. El archivo serializado solo se debe
cargar desde una fuente confiable y con versiones compatibles de Python y
scikit-learn.

El objeto `pipeline` dentro del modelo guardado acepta un `pandas.DataFrame`
con los **códigos censales brutos** de las variables indicadas en el campo
`features` del artefacto. Convierte centinelas, codifica e imputa
internamente. `pipeline.predict_proba(entrada)[:, 1]` devuelve la
probabilidad estimada para `SIN_ACCESO=1`. Para cargarlo desde otro
directorio, `ml_salud` debe estar instalado o en `PYTHONPATH`, porque el
artefacto referencia `ml_salud.esquema`. El artefacto guarda la firma
SHA-256 de ese archivo; mantén ambas piezas en la misma versión. Los
códigos imposibles y las columnas ausentes generan errores explícitos.
Ejecuta
`python -m ml_salud.pruebas` desde la raíz para comprobar el contrato.

## Uso posterior en Bookdown y Dash

En Bookdown conviene explicar primero la población, el código de la etiqueta,
las exclusiones por fuga, la partición por vivienda y los resultados en prueba.
En Dash se pueden mostrar prevalencias y resultados agregados por subgrupo,
las curvas ROC/PR y el umbral; cualquier formulario de predicción debe usar
exactamente las variables y transformaciones de `esquema.py`. No debe
exponerse una predicción individual como diagnóstico o decisión de acceso.

Fuente metodológica y diccionario:
[DANE, CNPV 2018](https://microdatos.dane.gov.co/catalog/643),
[tratamiento principal del problema de salud](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V582?name=P_QUEHIZO_PPAL),
[atención del problema de salud](https://microdatos.dane.gov.co/index.php/catalog/643/variable/F11/V583?name=PA_LO_ATENDIERON).
