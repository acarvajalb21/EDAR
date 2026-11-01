# Gráficas Plotly con los tokens comunes del proyecto (ver DISENO.md).
# Arcilla significa siempre «fuera de la ruta formal» y río, «dentro». Añil y ocre comparan grupos.

TK <- list(
  papel = "#F4F1E9", hoja = "#FDFCF9", tinta = "#13232C", tinta2 = "#465660", tinta3 = "#5F6D75",
  hilo = "#DDD8CB", base = "#C9C4B6", rio = "#00739A", arcilla = "#C4552D", anil = "#3F5AA6",
  ocre = "#B57A08", referencia = "#9A978C"
)
FUENTE <- "IBM Plex Sans, Segoe UI, Arial, sans-serif"

estilo <- function(p, alto, margen = list(l = 52, r = 18, t = 10, b = 46), leyenda = FALSE) {
  p$x$layout$height <- alto
  p |>
    plotly::layout(
      margin = margen, separators = ",.", showlegend = leyenda,
      font = list(family = FUENTE, color = TK$tinta2, size = 13),
      paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
      hoverlabel = list(bgcolor = TK$tinta, bordercolor = TK$tinta, align = "left",
                        font = list(family = FUENTE, color = "#FFFFFF", size = 13)),
      legend = list(orientation = "h", x = 0, y = 1.1, xanchor = "left", yanchor = "bottom",
                    font = list(color = TK$tinta2)),
      xaxis = list(gridcolor = TK$hilo, zeroline = FALSE, linecolor = TK$base, tickcolor = TK$base,
                   title = list(font = list(color = TK$tinta3, size = 12)), fixedrange = TRUE, automargin = TRUE),
      yaxis = list(gridcolor = TK$hilo, zeroline = FALSE, linecolor = TK$base, tickcolor = TK$base,
                   title = list(font = list(color = TK$tinta3, size = 12)), fixedrange = TRUE, automargin = TRUE)
    ) |>
    plotly::config(displayModeBar = FALSE, responsive = TRUE, locale = "es")
}

fig_vacia <- function(mensaje, alto = 300) {
  # Se parte en líneas cortas para que el aviso no se recorte en pantallas estrechas.
  texto <- paste(strwrap(mensaje, width = 36), collapse = "<br>")
  plotly::plot_ly(type = "scatter", mode = "markers") |>
    plotly::add_annotations(text = texto, x = 0.5, y = 0.5, xref = "paper", yref = "paper", showarrow = FALSE,
                            font = list(color = TK$tinta3, size = 14, family = FUENTE)) |>
    estilo(alto) |>
    plotly::layout(xaxis = list(visible = FALSE), yaxis = list(visible = FALSE))
}

g_panorama_municipal <- function() {
  d <- EDA$municipal_overview
  d$tasa <- 100 * d$sin_formal / d$n
  d <- d[order(d$tasa), ]
  plotly::plot_ly(d, x = ~tasa, y = ~factor(municipio, levels = municipio), type = "bar", orientation = "h",
                  marker = list(color = TK$arcilla),
                  customdata = ~fmt_int(n),
                  hovertemplate = "%{y}<br>%{x:.1f} % fuera de la ruta formal<br>Base aproximada: %{customdata}<extra></extra>") |>
    estilo(600, list(l = 8, r = 18, t = 6, b = 44)) |>
    plotly::layout(bargap = 0.34, xaxis = list(title = list(text = "Fuera de la ruta formal (%)"), ticksuffix = " %"),
                   yaxis = list(title = list(text = ""), gridcolor = "rgba(0,0,0,0)", ticks = ""))
}

