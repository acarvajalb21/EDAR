# Figuras interactivas del libro con los tokens de la gama Petróleo (ver shiny_salud/DISENO.md).
# En HTML se dibujan con Plotly a partir de los agregados de data/; en otros formatos se usa
# la imagen estática que genera scripts/preparar_resumen.py. «Fuera» siempre es la clase
# «fuera de la ruta formal»; los grupos se comparan con otra pareja de colores.

TK <- list(
  hoja = "#F7F9FB", tinta = "#10293B", tinta2 = "#3A4F60", tinta3 = "#54697A", hilo = "#D9E1E7",
  base = "#A9B6C1", suelo = "#EEF2F5", dentro = "#1B6CA8", fuera = "#DD6B20", grupo_a = "#5B6FB5",
  grupo_b = "#A86C00", referencia = "#7D8A96"
)
FUENTE <- "Atkinson Hyperlegible Next, Segoe UI, Arial, sans-serif"

num_es <- function(x, decimales = 0) {
  formatC(x, format = "f", digits = decimales, big.mark = ".", decimal.mark = ",")
}
pct_es <- function(x, decimales = 1) paste0(num_es(x, decimales), " %")

figura <- function(grafico, imagen) {
  if (knitr::is_html_output()) grafico else knitr::include_graphics(imagen)
}

eje <- function(titulo = "", ...) {
  utils::modifyList(list(
    title = list(text = titulo, font = list(color = TK$tinta3, size = 13)), gridcolor = TK$hilo,
    zeroline = FALSE, linecolor = TK$base, tickcolor = TK$base, automargin = TRUE, fixedrange = TRUE
  ), list(...))
}

estilo_libro <- function(p, titulo, leyenda = TRUE, margen = list(l = 10, r = 24, t = 84, b = 10)) {
  p |>
    plotly::layout(
      title = list(text = titulo, x = 0, xanchor = "left", xref = "paper",
                   font = list(family = FUENTE, color = TK$tinta, size = 17)),
      margin = margen, separators = ",.", showlegend = leyenda,
      font = list(family = FUENTE, color = TK$tinta2, size = 13),
      paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
      hoverlabel = list(bgcolor = TK$tinta, bordercolor = TK$tinta, align = "left",
                        font = list(family = FUENTE, color = "#FFFFFF", size = 13)),
      legend = list(orientation = "h", x = 0, y = 1.02, xanchor = "left", yanchor = "bottom",
                    font = list(color = TK$tinta2))
    ) |>
    plotly::config(displaylogo = FALSE, locale = "es", responsive = TRUE,
                   modeBarButtonsToRemove = c("select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
                                              "hoverClosestCartesian", "hoverCompareCartesian"),
                   toImageButtonOptions = list(format = "png", scale = 2))
}

barras_h <- function(categorias, valores, colores, textos, detalle, alto, nombre = "Valor") {
  plotly::plot_ly(x = valores, y = factor(categorias, levels = categorias), type = "bar", orientation = "h", name = nombre,
                  marker = list(color = colores), text = textos, textposition = "outside", cliponaxis = FALSE,
                  textfont = list(color = TK$tinta), customdata = detalle,
                  hovertemplate = "%{customdata}<extra></extra>", height = alto)
}

g_faltantes <- function() {
  d <- utils::head(leer("calidad_variables.csv"), 12)
  d <- d[order(d$pct), ]
  barras_h(d$descripcion, d$pct, TK$tinta3, pct_es(d$pct),
           paste0(d$descripcion, "<br>", pct_es(d$pct), " sin dato o con código de no informa<br>",
                  num_es(d$missing_or_sentinel), " personas"), 450, nombre = "Sin dato o «no informa» (%)") |>
    estilo_libro("Variables con mayor ausencia en los predictores") |>
    plotly::layout(xaxis = eje("Faltantes o códigos de no informa (%)", range = c(0, max(d$pct) * 1.18)),
                   yaxis = eje(gridcolor = "rgba(0,0,0,0)"), bargap = .32)
}

