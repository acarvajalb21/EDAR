# DATAVIZ · Salud Atlántico: aplicación Shiny sobre agregados publicables del CNPV 2018.
# Ejecutar con shiny::runApp("shiny_salud") desde la raíz del repositorio EDAR.

library(shiny)
library(bslib)
library(plotly)

tema <- bs_theme(
  version = 5, bg = TK$papel, fg = TK$tinta, primary = TK$rio, secondary = TK$tinta2,
  base_font = FUENTE, heading_font = FUENTE, font_scale = 1, "border-radius" = "6px"
)

ui <- page_navbar(
  title = tags$span(class = "marca", tags$span(class = "marca-punto"), "DATAVIZ",
                    tags$span(class = "marca-sub", "/ Salud Atlántico")),
  id = "nav", lang = "es", theme = tema, fillable = FALSE, window_title = "Salud Atlántico · DataViz",
  header = tags$head(
    tags$link(rel = "preload", href = "fonts/ibm-plex-sans-latin-variable.woff2", as = "font", type = "font/woff2", crossorigin = NA),
    tags$link(rel = "stylesheet", href = "relato.css"),
    tags$link(rel = "stylesheet", href = "estilos.css"),
    tags$script(src = "relato.js"),
    tags$meta(name = "description", content = "Exploración y modelo sobre la ruta de atención declarada en el Atlántico, CNPV 2018."),
    # En móvil el menú se cierra al elegir una vista.
    tags$script(HTML("document.addEventListener('click', function (e) {
      var menu = document.querySelector('.navbar-collapse.show');
      if (menu && e.target.closest('.navbar-collapse .nav-link')) bootstrap.Collapse.getOrCreateInstance(menu).hide();
    });
    document.addEventListener('shown.bs.tab', function () { window.scrollTo({ top: 0, behavior: 'instant' }); });"))
  ),
  nav_panel("Panorama", value = "panorama", vista_panorama()),
  nav_panel("Explorar", value = "explorar", vista_explorar()),
  nav_panel("Modelo", value = "modelo", vista_modelo()),
  nav_panel("Método", value = "metodo", vista_metodo()),
  nav_spacer(),
  nav_item(enlace("Informe completo", URL_BOOKDOWN))
)

