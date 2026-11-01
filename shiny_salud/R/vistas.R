# Secciones con controles propios. Los textos vienen de data/contenido.json, común con el Dash.

enlace <- function(texto, url) tags$a(texto, href = url, target = "_blank", rel = "noopener noreferrer")

ficha <- function(etiqueta, valor, nota, tono = NULL) {
  div(class = paste(c("c-ficha", tono), collapse = " "),
      div(class = "c-ficha-etiqueta", etiqueta),
      div(class = "c-ficha-valor", valor),
      div(class = "c-ficha-nota", nota))
}

tabla_html <- function(df) {
  tags$div(class = "c-tabla-marco", tags$table(class = "c-tabla",
    tags$thead(tags$tr(lapply(seq_along(df), function(j) tags$th(scope = "col", class = if (j == 1) "izq", names(df)[j])))),
    tags$tbody(lapply(seq_len(nrow(df)), function(i) {
      tags$tr(lapply(seq_along(df), function(j) tags$td(class = if (j == 1) "izq", as.character(df[[j]][i]))))
    }))))
}

pregunta <- function(titulo, respuesta) {
  tags$details(class = "pregunta", tags$summary(titulo), tags$p(respuesta))
}

vista_panorama <- function() {
  tagList(div(id = "relato"), vista_contenido("panorama"))
}

# Resume la selección en una frase; solo enuncia un porcentaje cuando las reglas lo permiten.
frase_seleccion <- function(s, r) {
  explorar <- CONTENIDO$explorar
  lugar <- if (length(s$municipios) == 0) "En el Atlántico" else if (length(s$municipios) == 1) {
    paste("En", s$municipios)
  } else paste("En", length(s$municipios), "municipios")
  edad <- if (s$edad == "Todos") NULL else if (s$edad == "65+") "de 65 años o más" else paste("de", s$edad, "años")
  zona <- c(Cabecera = "de cabecera", `Centros poblados y rural disperso` = "de centros poblados y rural disperso")[s$zona]
  dificultad <- if (s$dificultad == "Todos") NULL else tolower(s$dificultad)
  detalle <- c(edad, if (!is.na(zona)) unname(zona), dificultad)
  quien <- c(Mujer = "entre mujeres", Hombre = "entre hombres", Todos = if (length(detalle) > 0) "entre personas" else NA)[[s$sexo]]
  grupo <- if (is.na(quien)) "" else paste0(", ", paste(c(quien, detalle), collapse = " "))
  if (r$tasa_segura) {
    base <- paste0("Base aproximada: ", fmt_int(r$n), " personas en ", r$celdas, if (r$celdas == 1) " grupo publicado." else " grupos publicados.")
    if (length(s$municipios) == 1 && is.na(quien)) base <- paste(base, explorar$mapa_nota)
    if (length(s$municipios) == 0 && is.na(quien)) base <- paste(base, explorar$total_nota)
    div(class = "frase", tags$p(paste0(lugar, grupo, ", "), tags$strong(paste("≈", fmt_pct(r$positivos / r$n))), " quedó fuera de la ruta formal."),
        span(class = "frase-base", base))
  } else {
    div(class = "frase", tags$p(paste0(lugar, grupo, ", esta selección "), tags$em("no permite mostrar un porcentaje"), "."),
        span(class = "frase-base", if (r$celdas == 0) "Ningún grupo cumple las reglas de publicación. Prueba a quitar un filtro." else paste0("≈ ", fmt_int(r$n), " personas en grupos publicados. La protección de grupos pequeños oculta el porcentaje.")))
  }
}

filtro <- function(id, etiqueta, opciones) {
  selectInput(id, etiqueta, choices = c("Todos", opciones), selected = "Todos", selectize = FALSE)
}

vista_comparar <- function() {
  explorar <- CONTENIDO$explorar
  opciones <- stats::setNames(vapply(explorar$variables, function(v) v$id, character(1)),
                              vapply(explorar$variables, function(v) v$etiqueta, character(1)))
  div(class = "c-pila",
      p(class = "c-entrada", explorar$comparar_entrada),
      div(class = "opciones", radioButtons("comp_variable", NULL, inline = TRUE, choices = opciones, selected = opciones[[1]])),
      uiOutput("comp_lectura"),
      caja(plotlyOutput("g_comparada", height = "auto"), "Porcentaje fuera de la ruta formal", "En cada categoría de la variable elegida"),
      p(class = "c-pie", explorar$comparar_nota))
}