g_composicion <- function() {
  d <- leer("composicion_etiqueta.csv")
  d <- d[rev(seq_len(nrow(d))), ]
  niveles <- d$tratamiento_principal
  p <- plotly::plot_ly(height = 360)
  for (clase in c("Dentro de la ruta formal", "Fuera de la ruta formal")) {
    x <- d[d$clasificacion == clase, ]
    p <- plotly::add_trace(p, x = x$n, y = factor(x$tratamiento_principal, levels = niveles), type = "bar", orientation = "h",
                           name = clase, marker = list(color = if (clase == "Dentro de la ruta formal") TK$dentro else TK$fuera),
                           text = num_es(x$n), textposition = "outside", cliponaxis = FALSE, textfont = list(color = TK$tinta),
                           customdata = paste0(x$tratamiento_principal, "<br>", num_es(x$n), " personas (", pct_es(x$porcentaje), ")<br>", clase),
                           hovertemplate = "%{customdata}<extra></extra>")
  }
  p |>
    estilo_libro("Composición de la etiqueta operativa") |>
    plotly::layout(xaxis = eje("Personas", range = c(0, max(d$n) * 1.18), tickformat = ",d"),
                   yaxis = eje(gridcolor = "rgba(0,0,0,0)"), bargap = .38)
}

g_dificultad <- function() {
  d <- leer("dificultad.csv")
  d <- d[match(c("Sin dificultad", "Con dificultad"), d$dificultad), ]
  dentro <- 100 - d$porcentaje_sin_formal
  plotly::plot_ly(y = d$dificultad, x = dentro, type = "bar", orientation = "h", name = "Dentro de la ruta formal",
                  marker = list(color = TK$dentro), customdata = paste0(d$dificultad, "<br>Dentro de la ruta formal: ",
                  pct_es(dentro), "<br>", num_es(d$con_formal), " de ", num_es(d$n), " personas"),
                  hovertemplate = "%{customdata}<extra></extra>", height = 300) |>
    plotly::add_trace(x = d$porcentaje_sin_formal, name = "Fuera de la ruta formal", marker = list(color = TK$fuera),
                      customdata = paste0(d$dificultad, "<br>Fuera de la ruta formal: ", pct_es(d$porcentaje_sin_formal),
                                          "<br>", num_es(d$sin_formal), " de ", num_es(d$n), " personas")) |>
    plotly::add_annotations(x = 101, y = d$dificultad, text = paste0("n = ", num_es(d$n)), xanchor = "left",
                            showarrow = FALSE, font = list(color = TK$tinta2, size = 12)) |>
    estilo_libro("Clasificación por dificultad funcional declarada", leyenda = TRUE, margen = list(l = 10, r = 70, t = 84, b = 10)) |>
    plotly::layout(barmode = "stack", bargap = .42, xaxis = eje("Porcentaje dentro de cada grupo", range = c(0, 100)),
                   yaxis = eje(gridcolor = "rgba(0,0,0,0)"))
}

g_edad <- function() {
  d <- leer("edad_dificultad.csv")
  d <- d[d$publicable %in% c(TRUE, "True"), ]
  d <- d[order(d$P_EDADR), ]
  niveles <- unique(d$grupo_edad)
  p <- plotly::plot_ly(height = 420)
  for (grupo in c("Con dificultad", "Sin dificultad")) {
    parte <- d[d$dificultad == grupo, ]
    p <- plotly::add_trace(p, x = factor(parte$grupo_edad, levels = niveles), y = parte$porcentaje_sin_formal,
                           type = "scatter", mode = "lines+markers", name = grupo,
                           line = list(color = if (grupo == "Con dificultad") TK$grupo_b else TK$grupo_a, width = 2.5),
                           marker = list(size = 7),
                           customdata = paste0(grupo, ", ", parte$grupo_edad, " años<br>Fuera de la ruta formal: ",
                                               pct_es(parte$porcentaje_sin_formal), "<br>Base: ", num_es(parte$n), " personas"),
                           hovertemplate = "%{customdata}<extra></extra>")
  }
  estilo_libro(p, "La relación cambia con la edad", leyenda = TRUE, margen = list(l = 10, r = 20, t = 84, b = 10)) |>
    plotly::layout(xaxis = eje("Edad al censo (grupos quinquenales)", tickangle = -50),
                   yaxis = eje("Fuera de la ruta formal (%)", rangemode = "tozero"))
}

