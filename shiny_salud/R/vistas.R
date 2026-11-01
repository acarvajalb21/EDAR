# Vistas de la aplicación. Los textos conservan las reglas de interpretación del proyecto.

enlace <- function(texto, url) tags$a(texto, href = url, target = "_blank", rel = "noopener noreferrer")

panel_g <- function(titulo, meta, contenido, nota = NULL) {
  div(class = "panel",
      div(class = "panel-cabeza", h3(titulo), if (!is.null(meta)) span(class = "panel-meta", meta)),
      contenido,
      if (!is.null(nota)) p(class = "panel-nota", nota))
}

ficha <- function(etiqueta, valor, nota, clase = "") {
  div(class = paste("ficha", clase),
      div(class = "ficha-etiqueta", etiqueta),
      div(class = "ficha-valor", valor),
      div(class = "ficha-nota", nota))
}

tabla_html <- function(df, leyenda = NULL) {
  tags$div(class = "tabla-marco", tags$table(class = "tabla",
    if (!is.null(leyenda)) tags$caption(leyenda),
    tags$thead(tags$tr(lapply(names(df), function(n) tags$th(scope = "col", n)))),
    tags$tbody(lapply(seq_len(nrow(df)), function(i) {
      tags$tr(lapply(seq_along(df), function(j) tags$td(as.character(df[[j]][i]))))
    }))))
}

banda <- function(x1, a1, b1, x2, a2, b2, color) {
  m <- (x1 + x2) / 2
  sprintf('<path d="M%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f L%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f Z" fill="%s" fill-opacity=".2"/>',
          x1, a1, m, a1, m, a2, x2, a2, x2, b2, m, b2, m, b1, x1, b1, color)
}

nodo <- function(x, y, alto, color) {
  sprintf('<rect x="%.1f" y="%.1f" width="9" height="%.1f" rx="2" fill="%s"/>', x, y, alto, color)
}

rotulo <- function(x, y, titulo, cifra, clase = "") {
  sprintf('<text x="%.1f" y="%.1f" class="ruta-nombre %s">%s</text><text x="%.1f" y="%.1f" class="ruta-cifra">%s</text>',
          x, y, clase, titulo, x, y + 18, cifra)
}

# Diagrama de ruta: el ancho de cada banda es proporcional a las personas que la siguen.
ruta_svg <- function() {
  b <- EDA$metadata$label_breakdown_exact
  total <- EXACTO$n
  dentro <- b$eps_atendido + b$medico_particular
  fuera <- EXACTO$sin_formal
  k <- 250 / total
  xa <- 196; xb <- 548; xc <- 800
  a0 <- 50
  yd <- 34; hd <- dentro * k
  yf <- yd + hd + 28; hf <- fuera * k
  he <- b$eps_atendido * k; hp <- b$medico_particular * k; ho <- b$otras_acciones_o_ninguna * k
  hn <- max(b$eps_no_atendido * k, 3)
  ye <- 18; yp <- ye + he + 20
  yo <- yp + hp + 26; yn <- yo + ho + 16
  etiqueta <- function(v) paste0(fmt_int(v), " · ", fmt_pct(v / total))
  partes <- c(
    banda(xa + 9, a0, a0 + hd, xb, yd, yd + hd, TK$dentro),
    banda(xa + 9, a0 + hd, a0 + 250, xb, yf, yf + hf, TK$fuera),
    banda(xb + 9, yd, yd + he, xc, ye, ye + he, TK$dentro),
    banda(xb + 9, yd + he, yd + hd, xc, yp, yp + hp, TK$dentro),
    banda(xb + 9, yf, yf + ho, xc, yo, yo + ho, TK$fuera),
    banda(xb + 9, yf + ho, yf + hf, xc, yn, yn + hn, TK$fuera),
    nodo(xa, a0, 250, TK$tinta), nodo(xb, yd, hd, TK$dentro), nodo(xb, yf, hf, TK$fuera),
    nodo(xc, ye, he, TK$dentro), nodo(xc, yp, hp, TK$dentro), nodo(xc, yo, ho, TK$fuera), nodo(xc, yn, hn, TK$fuera),
    sprintf('<text x="0" y="168" class="ruta-total">%s</text><text x="0" y="192" class="ruta-nombre">personas con respuesta</text><text x="0" y="210" class="ruta-nombre">clasificable</text>', fmt_int(total)),
    rotulo(xb - 200, yd + hd / 2 - 8, "Dentro de la ruta formal", etiqueta(dentro), "fuerte"),
    rotulo(xb - 200, yf + hf / 2 - 2, "Fuera de la ruta formal", etiqueta(fuera), "fuerte"),
    rotulo(xc + 20, ye + he / 2 - 8, "EPS y recibió atención", etiqueta(b$eps_atendido)),
    rotulo(xc + 20, yp + 2, "Médico particular", etiqueta(b$medico_particular)),
    rotulo(xc + 20, yo + ho / 2 - 8, "Otra acción principal o ninguna", etiqueta(b$otras_acciones_o_ninguna)),
    rotulo(xc + 20, yn + 8, "EPS sin atención", etiqueta(b$eps_no_atendido))
  )
  descripcion <- paste0("De ", fmt_int(total), " personas, ", fmt_int(dentro), " quedaron dentro de la ruta formal y ",
                        fmt_int(fuera), " fuera. Solo ", fmt_int(b$eps_no_atendido), " acudieron a su EPS sin recibir atención.")
  HTML(sprintf('<svg class="ruta-svg" viewBox="0 0 1090 360" role="img" aria-label="%s">%s</svg>',
               descripcion, paste(partes, collapse = "")))
}

