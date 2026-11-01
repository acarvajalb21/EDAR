# Verifica reglas de protección, paridad con el Dash y reactividad de la aplicación.
# Ejecutar desde shiny_salud/: Rscript pruebas/pruebas.R

suppressPackageStartupMessages({
  library(testthat)
  library(shiny)
  library(bslib)
  library(plotly)
})
for (archivo in list.files("R", full.names = TRUE)) source(archivo, encoding = "UTF-8")

test_that("solo se distribuyen agregados publicables", {
  expect_setequal(list.files("data"), c("contenido.json", "eda.json", "modelo.json"))
  expect_length(list.files(".", pattern = "\\.(joblib|pkl|rds|CSV|csv)$", recursive = TRUE, ignore.case = TRUE), 0)
  cubo <- EDA$cube
  expect_true(all(cubo$n >= 30 & cubo$sin_formal >= 5 & cubo$n - cubo$sin_formal >= 5))
  expect_true(all(cubo$n %% 5 == 0 & cubo$sin_formal %% 5 == 0))
  panorama <- EDA$municipal_overview
  expect_true(all(panorama$n >= 100 & panorama$sin_formal >= 10 & panorama$n - panorama$sin_formal >= 10))
  expect_false("Piojó" %in% panorama$municipio)
  expect_false(any(c("score", "probability", "COD_ENCUESTAS") %in% names(cubo)))
})

test_that("los datos coinciden con los del Dash cuando está disponible", {
  dash <- file.path("..", "..", "EDAPYTHON-main", "dash_salud", "data")
  skip_if_not(dir.exists(dash))
  for (nombre in c("contenido.json", "eda.json", "modelo.json")) {
    expect_equal(unname(tools::md5sum(file.path("data", nombre))), unname(tools::md5sum(file.path(dash, nombre))))
  }
})

test_that("el relato solo publica agregados y coincide con el del Dash", {
  relato <- jsonlite::fromJSON("www/relato_datos.json")
  expect_equal(relato$cohorte, EXACTO$n)
  expect_equal(relato$fuera, EXACTO$sin_formal)
  expect_equal(sum(unlist(relato$acciones)) + relato$rutas$eps_no_atendido, relato$fuera)
  expect_setequal(names(relato$mapa$municipios), c("municipio", "trazo", "n", "sin_formal"))
  con_dato <- relato$mapa$municipios[!is.na(relato$mapa$municipios$n), ]
  panorama <- EDA$municipal_overview[match(con_dato$municipio, EDA$municipal_overview$municipio), ]
  expect_equal(con_dato$n, panorama$n)
  expect_equal(con_dato$sin_formal, panorama$sin_formal)
  dash <- file.path("..", "..", "EDAPYTHON-main", "dash_salud", "assets")
  skip_if_not(dir.exists(dash))
  for (nombre in c("relato.js", "relato.css", "relato_datos.json", "contenido.css")) {
    expect_equal(unname(tools::md5sum(file.path("www", nombre))), unname(tools::md5sum(file.path(dash, nombre))))
  }
})

test_that("las secciones se construyen y solo publican grupos protegidos", {
  expect_length(CONTENIDO$secciones, 9)
  for (clave in names(CONTENIDO$paginas)) expect_s3_class(vista_contenido(clave), "shiny.tag")
  expect_gt(length(barras_contenido()), 5)
  for (v in CONTENIDO$explorar$variables) {
    n <- vapply(v$categorias, function(c) c$n, numeric(1))
    fuera <- vapply(v$categorias, function(c) c$sin_formal, numeric(1))
    expect_true(all(n >= 100 & fuera >= 10 & n - fuera >= 10 & n %% 10 == 0 & fuera %% 10 == 0))
  }
  expect_equal(variable_comparada("edad")$v, "0,163")
  expect_equal(variable_comparada("municipio")$v, "0,085")
  expect_false(grepl("valor p ", tolower(as.character(vista_contenido("creacion"))), fixed = TRUE))
})

test_that("la frase no enuncia tasas ocultas", {
  oculta <- list(municipios = "Usiacurí", sexo = "Todos", edad = "Todos", zona = "Todos", dificultad = "Todos")
  texto <- as.character(frase_seleccion(oculta, do.call(resumen_seleccion, oculta)))
  expect_match(texto, "no permite mostrar una tasa", fixed = TRUE)
  expect_false(grepl("%", texto, fixed = TRUE))
  visible <- list(municipios = "Soledad", sexo = "Mujer", edad = "65+", zona = "Todos", dificultad = "Todos")
  texto <- as.character(frase_seleccion(visible, do.call(resumen_seleccion, visible)))
  expect_match(texto, "entre mujeres de 65 años o más", fixed = TRUE)
  expect_false(grepl("cifra del mapa", texto, fixed = TRUE))
  municipio <- list(municipios = "Malambo", sexo = "Todos", edad = "Todos", zona = "Todos", dificultad = "Todos")
  expect_match(as.character(frase_seleccion(municipio, do.call(resumen_seleccion, municipio))), "cifra del mapa", fixed = TRUE)
})

