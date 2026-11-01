# Bloques de las secciones. Los textos y tablas vienen de data/contenido.json, común con el Dash.

URL_INFORME <- "https://acarvajalb21.github.io/EDAR/"

caja <- function(contenido, titulo = NULL, meta = NULL, nota = NULL) {
  div(class = "c-bloque",
      if (!is.null(titulo)) h3(titulo),
      if (!is.null(meta)) span(class = "c-meta", meta),
      contenido,
      if (!is.null(nota)) p(class = "c-nota", nota))
}

tabla_bloque <- function(b) {
  clase <- function(j) if (j <= b$texto_cols) "izq"
  destacar <- if (is.null(b$destacar)) -1 else b$destacar + 1
  div(class = "c-tabla-marco", tags$table(class = "c-tabla",
    tags$thead(tags$tr(lapply(seq_along(b$columnas), function(j) tags$th(scope = "col", class = clase(j), b$columnas[[j]])))),
    tags$tbody(lapply(seq_along(b$filas), function(i) {
      fila <- b$filas[[i]]
      tags$tr(class = if (i == destacar) "destacada", lapply(seq_along(fila), function(j) tags$td(class = clase(j), fila[[j]])))
    }))))
}

ruta_bloque <- function(b) {
  lista <- div(class = "ruta-lista", lapply(b$lista, function(i) {
    div(class = "ruta-fila",
        div(class = "ruta-linea", span(i$nombre), strong(i$valor)),
        div(class = "ruta-pista", div(class = paste("ruta-relleno", i$clase), style = sprintf("width:%.2f%%", i$ancho))))
  }))
  caja(tagList(HTML(b$svg), lista), b$titulo, b$meta, b$nota)
}

pestanas_bloque <- function(b) {
  paneles <- lapply(seq_along(b$pestanas), function(i) {
    nav_panel(b$pestanas[[i]]$titulo, value = as.character(i), div(class = "c-pila", lapply(b$pestanas[[i]]$bloques, bloque)))
  })
  div(class = "c-subnav", do.call(navset_underline, c(list(id = b$id), paneles)))
}

bloque <- function(b) {
  switch(b$tipo,
    parrafos = caja(tagList(div(class = "c-texto", lapply(b$parrafos, tags$p)),
                            if (!is.null(b$enlace)) tags$a(class = "c-enlace", b$enlace$texto, href = b$enlace$url, target = "_blank", rel = "noopener noreferrer")),
                    b$titulo),
    destacado = div(class = paste("c-destacado", b$tono), span(class = "c-rotulo", b$rotulo), tags$p(b$texto)),
    fichas = div(class = "c-fichas", lapply(b$items, function(i) ficha(i$etiqueta, i$valor, i$nota, i$tono))),
    lista = caja(div(class = if (identical(b$columnas, 2L)) "c-lista dos" else "c-lista",
                     lapply(b$items, function(i) div(class = "c-item", tags$strong(i$rotulo), tags$p(i$texto)))), b$titulo),
    etapas = {
      lista <- caja(tags$ol(class = "c-etapas", lapply(b$items, function(i) tags$li(tags$strong(i$titulo), tags$p(i$texto)))), b$titulo)
      if (isTRUE(b$horizontal)) div(class = "c-horizontal", lista) else lista
    },
    tabla = caja(tabla_bloque(b), b$titulo, b$meta, b$nota),
    barras = caja(plotlyOutput(b$id, height = "auto"), b$titulo, b$meta, b$nota),
    ruta = ruta_bloque(b),
    permite = div(class = "c-permite",
                  div(h3(b$si_titulo), tags$ul(lapply(b$si, tags$li))),
                  div(h3(b$no_titulo), tags$ul(lapply(b$no, tags$li)))),
    glosario = caja(tags$dl(class = "c-glosario", lapply(b$items, function(i) div(tags$dt(i$termino), tags$dd(i$definicion)))), b$titulo),
    columnas = div(class = "c-columnas", lapply(b$bloques, bloque)),
    pila = div(class = "c-pila", lapply(b$bloques, bloque)),
    pestanas = pestanas_bloque(b),
    preguntas = tags$section(class = "preguntas", h3(b$titulo),
                             lapply(b$items, function(i) pregunta(i$pregunta, i$respuesta))),
    referencias = caja(tags$ol(class = "c-referencias", lapply(b$items, function(i) {
      tags$li(i$texto, " ", if (!is.null(i$url)) enlace("Ver fuente", i$url))
    })), b$titulo),
    enlaces = caja(tags$ul(class = "c-enlaces", lapply(b$items, function(i) tags$li(enlace(i$texto, i$url)))), b$titulo),
    pie = p(class = "c-pie", b$texto),
    stop("Bloque desconocido: ", b$tipo)
  )
}

vista_contenido <- function(clave) {
  pagina <- CONTENIDO$paginas[[clave]]
  div(class = "c-pagina",
      if (!is.null(pagina$titulo)) div(class = "c-cabecera", h1(pagina$titulo), p(class = "c-entrada", pagina$entrada)),
      lapply(pagina$bloques, bloque))
}

# Recorre los bloques para conectar cada gráfica con su salida.
barras_de <- function(bloques) {
  unlist(lapply(bloques, function(b) {
    if (identical(b$tipo, "barras")) return(list(b))
    c(barras_de(b$bloques), unlist(lapply(b$pestanas, function(p) barras_de(p$bloques)), recursive = FALSE))
  }), recursive = FALSE)
}

barras_contenido <- function() {
  c(unlist(lapply(CONTENIDO$paginas, function(p) barras_de(p$bloques)), recursive = FALSE, use.names = FALSE),
    barras_de(CONTENIDO$explorar$ajuste))
}

variable_comparada <- function(clave) {
  Filter(function(v) identical(v$id, clave), CONTENIDO$explorar$variables)[[1]]
}

lectura_comparada <- function(v) {
  div(class = "c-lectura",
      div(span(class = "c-rotulo", "V de Cramér"), tags$strong(class = "c-v", v$v)),
      div(p(class = "c-rango", v$rango), p(class = "c-lectura-texto", v$lectura)))
}

g_comparada <- function(v) {
  n <- vapply(v$categorias, function(c) c$n, numeric(1))
  fuera <- vapply(v$categorias, function(c) c$sin_formal, numeric(1))
  g_barras(vapply(v$categorias, function(c) c$categoria, character(1)), round(100 * fuera / n, 1), "%", "fuera", n)
}