g_sexo <- function() {
  d <- leer("sexo_dificultad.csv")
  p <- plotly::plot_ly(height = 360)
  for (grupo in c("Con dificultad", "Sin dificultad")) {
    parte <- d[d$dificultad == grupo, ]
    parte <- parte[match(c("Hombre", "Mujer"), parte$sexo), ]
    p <- plotly::add_trace(p, x = c("Hombres", "Mujeres"), y = parte$porcentaje_sin_formal, type = "bar", name = grupo,
                           marker = list(color = if (grupo == "Con dificultad") TK$grupo_b else TK$grupo_a),
                           text = pct_es(parte$porcentaje_sin_formal), textposition = "outside", cliponaxis = FALSE,
                           customdata = paste0(c("Hombres", "Mujeres"), ", ", tolower(grupo), "<br>Fuera de la ruta formal: ",
                                               pct_es(parte$porcentaje_sin_formal), "<br>Base: ", num_es(parte$n), " personas"),
                           hovertemplate = "%{customdata}<extra></extra>")
  }
  estilo_libro(p, "Sexo y dificultad funcional", leyenda = TRUE, margen = list(l = 10, r = 20, t = 84, b = 10)) |>
    plotly::layout(barmode = "group", bargap = .35, xaxis = eje(gridcolor = "rgba(0,0,0,0)"),
                   yaxis = eje("Fuera de la ruta formal (%)", range = c(0, max(d$porcentaje_sin_formal) * 1.2)))
}

g_municipio <- function() {
  d <- leer("municipio.csv")
  d <- d[order(d$porcentaje_sin_formal), ]
  total <- resumen$porcentaje_sin_formal
  barras_h(d$municipio, d$porcentaje_sin_formal, TK$fuera, pct_es(d$porcentaje_sin_formal),
           paste0(d$municipio, "<br>Fuera de la ruta formal: ", pct_es(d$porcentaje_sin_formal),
                  "<br>", num_es(d$sin_formal), " de ", num_es(d$n), " personas"), 660, nombre = "Fuera de la ruta formal (%)") |>
    estilo_libro("Municipios con recuentos publicables") |>
    plotly::layout(
      bargap = .3, xaxis = eje("Fuera de la ruta formal (%)", range = c(0, max(d$porcentaje_sin_formal) * 1.16)),
      yaxis = eje(gridcolor = "rgba(0,0,0,0)"),
      shapes = list(list(type = "line", x0 = total, x1 = total, y0 = 0, y1 = 1, yref = "paper",
                         line = list(color = TK$tinta, dash = "dash", width = 1.5))),
      annotations = list(list(x = total, y = 1, yref = "paper", yanchor = "bottom", xanchor = "left", showarrow = FALSE,
                              text = paste0("Atlántico: ", pct_es(total)), font = list(color = TK$tinta, size = 12)))
    )
}

g_modelos <- function() {
  d <- leer("comparacion_modelos.csv")
  d <- d[rev(seq_len(nrow(d))), ]
  p <- plotly::plot_ly(height = 360)
  for (parte in list(list("ap_validacion", "Validación", TK$grupo_a), list("ap_prueba", "Prueba", TK$grupo_b))) {
    p <- plotly::add_trace(p, y = factor(d$modelo, levels = d$modelo), x = d[[parte[[1]]]], type = "bar", orientation = "h",
                           name = parte[[2]], marker = list(color = parte[[3]]),
                           customdata = paste0(d$modelo, "<br>AP en ", tolower(parte[[2]]), ": ", num_es(d[[parte[[1]]]], 3)),
                           hovertemplate = "%{customdata}<extra></extra>")
  }
  estilo_libro(p, "Comparación bajo el mismo protocolo", leyenda = TRUE, margen = list(l = 10, r = 20, t = 84, b = 10)) |>
    plotly::layout(barmode = "group", bargap = .3, xaxis = eje("Precisión promedio (AP)", range = c(0, .42)),
                   yaxis = eje(gridcolor = "rgba(0,0,0,0)"))
}