g_ranking <- function(filas, metrica, sexo, edad, zona, dificultad) {
  d <- municipios_visibles(filas, sexo, edad, zona, dificultad)
  if (nrow(d) == 0) return(fig_vacia("Cobertura o tamaño insuficiente para comparar municipios", 360))
  if (metrica == "conteo") {
    d$valor <- d$sin_formal
    titulo <- "Personas aproximadas fuera de la ruta formal"
    tip <- "%{y}<br>%{x:,} personas aprox.<br>Base: %{customdata}<extra></extra>"
    sufijo <- ""
  } else {
    d$valor <- 100 * d$sin_formal / d$n
    titulo <- "Fuera de la ruta formal (%)"
    tip <- "%{y}<br>%{x:.1f} % aprox.<br>Base: %{customdata}<extra></extra>"
    sufijo <- " %"
  }
  d <- d[order(d$valor), ]
  plotly::plot_ly(d, x = ~valor, y = ~factor(municipio, levels = municipio), type = "bar", orientation = "h",
                  marker = list(color = TK$arcilla), customdata = ~fmt_int(n), hovertemplate = tip) |>
    estilo(max(170, 58 + 25 * nrow(d)), list(l = 8, r = 18, t = 6, b = 44)) |>
    plotly::layout(bargap = 0.34, xaxis = list(title = list(text = titulo), ticksuffix = sufijo),
                   yaxis = list(title = list(text = ""), gridcolor = "rgba(0,0,0,0)", ticks = ""))
}

g_edad <- function(filas, municipios, sexo, zona) {
  d <- edades_visibles(filas, municipios, sexo, zona)
  if (nrow(d) == 0) return(fig_vacia("Cobertura o tamaño insuficiente para comparar edades", 330))
  p <- plotly::plot_ly()
  for (grupo in c(sin = "Sin dificultad funcional", con = "Con dificultad funcional")) {
    x <- d[d$dificultad == grupo, ]
    if (nrow(x) == 0) next
    x <- x[order(match(x$edad, EDADES)), ]
    color <- if (grupo == "Sin dificultad funcional") TK$anil else TK$ocre
    p <- p |>
      plotly::add_trace(x = factor(x$edad, levels = EDADES), y = 100 * x$sin_formal / x$n, type = "scatter",
                        mode = "lines+markers", name = grupo, line = list(color = color, width = 2.5),
                        marker = list(color = color, size = 10, line = list(color = TK$hoja, width = 2)),
                        customdata = fmt_int(x$n),
                        hovertemplate = paste0("%{x}<br>%{y:.1f} % aprox.<br>Base: %{customdata}<extra>", grupo, "</extra>"))
  }
  p |>
    estilo(330, leyenda = TRUE) |>
    plotly::layout(xaxis = list(title = list(text = "Edad"), categoryorder = "array", categoryarray = EDADES),
                   yaxis = list(title = list(text = ""), ticksuffix = " %", rangemode = "tozero"))
}

g_composicion <- function(filas, municipios, sexo, edad, zona, dificultad) {
  r <- composicion_visible(filas, municipios, sexo, edad, zona, dificultad)
  d <- r$datos
  if (nrow(d) == 0) return(fig_vacia("No hay grupos con cobertura suficiente para comparar", 330))
  zonas <- ZONAS[ZONAS %in% d$zona]
  rotulos <- ifelse(zonas == "Cabecera", "Cabecera", "Centros poblados<br>y rural disperso")
  p <- plotly::plot_ly()
  for (grupo in c("Mujer", "Hombre")) {
    x <- d[d$sexo == grupo, ]
    if (nrow(x) == 0) next
    x <- x[order(match(x$zona, zonas)), ]
    valores <- 100 * x$sin_formal / x$n
    p <- p |>
      plotly::add_trace(x = factor(x$zona, levels = zonas), y = valores, type = "bar", name = grupo,
                        marker = list(color = if (grupo == "Mujer") TK$ocre else TK$anil),
                        text = fmt_pct(valores / 100), textposition = "outside", cliponaxis = FALSE,
                        textfont = list(color = TK$tinta, family = FUENTE), customdata = fmt_int(x$n),
                        hovertemplate = paste0("%{x}<br>%{y:.1f} % aprox.<br>Base: %{customdata} personas<extra>", grupo, "</extra>"))
  }
  tope <- max(100 * d$sin_formal / d$n) * 1.2
  p |>
    estilo(330, list(l = 52, r = 18, t = 10, b = 62), leyenda = TRUE) |>
    plotly::layout(barmode = "group", bargap = 0.4,
                   xaxis = list(title = list(text = ""), tickmode = "array", tickvals = zonas, ticktext = rotulos),
                   yaxis = list(title = list(text = ""), ticksuffix = " %", range = c(0, tope)))
}

