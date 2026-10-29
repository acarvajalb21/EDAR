# DATAVIZ · Salud en el Atlántico — Bookdown

Este repositorio contiene el **informe Bookdown vigente** del proyecto de Alejandro Carvajal y Mateo Chang. El [libro publicado](https://acarvajalb21.github.io/EDAR/) se genera desde `index.Rmd` y los capítulos `01`–`07`; `docs/` conserva el HTML listo para GitHub Pages. El antiguo archivo `EDA_acceso_salud_Atlantico_CNPV2018.Rmd` permanece como antecedente, pero no forma parte del libro actual.

La pregunta del informe es qué patrones se observaron entre las personas del Atlántico que declararon un problema de salud en los 30 días previos al CNPV 2018, sin hospitalización, y hasta dónde permite clasificarlas la regla operativa `ACCESO_FORMAL_SALUD`. La cohorte tiene **136.034 personas**. La categoría `ACCESO_FORMAL_SALUD = 0` reúne **28.650 (21,06 %)**: 1.907 acudieron a su EPS y no fueron atendidas; las demás reportaron otra acción principal o ninguna. **No equivale a una tasa general de atención denegada ni de necesidad médica insatisfecha.**

## Estructura vigente

- `index.Rmd`, `01`–`07-*.Rmd`, `_bookdown.yml`, `_output.yml`, `style.css`: fuentes y configuración del libro.
- `data/`: cuadros **agregados** para reproducir las tablas; no contiene registros individuales.
- `figures/`: gráficos del análisis y del modelo.
- `scripts/`: preparación de agregados y auditoría.
- `ml_salud/`: copia del pipeline y resultados que permiten regenerar el libro de forma independiente; la misma versión se entrega en EDAPYTHON.
- `docs/`: HTML compilado que publica GitHub Pages.

El [Dash actual](https://dataviz-salud-atlantico-409319239507.us-east1.run.app/) y el código del modelo están en [EDAPYTHON](https://github.com/acarvajalb21/EDAPYTHON), carpetas `dash_salud/` y `ml_salud/`. El informe técnico de la [auditoría de octubre de 2026](https://github.com/acarvajalb21/EDAPYTHON/blob/main/ml_salud/experimentos_2026_10/INFORME_AUDITORIA.md) explica por qué se conserva el modelo original. El antiguo `dashboard/` de este repositorio es un entregable anterior.

## Reproducir el libro

Para leer el informe no hacen falta los microdatos: abra `docs/index.html` o el enlace publicado. Para volver a compilarlo, instale R, Pandoc y los paquetes `bookdown`, `rmarkdown` y `knitr`; luego, desde la raíz del repositorio:

```powershell
Rscript build_bookdown.R
```

`build_bookdown.R` escribe en `docs/`. Para **regenerar** las tablas y figuras desde cero se necesitan además Python, las dependencias de `ml_salud` y los tres CSV departamentales del CNPV 2018 del DANE (`5PER`, `2HOG`, `1VIV`, departamento 08). Ejecute desde la raíz `python scripts/preparar_resumen.py --data-dir RUTA_CSV_DANE` y luego `python scripts/preparar_auditoria.py`. Los scripts verifican las huellas de los archivos. Los microdatos originales no se suben a GitHub.

**Estado metodológico:** el modelo es retrospectivo y su validación se limita al censo 2018. No se ha demostrado que sus patrones sirvan para decisiones sobre personas actuales. Antes de redefinir la pregunta o la etiqueta del proyecto hace falta comprobar la viabilidad de una fuente que observe barreras reales de atención.

Fuente: [DANE, CNPV 2018](https://microdatos.dane.gov.co/catalog/643).