test_that("las tasas se ocultan con base o cobertura insuficientes", {
  expect_false(tasa_segura(100, 100))
  expect_false(tasa_segura(5000, 75))
  expect_false(tasa_segura(5000, NA))
  expect_true(tasa_segura(200, 80))
  oculta <- resumen_seleccion("Usiacurí", "Todos", "Todos", "Todos", "Todos")
  expect_false(oculta$tasa_segura)
  expect_equal(oculta$referencia$n, EDA$municipal_overview$n[EDA$municipal_overview$municipio == "Usiacurí"])
  expect_null(referencia_agregada("Usiacurí", "Hombre", "Todos", "Todos", "Todos"))
  expect_null(referencia_agregada(character(0), "Todos", "65+", "Todos", "Todos"))
  expect_equal(resumen_seleccion("Piojó", "Todos", "Todos", "Todos", "Todos")$celdas, 0)
})

test_that("el umbral validado reproduce la prueba del modelo", {
  fila <- fila_umbral(round(MODELO$metadata$chosen_threshold, 2))
  confusion <- MODELO$models$hist_gradient_boosting$test$confusion
  expect_equal(c(fila$tn, fila$fp, fila$fn, fila$tp), c(confusion$tn, confusion$fp, confusion$fn, confusion$tp))
  expect_equal(metricas_umbral(fila)[["marcadas"]], confusion$tp + confusion$fp)
})

test_that("Shiny y Dash dan el mismo resultado en todas las combinaciones de filtros", {
  esperado <- jsonlite::fromJSON("pruebas/esperado_dash.json")
  expect_length(esperado, 3375)
  huella <- function(d) sprintf("%d:%d:%d", nrow(d), as.integer(sum(d$n)), as.integer(sum(d$sin_formal)))
  distintos <- character(0)
  for (clave in names(esperado)) {
    partes <- strsplit(clave, "|", fixed = TRUE)[[1]]
    municipios <- if (partes[1] == "") character(0) else strsplit(partes[1], ";", fixed = TRUE)[[1]]
    r <- resumen_seleccion(municipios, partes[2], partes[3], partes[4], partes[5])
    ref <- if (is.null(r$referencia)) "-" else sprintf("%s:%d:%d", r$referencia$etiqueta, r$referencia$n, r$referencia$sin_formal)
    comp <- composicion_visible(r$filas, municipios, partes[2], partes[3], partes[4], partes[5])
    obtenido <- paste(r$n, r$positivos, r$celdas, ifelse(is.na(r$cobertura), "NA", r$cobertura), as.integer(r$tasa_segura), ref,
                      huella(municipios_visibles(r$filas, partes[2], partes[3], partes[4], partes[5])),
                      huella(edades_visibles(r$filas, municipios, partes[2], partes[4])),
                      huella(comp$datos), comp$omitidos, sep = "|")
    if (!identical(obtenido, esperado[[clave]])) distintos <- c(distintos, clave)
  }
  expect_identical(distintos, character(0))
})

aplicacion <- source("app.R", encoding = "UTF-8")$value

test_that("la aplicación reacciona a los filtros y respeta la protección", {
  testServer(aplicacion, {
    session$setInputs(f_municipio = NULL, f_sexo = "Todos", f_edad = "Todos", f_zona = "Todos", f_dificultad = "Todos",
                      metrica = "tasa", umbral = 0.22, curva = "roc", comp_variable = "municipio")
    expect_match(as.character(output$comp_lectura$html), "0,085", fixed = TRUE)
    expect_match(as.character(output$frase$html), "21,5", fixed = TRUE)
    expect_null(resumen()$referencia)

    session$setInputs(f_municipio = "Usiacurí")
    expect_match(as.character(output$frase$html), "no permite mostrar una tasa", fixed = TRUE)
    expect_false(grepl("%", as.character(output$frase$html), fixed = TRUE))
    expect_match(as.character(output$nota_referencia$html), "340", fixed = TRUE)
    expect_match(as.character(output$cinta$html), "Tasa oculta", fixed = TRUE)

    session$setInputs(f_municipio = NULL, f_sexo = "Mujer", f_edad = "0–19",
                      f_zona = "Centros poblados y rural disperso", f_dificultad = "Con dificultad funcional")
    expect_match(as.character(output$cinta$html), "Sin cruces publicables", fixed = TRUE)
    expect_equal(nrow(utils::read.csv(output$descargar, encoding = "UTF-8")), 0)

    session$setInputs(f_sexo = "Todos", f_edad = "Todos", f_zona = "Todos", f_dificultad = "Todos")
    descarga <- utils::read.csv(output$descargar, encoding = "UTF-8")
    expect_equal(names(descarga), c("municipio", "sexo", "edad", "zona", "dificultad", "n", "sin_formal"))
    expect_equal(nrow(descarga), nrow(EDA$cube))

    expect_match(as.character(output$umbral_titulo$html), "Umbral validado", fixed = TRUE)
    session$setInputs(umbral = 0.5)
    expect_match(as.character(output$umbral_titulo$html), "Escenario exploratorio", fixed = TRUE)
  })
})

cat("Shiny: verificaciones satisfactorias\n")