vista_grupos <- function() {
  explorar <- CONTENIDO$explorar
  g <- explorar$graficas
  omitidos <- oracion_omitidos(MUNICIPIOS_CUBO, "en el selector", "ninguno de sus grupos cumple las reglas de publicación")
  div(class = "c-pila",
      tags$section(class = "seleccion", `aria-label` = "Filtros y resultado",
          div(class = "seleccion-filtros",
              selectizeInput("f_municipio", "Municipio", choices = MUNICIPIOS_CUBO, multiple = TRUE,
                             options = list(placeholder = "Todos los municipios", plugins = list("remove_button"))),
              filtro("f_sexo", "Sexo", SEXOS),
              filtro("f_edad", "Edad", EDADES),
              filtro("f_zona", "Zona", ZONAS),
              filtro("f_dificultad", "Dificultad funcional", DIFICULTADES)),
          div(class = "seleccion-pie",
              p(class = "seleccion-ayuda", explorar$ayuda),
              actionButton("limpiar", "Quitar filtros", class = "boton discreto")),
          div(class = "seleccion-resultado", uiOutput("frase"), uiOutput("cinta"))),
      uiOutput("nota_referencia"),
      div(class = "lecturas",
          caja(tagList(div(class = "opciones", radioButtons("metrica", NULL, inline = TRUE, choices = c("Porcentaje" = "tasa", "Personas" = "conteo"), selected = "tasa")),
                       plotlyOutput("g_ranking", height = "auto"),
                       tags$details(class = "ver-datos", tags$summary("Ver estos datos en una tabla"), uiOutput("tabla_municipios"))),
               g$municipios$titulo, g$municipios$meta),
          div(class = "lecturas-lado",
              caja(plotlyOutput("g_edad", height = "auto"), g$edad$titulo, g$edad$meta, g$edad$nota),
              caja(tagList(plotlyOutput("g_composicion", height = "auto"), p(class = "c-nota", textOutput("nota_composicion", inline = TRUE))),
                   g$composicion$titulo, g$composicion$meta))),
      tags$details(class = "por-que-faltan", tags$summary(explorar$por_que_titulo),
                   tags$ul(lapply(explorar$por_que, tags$li)),
                   if (nzchar(omitidos)) p(class = "c-nota", trimws(omitidos))),
      div(class = "descarga",
          downloadButton("descargar", "Descargar selección agregada", class = "boton secundario", icon = NULL),
          span(class = "descarga-nota", explorar$descarga_nota)))
}

vista_explorar <- function() {
  explorar <- CONTENIDO$explorar
  div(class = "pagina",
      div(class = "c-cabecera", h1(explorar$titulo), p(class = "c-entrada", explorar$entrada)),
      div(class = "c-subnav", navset_underline(id = "sub_explorar",
        nav_panel(explorar$pestanas[[1]], value = "grupos", vista_grupos()),
        nav_panel(explorar$pestanas[[2]], value = "comparar", vista_comparar()),
        nav_panel(explorar$pestanas[[3]], value = "ajuste", div(class = "c-pila", lapply(explorar$ajuste, bloque))))))
}

vista_modelo <- function() {
  m <- CONTENIDO$modelo
  g <- m$graficas
  lab <- m$laboratorio
  cambio <- m$cambio
  div(class = "pagina",
      div(class = "c-cabecera", h1(m$titulo), p(class = "c-entrada", m$entrada)),
      bloque(m$fichas),
      tags$section(class = "cambio",
          div(h2(cambio$titulo), lapply(cambio$parrafos, tags$p),
              enlace("Ver la revisión completa en el informe", paste0(URL_INFORME, "modelo.html#modelo-contexto-2026"))),
          div(h3(cambio$aviso_titulo), lapply(cambio$aviso, tags$p))),
      div(class = "laboratorio",
          div(h2(lab$titulo), p(lab$texto),
              sliderInput("umbral", lab$etiqueta, min = 0.05, max = 0.8, step = 0.01,
                          value = round(MODELO$metadata$chosen_threshold, 2), ticks = FALSE, width = "100%"),
              uiOutput("umbral_titulo"),
              uiOutput("umbral_fichas")),
          div(h3(lab$matriz_titulo), uiOutput("matriz"), p(class = "c-nota", lab$matriz_nota))),
      div(class = "c-columnas",
          caja(plotlyOutput("g_comparacion", height = "auto"), g$comparacion$titulo, g$comparacion$meta, g$comparacion$nota),
          caja(tagList(div(class = "opciones", radioButtons("curva", NULL, inline = TRUE, choices = c("ROC" = "roc", "Precisión y sensibilidad" = "pr"), selected = "roc")),
                       plotlyOutput("g_curvas", height = "auto")),
               g$curvas$titulo, g$curvas$meta, g$curvas$nota)),
      div(class = "c-columnas",
          caja(plotlyOutput("g_calibracion", height = "auto"), g$calibracion$titulo, g$calibracion$meta, g$calibracion$nota),
          caja(plotlyOutput("g_importancia", height = "auto"), g$importancia$titulo, g$importancia$meta, g$importancia$nota)),
      lapply(m$despues, bloque))
}