ruta_lista <- function() {
  b <- EDA$metadata$label_breakdown_exact
  total <- EXACTO$n
  filas <- list(
    list("EPS y recibió atención", b$eps_atendido, "dentro"), list("Médico particular", b$medico_particular, "dentro"),
    list("Otra acción principal o ninguna", b$otras_acciones_o_ninguna, "fuera"),
    list("EPS sin atención", b$eps_no_atendido, "fuera")
  )
  div(class = "ruta-lista",
      lapply(filas, function(f) {
        div(class = "ruta-fila",
            div(class = "ruta-linea", span(f[[1]]), strong(paste0(fmt_int(f[[2]]), " · ", fmt_pct(f[[2]] / total)))),
            div(class = "ruta-pista", div(class = paste("ruta-relleno", f[[3]]),
                                          style = sprintf("width:%.2f%%", 100 * f[[2]] / total))))
      }))
}

vista_panorama <- function() {
  tagList(div(id = "relato"), vista_contenido("panorama"))
}

pregunta <- function(titulo, respuesta) {
  tags$details(class = "pregunta", tags$summary(titulo), tags$p(respuesta))
}

# Resume la selección en una frase; solo enuncia una tasa cuando las reglas lo permiten.
frase_seleccion <- function(s, r) {
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
    div(class = "frase", tags$p(paste0(lugar, grupo, ", "), tags$strong(paste("\u2248", fmt_pct(r$positivos / r$n))), " quedó fuera de la ruta formal."),
        span(class = "frase-base", paste0("Base aproximada: ", fmt_int(r$n), " personas en ", r$celdas, if (r$celdas == 1) " cruce publicable" else " cruces publicables",
                                          if (length(s$municipios) == 1 && is.na(quien)) ". Se suman solo los cruces publicables, por eso puede diferir de la cifra del mapa.")))
  } else {
    div(class = "frase", tags$p(paste0(lugar, grupo, ", esta selección "), tags$em("no permite mostrar una tasa"), "."),
        span(class = "frase-base", if (r$celdas == 0) "Ningún cruce cumple las reglas de publicación. Prueba a quitar un filtro." else paste0("≈ ", fmt_int(r$n), " personas en cruces publicables. La protección de grupos pequeños oculta la tasa.")))
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
      radioButtons("comp_variable", NULL, inline = TRUE, choices = opciones, selected = opciones[[1]]),
      uiOutput("comp_lectura"),
      caja(plotlyOutput("g_comparada", height = "auto"), "Fuera de la ruta formal por categoría", "Porcentaje dentro de cada categoría"),
      p(class = "c-pie", explorar$comparar_nota))
}

