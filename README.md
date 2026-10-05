# EDA de acceso a atención formal en salud en el Atlántico (R)

Autores: Alejandro Carvajal y Mateo Chang

Repositorio: [acarvajalb21/EDAR](https://github.com/acarvajalb21/EDAR). El libro HTML compilado está en `docs/`.

**Libro publicado:** [Acceso a atención formal en salud en el Atlántico](https://acarvajalb21.github.io/EDAR/).

Este libro Bookdown describe el acceso a atención formal entre las personas censadas en el Atlántico que reportaron un problema de salud en los 30 días anteriores al CNPV 2018 y cuya respuesta pudo clasificarse. El análisis es descriptivo; las asociaciones observadas no establecen causas.

El análisis completo está en [el archivo R Markdown](EDA_acceso_salud_Atlantico_CNPV2018.Rmd). La versión de la misma pregunta en Python está en [EDAPYTHON](https://github.com/Mateochang82/EDAPYTHON).

## Archivos

- `index.Rmd`: portada y presentación del libro.
- `EDA_acceso_salud_Atlantico_CNPV2018.Rmd`: capítulo con código, método, diccionario, tablas y conclusiones.
- `_bookdown.yml`, `_output.yml` y `book.css`: orden de capítulos, formato y estilos.
- `EDAR.Rproj`: proyecto para abrir en RStudio y usar Build Book.
- `docs/`: libro HTML compilado; abra `docs/index.html` para leerlo localmente.
- `figuras/`: nueve gráficas en PNG, incluido el mapa municipal con nombres.
- `datos/mgn2018_municipios_atlantico.geojson`: 23 polígonos del MGN integrado 2018 del DANE.
- `salidas/`: base analítica y resumen municipal generados por el análisis.

## Microdatos y ejecución

Los microdatos no se incluyen en el repositorio. Para reejecutar el análisis, coloque estos tres archivos del CNPV 2018, departamento del Atlántico (08), en `datos/`:

```text
CNPV2018_1VIV_A2_08.CSV
CNPV2018_2HOG_A2_08.CSV
CNPV2018_5PER_A2_08.CSV
```

El capítulo también reconoce esos CSV en la carpeta `datos/` del proyecto Python vecino dentro de `DataViz_2026`. Para reconstruir el libro en otro equipo, coloque los archivos en este proyecto. Se necesitan `tidyverse`, `scales`, `knitr`, `rmarkdown`, `jsonlite` y `bookdown`.

```r
install.packages(c("tidyverse", "scales", "knitr", "rmarkdown", "jsonlite", "bookdown"))
bookdown::render_book("index.Rmd", "bookdown::gitbook")
```

En RStudio, abra `EDAR.Rproj` y use Build → Build Book. También puede ejecutar el script de compilación desde la raíz del proyecto:

```powershell
& "C:\Program Files\R\R-4.4.1\bin\Rscript.exe" build_bookdown.R
```

El libro se compiló y verificó el 5 de octubre de 2026 con R 4.4.1 y los tres CSV departamentales. La carpeta `docs/` contiene una versión lista para publicarse sin distribuir los microdatos. El flujo de GitHub Pages publica esa carpeta al actualizar `main`; los CSV no se cargan a GitHub.

## Cifras de control

- Personas en el archivo departamental: 2.342.265.
- Reportaron problema de salud: 136.114.
- Respuesta clasificable: 136.034.
- Accedieron a atención formal: 107.384 (78,94 %).
- No accedieron: 28.650 (21,06 %).
- Municipios representados en el mapa: 23.
- Diferencia por dificultad funcional estandarizada por edad: 4,25 puntos porcentuales.

Fuentes: [diccionario del CNPV 2018](https://microdatos.dane.gov.co/index.php/catalog/643/data-dictionary) y [capa municipal del MGN integrado 2018](https://geoportal.dane.gov.co/mparcgis/rest/services/MGN2018/Serv_CapaMunicipiosInt_2018/MapServer/0).