g_comparacion <- function() {
  claves <- names(NOMBRES_MODELO)
  ap <- vapply(claves, function(k) MODELO$models[[k]]$test$pr_auc, numeric(1))
  plotly::plot_ly(x = factor(NOMBRES_MODELO, levels = NOMBRES_MODELO), y = ap, type = "bar",
                  marker = list(color = c(TK$referencia, TK$base, TK$base, TK$rio)),
                  text = fmt_dec(ap), textposition = "outside", cliponaxis = FALSE,
                  textfont = list(color = TK$tinta, family = FUENTE),
                  hovertemplate = "%{x}<br>Average Precision: %{y:.3f}<extra></extra>") |>
    estilo(330, list(l = 44, r = 14, t = 12, b = 70)) |>
    plotly::layout(bargap = 0.5, xaxis = list(title = list(text = "")),
                   yaxis = list(title = list(text = "AP en prueba"), range = c(0, max(ap) * 1.2)))
}

g_curvas <- function(tipo) {
  if (tipo == "pr") {
    d <- MODELO$pr_curve
    base <- MODELO$metadata$test_positive / MODELO$metadata$test_n
    ref <- list(x = c(0, 1), y = c(base, base), nombre = "Prevalencia")
    ejes <- c("Sensibilidad", "Precisión")
  } else {
    d <- MODELO$roc_curve
    ref <- list(x = c(0, 1), y = c(0, 1), nombre = "Azar")
    ejes <- c("1 − especificidad", "Sensibilidad")
  }
  plotly::plot_ly() |>
    plotly::add_trace(x = ref$x, y = ref$y, type = "scatter", mode = "lines", name = ref$nombre,
                      line = list(color = TK$referencia, width = 1.5), hoverinfo = "skip") |>
    plotly::add_trace(x = d$x, y = d$y, type = "scatter", mode = "lines", name = "Modelo",
                      line = list(color = TK$rio, width = 2.5),
                      hovertemplate = paste0(ejes[1], ": %{x:.2f}<br>", ejes[2], ": %{y:.2f}<extra></extra>")) |>
    estilo(330, leyenda = TRUE) |>
    plotly::layout(xaxis = list(title = list(text = ejes[1]), range = c(0, 1)),
                   yaxis = list(title = list(text = ejes[2]), range = c(0, 1.02)))
}

g_calibracion <- function() {
  d <- MODELO$calibration
  plotly::plot_ly() |>
    plotly::add_trace(x = c(0, 55), y = c(0, 55), type = "scatter", mode = "lines", name = "Calibración perfecta",
                      line = list(color = TK$referencia, width = 1.5), hoverinfo = "skip") |>
    plotly::add_trace(x = 100 * d$mean_predicted, y = 100 * d$observed, type = "scatter", mode = "lines+markers", name = "Modelo",
                      line = list(color = TK$rio, width = 2.5),
                      marker = list(color = TK$rio, size = 9, line = list(color = TK$hoja, width = 2)),
                      customdata = fmt_int(d$n),
                      hovertemplate = "Predicho: %{x:.1f} %<br>Observado: %{y:.1f} %<br>Base: %{customdata}<extra></extra>") |>
    estilo(330, leyenda = TRUE) |>
    plotly::layout(xaxis = list(title = list(text = "Probabilidad predicha media"), ticksuffix = " %", range = c(0, 55)),
                   yaxis = list(title = list(text = "Proporción observada"), ticksuffix = " %", range = c(0, 55)))
}

g_importancia <- function() {
  d <- utils::head(MODELO$importance, 8)
  d <- d[order(d$mean_ap_drop), ]
  etiquetas <- unname(NOMBRES_VARIABLE[d$feature])
  etiquetas[is.na(etiquetas)] <- d$feature[is.na(etiquetas)]
  plotly::plot_ly(x = d$mean_ap_drop, y = factor(etiquetas, levels = etiquetas), type = "bar", orientation = "h",
                  marker = list(color = ifelse(d$feature %in% VARIABLES_NUEVAS, TK$rio, TK$base)),
                  text = fmt_dec(d$mean_ap_drop), textposition = "outside", cliponaxis = FALSE,
                  textfont = list(color = TK$tinta, family = FUENTE),
                  hovertemplate = "%{y}<br>Caída de AP al permutar: %{x:.3f}<extra></extra>") |>
    estilo(330, list(l = 8, r = 44, t = 6, b = 44)) |>
    plotly::layout(bargap = 0.36, xaxis = list(title = list(text = "Caída media de AP en validación")),
                   yaxis = list(title = list(text = ""), gridcolor = "rgba(0,0,0,0)", ticks = ""))
}