vista_explorar <- function() {
  explorar <- CONTENIDO$explorar
  div(class = "vista",
      div(class = "encabezado",
          h1(HTML("Elige un grupo y mira qué <em>cambia</em>.")),
          p(class = "entrada", paste0("Compara la proporción cuya acción principal quedó fuera de EPS con atención o médico particular. Al filtrar cambian el grupo, su denominador y la cobertura publicable.",
                                      oracion_omitidos(MUNICIPIOS_CUBO, "en el selector", "ninguno de sus cruces cumple las reglas de publicación")))),
      div(class = "c-subnav", navset_underline(id = "sub_explorar",
        nav_panel(explorar$pestanas[[1]], value = "grupos", div(class = "explorar-marco",
          tags$aside(class = "riel", `aria-label` = "Filtros",
              div(class = "filtros",
                  selectizeInput("f_municipio", "Municipio", choices = MUNICIPIOS_CUBO, multiple = TRUE,
                                 options = list(placeholder = "Todos los municipios", plugins = list("remove_button"))),
                  filtro("f_sexo", "Sexo reportado", SEXOS),
                  filtro("f_edad", "Edad", EDADES),
                  filtro("f_zona", "Zona", ZONAS),
                  filtro("f_dificultad", "Dificultad funcional diaria", DIFICULTADES),
                  actionLink("limpiar", "Limpiar filtros", class = "limpiar")),
              uiOutput("cinta")),
          div(class = "explorar-contenido",
              uiOutput("frase"),
              uiOutput("nota_referencia"),
              panel_g("Municipios en la selección", "Comparar territorios",
                      tagList(
                        radioButtons("metrica", NULL, inline = TRUE, choices = c("Porcentaje" = "tasa", "Personas" = "conteo"), selected = "tasa"),
                        plotlyOutput("g_ranking", height = "auto"),
                        tags$details(class = "ver-datos", tags$summary("Ver estos datos en una tabla"), uiOutput("tabla_municipios"))),
                      "Se omiten municipios sin cobertura o tamaño suficientes para mostrar una tasa."),
              div(class = "dos-columnas",
                  panel_g("Cómo cambia por edad", "Porcentaje fuera de la ruta formal",
                          plotlyOutput("g_edad", height = "auto"),
                          "Porcentajes dentro de cada grupo publicado; los cruces omitidos no entran en la línea."),
                  panel_g("Sexo y zona de residencia", "Porcentaje fuera de la ruta formal",
                          plotlyOutput("g_composicion", height = "auto"), textOutput("nota_composicion", inline = TRUE))),
              div(class = "descarga",
                  downloadButton("descargar", "Descargar selección agregada", class = "boton-secundario", icon = NULL),
                  span(class = "descarga-nota", "El archivo contiene solo celdas publicables y recuentos redondeados.")),
              p(class = "fuente", paste0("Protección de grupos pequeños: ", EDA$metadata$rules, " El cubo publicado cubre ",
                                         fmt_dec(EDA$metadata$coverage_pct, 2), " % del universo clasificable antes de aplicar filtros."))))),
        nav_panel(explorar$pestanas[[2]], value = "comparar", vista_comparar()),
        nav_panel(explorar$pestanas[[3]], value = "ajuste", div(class = "c-pila", lapply(explorar$ajuste, bloque)))))
  )
}

