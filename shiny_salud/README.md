# Aplicación Shiny · Salud Atlántico

Aplicación en R con nueve secciones: **Introducción**, **Objetivos**, **Problema**, **Marco teórico**, **EDA univariado**, **EDA multivariado**, **Modelado**, **Modelo** y **Conclusiones**. Usa los mismos agregados, textos y reglas de protección que el tablero Dash. La documentación completa está en el capítulo 8 del Bookdown (`08-aplicacion-shiny.Rmd`) y el sistema visual, en [`DISENO.md`](DISENO.md).

## Ejecutar

Necesita R 4.6 y los paquetes `shiny`, `bslib`, `plotly` y `jsonlite`. Desde la raíz de EDAR:

```r
shiny::runApp("shiny_salud")
```

No hacen falta microdatos: `data/` solo contiene `eda.json`, `modelo.json` y `contenido.json`, copiados de `dash_salud/data/` en EDAPYTHON. Si `eda.json` cambia, hay que copiarlo de nuevo y regenerar `pruebas/esperado_dash.json`. `contenido.json` se genera con `dash_salud/generar_contenido.py`, y el nombre del proyecto se cambia ahí. `www/relato.js`, `www/relato.css`, `www/contenido.css` y `www/relato_datos.json` son los mismos del Dash; `relato_datos.json` se genera con `dash_salud/generar_relato.py`.

## Estructura

| Archivo | Contenido |
|:--|:--|
| `app.R` | Interfaz general y lógica reactiva |
| `R/datos.R` | Carga de agregados y constantes |
| `R/reglas.R` | Filtros, cobertura, ocultación de tasas y referencias |
| `R/graficos.R` | Gráficas Plotly |
| `R/vistas.R` | Explorar y Modelo, las secciones con controles |
| `R/contenido.R` | Bloques de las demás secciones, leídos de `contenido.json` |
| `R/formato.R` | Números en español |
| `www/` | Estilos, fuentes y relato de apertura |
| `pruebas/pruebas.R` | Comprobaciones automáticas |

## Probar

Desde esta carpeta:

```bash
Rscript pruebas/pruebas.R
```

Las pruebas comprueban que solo se distribuyan agregados, que las tasas se oculten según las reglas, que la app reaccione a los filtros y que el umbral validado reproduzca la prueba del modelo. También comparan Shiny con Dash en las 3.375 combinaciones de filtros.

## Publicar

```powershell
.\deploy_cloud_run.ps1
```

El script necesita Google Cloud CLI con sesión iniciada y permisos sobre el proyecto. Crea el servicio `shiny-salud-atlantico` en `us-east1`, separado del Dash. Usa afinidad de sesión porque Shiny mantiene una conexión WebSocket. Con `deploy_cloud_shell.sh` se hace lo mismo desde Cloud Shell.