g_curvas <- function() {
  d <- leer("curvas_modelo.csv")
  r <- leer("curvas_resumen.csv")[1, ]
  roc <- d[d$curva == "roc", ]
  pr <- d[d$curva == "pr", ]
  a <- plotly::plot_ly(height = 520) |>
    plotly::add_trace(x = c(0, 1), y = c(0, 1), type = "scatter", mode = "lines", name = "Azar (curva ROC)",
                      line = list(color = TK$referencia, dash = "dash", width = 1.3), hoverinfo = "skip") |>
    plotly::add_trace(x = roc$x, y = roc$y, type = "scatter", mode = "lines", name = "Modelo (boosting de histogramas)",
                      legendgroup = "modelo", line = list(color = TK$dentro, width = 2.4),
                      hovertemplate = "Falsos positivos: %{x:.1%}<br>Sensibilidad: %{y:.1%}<extra></extra>") |>
    plotly::layout(xaxis = eje("Tasa de falsos positivos", range = c(0, 1), fixedrange = FALSE, tickformat = ".0%"),
                   yaxis = eje("Sensibilidad", range = c(0, 1), fixedrange = FALSE, tickformat = ".0%"))
  b <- plotly::plot_ly(height = 520) |>
    plotly::add_trace(x = c(0, 1), y = rep(r$prevalencia, 2), type = "scatter", mode = "lines", name = "Prevalencia (sin modelo, curva PR)",
                      line = list(color = TK$referencia, dash = "dash", width = 1.3), hoverinfo = "skip") |>
    plotly::add_trace(x = pr$x, y = pr$y, type = "scatter", mode = "lines", name = "Modelo", showlegend = FALSE,
                      legendgroup = "modelo", line = list(color = TK$dentro, width = 2.4),
                      hovertemplate = "Sensibilidad: %{x:.1%}<br>Precisión: %{y:.1%}<extra></extra>") |>
    plotly::layout(xaxis = eje("Sensibilidad", range = c(0, 1), fixedrange = FALSE, tickformat = ".0%"),
                   yaxis = eje("Precisión", range = c(0, 1), fixedrange = FALSE, tickformat = ".0%"))
  plotly::subplot(a, b, nrows = 1, margin = .07, titleX = TRUE, titleY = TRUE) |>
    estilo_libro("Modelo seleccionado, conjunto de prueba", margen = list(l = 10, r = 20, t = 84, b = 10)) |>
    plotly::layout(legend = list(orientation = "h", x = 0, y = -0.3, xanchor = "left", yanchor = "top"),
                   margin = list(l = 10, r = 20, t = 84, b = 110),
                   annotations = list(
      list(x = 0, y = 1.02, xref = "paper", yref = "paper", xanchor = "left", yanchor = "bottom", showarrow = FALSE,
           text = paste0("ROC, AUC ", num_es(r$roc_auc, 3)), font = list(color = TK$tinta2, size = 13)),
      list(x = .535, y = 1.02, xref = "paper", yref = "paper", xanchor = "left", yanchor = "bottom", showarrow = FALSE,
           text = paste0("Precisión y sensibilidad, AP ", num_es(r$ap, 3)), font = list(color = TK$tinta2, size = 13))))
}

g_confusion <- function() {
  m <- leer("matriz_confusion.csv")[1, ]
  valores <- matrix(c(m$verdaderos_negativos, m$falsos_positivos, m$falsos_negativos, m$verdaderos_positivos), nrow = 2, byrow = TRUE)
  nombres <- matrix(c("Verdaderos negativos", "Falsas alarmas", "No detectados", "Detectados"), nrow = 2, byrow = TRUE)
  ejes <- c("Dentro de la ruta", "Fuera de la ruta")
  plotly::plot_ly(x = ejes, y = ejes, z = valores, type = "heatmap", showscale = FALSE,
                  colorscale = list(c(0, TK$suelo), c(1, TK$dentro)),
                  customdata = nombres, text = matrix(num_es(valores), nrow = 2),
                  hovertemplate = "%{customdata}<br>Observado: %{y}<br>Predicción: %{x}<br>%{text} personas<extra></extra>",
                  height = 380, xgap = 3, ygap = 3) |>
    plotly::add_annotations(x = rep(ejes, 2), y = rep(ejes, each = 2), showarrow = FALSE,
                            text = paste0(as.vector(t(nombres)), "<br>", num_es(as.vector(t(valores)))),
                            font = list(size = 17, color = ifelse(as.vector(t(valores)) > .7 * max(valores), "#FFFFFF", TK$tinta))) |>
    estilo_libro("Matriz de confusión en prueba (umbral elegido en validación)", leyenda = FALSE, margen = list(l = 10, r = 20, t = 56, b = 10)) |>
    plotly::layout(xaxis = eje("Predicción", gridcolor = "rgba(0,0,0,0)"),
                   yaxis = eje("Observado", gridcolor = "rgba(0,0,0,0)", autorange = "reversed"))
}