vista_modelo <- function() {
  m <- MODELO
  f <- m$models$hist_gradient_boosting$test
  cambio <- m$version_change
  equidad <- m$equity
  ic <- m$uncertainty$intervals_95$selected_ap
  escenarios <- c(v1_umbral_validado = "Versión 1, su umbral",
                  v2_mismas_personas_marcadas = "Versión 2, mismas personas marcadas",
                  v2_umbral_validado = "Versión 2, su umbral")
  tabla_grupos <- do.call(rbind, lapply(names(escenarios), function(k) {
    x <- m$same_flagged[[k]]
    data.frame(Escenario = escenarios[[k]], Marcadas = fmt_int(x$flagged), Sensibilidad = fmt_pct(x$recall),
               `Con dificultad` = fmt_pct(x$recall_difficulty), `Sin dificultad` = fmt_pct(x$recall_no_difficulty),
               `60 años o más` = fmt_pct(x$recall_60_plus), check.names = FALSE)
  }))
  p_tabla <- m$prioritization
  tabla_prior <- data.frame(`Se revisa` = paste0(fmt_pct(p_tabla$fraction, 0), " con mayor puntuación"),
                            Personas = fmt_int(p_tabla$reviewed), `De la clase` = fmt_int(p_tabla$positives_found),
                            Precisión = fmt_pct(p_tabla$precision), Sensibilidad = fmt_pct(p_tabla$recall), check.names = FALSE)
  div(class = "vista",
      div(class = "encabezado",
          h1(HTML("Un modelo para ordenar perfiles, <em>con límites claros</em>.")),
          p(class = "entrada", "Comparamos cuatro enfoques. El mejor fue boosting de histogramas, evaluado en viviendas reservadas del mismo censo de 2018. Las cifras son agregadas; esta aplicación no calcula predicciones sobre personas.")),
      div(class = "fichas tres",
          ficha("Average Precision", fmt_dec(f$pr_auc), paste0("Prevalencia: ", fmt_dec(m$models$baseline$test$pr_auc), " · versión anterior: ", fmt_dec(cambio$previous_test_ap)), "destacada"),
          ficha("ROC-AUC", fmt_dec(f$roc_auc), "Capacidad de ordenar casos · prueba interna"),
          ficha("Brier", fmt_dec(f$brier), "Menor es mejor · prueba interna")),
      div(class = "cambio",
          div(h2(HTML("Qué <em>cambió</em> en esta versión")),
              p(paste0("Las ", m$audit_2026$alternatives, " alternativas de preparación de datos y ajuste probadas antes no mejoraron el modelo de 26 variables. La mejora llegó con dos variables de contexto: cuántas personas más del hogar declararon un problema de salud y qué proporción lo declaró en la sección censal.")),
              p(paste0("El AP de validación pasó de ", fmt_dec(cambio$previous_validation_ap), " a ", fmt_dec(cambio$new_validation_ap),
                       ", y en secciones no vistas al ajustar, de ", fmt_dec(cambio$previous_unseen_sections_ap), " a ", fmt_dec(cambio$new_unseen_sections_ap), "."))),
          div(class = "cambio-aviso", h3("Cómo leerlo"),
              p("Estas variables no revelan la acción de la persona, pero se miden en el mismo censo. Pueden reflejar problemas más leves o la forma de responder; no indican una causa ni una barrera."))),
      div(class = "laboratorio",
          div(class = "laboratorio-control",
              h2("¿Qué cambia al marcar a más personas?"),
              p("Mueve el umbral para comparar alcance y falsas alarmas en la prueba de 2018. La posición validada se eligió en validación; las demás son escenarios exploratorios."),
              sliderInput("umbral", "Umbral de clasificación", min = 0.05, max = 0.8, step = 0.01,
                          value = round(m$metadata$chosen_threshold, 2), ticks = FALSE, width = "100%"),
              uiOutput("umbral_titulo"),
              uiOutput("umbral_fichas")),
          div(class = "laboratorio-matriz", h3("Aciertos y errores"), uiOutput("matriz"),
              p(class = "panel-nota", "Clase positiva: acción principal fuera de la ruta formal. Conjunto de prueba reservado."))),
      div(class = "dos-columnas",
          panel_g("Comparación en prueba", "Average Precision", plotlyOutput("g_comparacion", height = "auto"),
                  "AP resume el ordenamiento de la clase minoritaria. Su referencia es la prevalencia."),
          panel_g("Curvas de discriminación", NULL,
                  tagList(radioButtons("curva", NULL, inline = TRUE, choices = c("ROC" = "roc", "Precisión–sensibilidad" = "pr"), selected = "roc"),
                          plotlyOutput("g_curvas", height = "auto")),
                  "Curvas resumidas; AP y ROC-AUC provienen de todas las puntuaciones de prueba.")),
      div(class = "dos-columnas",
          panel_g("Probabilidad y frecuencia observada", "Calibración", plotlyOutput("g_calibracion", height = "auto"),
                  "Cada punto agrupa cerca de una décima parte de la prueba. La cercanía a la diagonal no valida el modelo para otro año."),
          panel_g("Variables que más contribuyeron", "Importancia por permutación", plotlyOutput("g_importancia", height = "auto"),
                  "En azul, las dos variables añadidas. Mide dependencia predictiva, no efecto causal.")),
      panel_g("¿Y si solo se revisara una parte?", "Priorización exploratoria", tabla_html(tabla_prior),
              "No es una recomendación: no hay costos ni capacidad definidos, y el modelo no debe usarse para decidir sobre personas."),
      panel_g("Diferencias entre grupos", "Sensibilidad en la prueba interna", tabla_html(tabla_grupos),
              paste0("Con las mismas personas marcadas, la versión 2 mejora en todos los grupos; con su umbral marca a menos personas y pierde sensibilidad. Ajustada por edad, la sensibilidad es ",
                     fmt_pct(equidad$age_adjusted_recall_difficulty), " con dificultad funcional y ", fmt_pct(equidad$age_adjusted_recall_no_difficulty),
                     " sin ella: la brecha persiste y la sensibilidad en mayores de 60 sigue baja.")),
      div(class = "limites",
          h2("Cómo leer este modelo"),
          div(class = "limites-rejilla",
              div(h3("Separación cuidadosa"), p("Entrenamiento, validación y prueba se separaron por vivienda. Preprocesamiento y ajustes se hicieron dentro de entrenamiento; el umbral se eligió en validación.")),
              div(h3("Una mejora acotada"), p(paste0("El AP fue ", fmt_dec(f$pr_auc), ", con intervalo interno del 95 % de ", fmt_dec(ic[1]), " a ", fmt_dec(ic[2]), ". La discriminación es moderada."))),
              div(h3("Uso responsable"), p("Los datos son transversales de 2018. Falta validación temporal y geográfica antes de aplicarlo a personas actuales o decisiones de atención."))))
  )
}