server <- function(input, output, session) {
  observeEvent(input$relato_ir, nav_select("nav", input$relato_ir))
  observeEvent(input$relato_municipio, {
    limpiar_filtros(input$relato_municipio)
    nav_select("nav", "explorar")
  })

  output$g_panorama <- renderPlotly(g_panorama_municipal())

  seleccion <- reactive(list(
    municipios = if (is.null(input$f_municipio)) character(0) else input$f_municipio,
    sexo = input$f_sexo, edad = input$f_edad, zona = input$f_zona, dificultad = input$f_dificultad
  ))
  resumen <- reactive(do.call(resumen_seleccion, seleccion()))

  limpiar_filtros <- function(municipio = character(0)) {
    updateSelectizeInput(session, "f_municipio", selected = municipio)
    for (id in c("f_sexo", "f_edad", "f_zona", "f_dificultad")) updateSelectInput(session, id, selected = "Todos")
  }
  observeEvent(input$limpiar, limpiar_filtros())

  output$frase <- renderUI(frase_seleccion(seleccion(), resumen()))

  output$cinta <- renderUI({
    r <- resumen()
    cobertura <- if (is.na(r$cobertura)) 0 else r$cobertura
    estado <- if (r$celdas == 0) "sin-datos" else if (r$tasa_segura) "visible" else "oculta"
    rotulo_estado <- c(visible = "✓ Tasa visible", oculta = "⊘ Tasa oculta", `sin-datos` = "⊘ Sin cruces publicables")[[estado]]
    motivo <- if (r$celdas == 0) {
      "Ninguna celda cumple las reglas de publicación. Prueba a quitar un filtro."
    } else if (r$tasa_segura) {
      paste0("Base aproximada de ", fmt_int(r$n), " personas en ", r$celdas, if (r$celdas == 1) " cruce publicable." else " cruces publicables.")
    } else if (is.na(r$cobertura) || r$cobertura < COBERTURA_MINIMA) {
      paste0("La cobertura es menor del ", COBERTURA_MINIMA, " % necesario para interpretar la tasa.")
    } else {
      paste0("La base aproximada es menor de ", BASE_TASA_MINIMA, " personas.")
    }
    texto_cobertura <- if (is.na(r$cobertura)) "Cobertura sin estimación publicable" else paste0("Cobertura: al menos ", r$cobertura, " %")
    if (length(seleccion()$municipios) > 1) texto_cobertura <- paste(texto_cobertura, "(límite conservador por municipio)")
    div(class = paste("cinta", estado),
        div(class = "cinta-texto", strong(rotulo_estado), span(motivo)),
        div(class = "cinta-medida",
            div(class = "cinta-rotulo", texto_cobertura),
            div(class = "cinta-pista", role = "img", `aria-label` = paste(texto_cobertura, "; umbral de publicación 80 %"),
                div(class = "cinta-relleno", style = sprintf("width:%d%%", cobertura)),
                div(class = "cinta-umbral", title = "Umbral de 80 %"))))
  })

  output$nota_referencia <- renderUI({
    ref <- resumen()$referencia
    if (is.null(ref)) return(NULL)
    p(class = "referencia", paste0(
      "Referencia sin cruces adicionales: «", ref$etiqueta, "» registra ≈ ", fmt_pct(ref$sin_formal / ref$n),
      " sobre una base aproximada de ", fmt_int(ref$n), " personas en ", ref$fuente,
      ". Ese agregado se publica aparte, con conteos redondeados a 10, y no procede de las celdas filtrables."))
  })

  output$g_ranking <- renderPlotly({
    s <- seleccion()
    g_ranking(resumen()$filas, input$metrica, s$sexo, s$edad, s$zona, s$dificultad)
  })

  output$tabla_municipios <- renderUI({
    s <- seleccion()
    d <- municipios_visibles(resumen()$filas, s$sexo, s$edad, s$zona, s$dificultad)
    if (nrow(d) == 0) return(p(class = "panel-nota", "No hay municipios con cobertura suficiente."))
    d <- d[order(-d$sin_formal / d$n), ]
    tabla_html(data.frame(Municipio = d$municipio, `Base aproximada` = fmt_int(d$n), `Fuera de la ruta` = fmt_int(d$sin_formal),
                          Porcentaje = fmt_pct(d$sin_formal / d$n), check.names = FALSE))
  })

  output$g_edad <- renderPlotly({
    s <- seleccion()
    g_edad(resumen()$filas, s$municipios, s$sexo, s$zona)
  })

  output$g_composicion <- renderPlotly({
    s <- seleccion()
    g_composicion(resumen()$filas, s$municipios, s$sexo, s$edad, s$zona, s$dificultad)
  })

  output$nota_composicion <- renderText({
    s <- seleccion()
    r <- composicion_visible(resumen()$filas, s$municipios, s$sexo, s$edad, s$zona, s$dificultad)
    if (r$amplia) {
      "Cada barra muestra, de cada 100 personas de ese sexo y zona, cuántas quedaron fuera de la ruta formal. Se usa toda la cohorte; los recuentos se redondean a 10."
    } else {
      paste0("Cada barra usa como base a las personas de ese sexo y zona dentro del filtro. ",
             if (r$omitidos > 0) paste0("Se omiten ", r$omitidos, " grupos por tamaño o cobertura insuficiente. ") else "",
             "Los porcentajes son aproximados y pueden no representar a toda la subpoblación filtrada.")
    }
  })

  output$descargar <- downloadHandler(
    filename = "dataviz_salud_agregados.csv",
    content = function(archivo) {
      filas <- resumen()$filas[, c("municipio", "sexo", "edad", "zona", "dificultad", "n", "sin_formal")]
      utils::write.csv(filas, archivo, row.names = FALSE, fileEncoding = "UTF-8")
    },
    contentType = "text/csv"
  )

  fila <- reactive(fila_umbral(input$umbral))

  output$umbral_titulo <- renderUI({
    f <- fila()
    validado <- abs(f$threshold - MODELO$metadata$chosen_threshold) < 1e-8
    div(class = paste("umbral-titulo", if (validado) "validado"),
        paste0(if (validado) "Umbral validado: " else "Escenario exploratorio: ", fmt_dec(f$threshold)))
  })

  output$umbral_fichas <- renderUI({
    f <- fila()
    m <- metricas_umbral(f)
    div(class = "fichas tres compactas",
        ficha("Sensibilidad", fmt_pct(m[["sensibilidad"]]), "De los casos de la clase, cuántos marca"),
        ficha("Precisión", fmt_pct(m[["precision"]]), "De los marcados, cuántos son de la clase"),
        ficha("Personas marcadas", fmt_int(m[["marcadas"]]), paste("De", fmt_int(MODELO$metadata$test_n), "en prueba")))
  })

  output$matriz <- renderUI({
    f <- fila()
    celda <- function(valor, etiqueta, clase) div(class = paste("matriz-celda", clase), strong(fmt_int(valor)), span(etiqueta))
    div(class = "matriz", role = "group", `aria-label` = "Matriz de confusión en prueba",
        div(), div(class = "matriz-eje", "Predicción: dentro"), div(class = "matriz-eje", "Predicción: fuera"),
        div(class = "matriz-eje lado", "Dato: dentro"), celda(f$tn, "Aciertos", "acierto"), celda(f$fp, "Falsas alarmas", "error"),
        div(class = "matriz-eje lado", "Dato: fuera"), celda(f$fn, "No detectados", "error"), celda(f$tp, "Aciertos", "acierto"))
  })

  output$g_comparacion <- renderPlotly(g_comparacion())
  output$g_curvas <- renderPlotly(g_curvas(input$curva))
  output$g_calibracion <- renderPlotly(g_calibracion())
  output$g_importancia <- renderPlotly(g_importancia())
}

shinyApp(ui, server)