g_calibracion <- function() {
  d <- leer("calibracion.csv")
  plotly::plot_ly(height = 400) |>
    plotly::add_trace(x = c(0, .5), y = c(0, .5), type = "scatter", mode = "lines", name = "Calibración perfecta",
                      line = list(color = TK$referencia, dash = "dash", width = 1.3), hoverinfo = "skip") |>
    plotly::add_trace(x = d$mean_predicted, y = d$observed, type = "scatter", mode = "lines+markers", name = "Deciles en prueba",
                      line = list(color = TK$dentro, width = 2.4), marker = list(size = 8),
                      customdata = num_es(d$n),
                      hovertemplate = "Probabilidad media: %{x:.1%}<br>Frecuencia observada: %{y:.1%}<br>%{customdata} personas<extra></extra>") |>
    estilo_libro("Calibración interna", leyenda = TRUE, margen = list(l = 10, r = 20, t = 84, b = 10)) |>
    plotly::layout(xaxis = eje("Probabilidad media predicha", range = c(0, .5), tickformat = ".0%"),
                   yaxis = eje("Frecuencia observada", range = c(0, .5), tickformat = ".0%"))
}

g_importancia <- function() {
  d <- leer("importancia.csv")
  d <- utils::head(d[order(-d$mean_ap_drop), ], 10)
  d <- d[order(d$mean_ap_drop), ]
  nuevas <- d$feature %in% c("HOGAR_OTROS_ENFERMOS", "SECCION_PCT_ENFERMOS")
  p <- plotly::plot_ly(height = 450)
  for (grupo in list(list(FALSE, "Variables de la versión 1", TK$base), list(TRUE, "Variables de contexto añadidas (versión 2)", TK$dentro))) {
    x <- d[nuevas == grupo[[1]], ]
    p <- plotly::add_trace(p, x = x$mean_ap_drop, y = factor(x$descripcion, levels = d$descripcion), type = "bar", orientation = "h",
                           name = grupo[[2]], marker = list(color = grupo[[3]]), text = num_es(x$mean_ap_drop, 3),
                           textposition = "outside", cliponaxis = FALSE, textfont = list(color = TK$tinta),
                           customdata = paste0(x$descripcion, "<br>Caída media de AP: ", num_es(x$mean_ap_drop, 4),
                                               " (desviación ", num_es(x$std_ap_drop, 4), ")"),
                           hovertemplate = "%{customdata}<extra></extra>")
  }
  p |>
    estilo_libro("Importancia predictiva, sin interpretación causal") |>
    plotly::layout(xaxis = eje("Caída de AP al permutar la variable en validación", range = c(0, max(d$mean_ap_drop) * 1.2)),
                   yaxis = eje(gridcolor = "rgba(0,0,0,0)"), bargap = .32)
}

g_brecha <- function() {
  d <- leer("auditoria_brecha_2026.csv")
  bandas <- c("0-14" = "0 a 14", "15-59" = "15 a 59", "60+" = "60 o más")
  p <- plotly::plot_ly(height = 400)
  for (grupo in c("Con dificultad", "Sin dificultad")) {
    parte <- d[d$dificultad == grupo, ]
    p <- plotly::add_trace(p, x = factor(bandas[parte$edad], levels = bandas), y = parte$sensibilidad,
                           type = "scatter", mode = "lines+markers", name = grupo,
                           line = list(color = if (grupo == "Con dificultad") TK$grupo_b else TK$grupo_a, width = 2.5),
                           marker = list(size = 9),
                           error_y = list(type = "data", symmetric = FALSE, array = parte$superior - parte$sensibilidad,
                                          arrayminus = parte$sensibilidad - parte$inferior, thickness = 1.5, width = 5),
                           customdata = paste0(grupo, ", ", bandas[parte$edad], " años<br>Sensibilidad: ", pct_es(100 * parte$sensibilidad),
                                               "<br>Detectados: ", num_es(parte$detectados), " de ", num_es(parte$positivos),
                                               "<br>Intervalo Wilson 95 %: ", pct_es(100 * parte$inferior), " a ", pct_es(100 * parte$superior)),
                           hovertemplate = "%{customdata}<extra></extra>")
  }
  estilo_libro(p, "Sensibilidad por edad y dificultad funcional declarada", leyenda = TRUE,
               margen = list(l = 10, r = 20, t = 84, b = 10)) |>
    plotly::layout(xaxis = eje("Edad en años", gridcolor = "rgba(0,0,0,0)"),
                   yaxis = eje("Sensibilidad entre quienes están fuera de la ruta", range = c(0, 1), tickformat = ".0%"))
}
