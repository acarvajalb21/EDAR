# Reglas de protección y cálculo. Replican dash_salud/app.py; pruebas/pruebas.R compara
# ambas implementaciones en todas las combinaciones de filtros.

BASE_TASA_MINIMA <- 200
COBERTURA_MINIMA <- 80

filtrar_cubo <- function(municipios, sexo, edad, zona, dificultad) {
  cubo <- EDA$cube
  cubo[(length(municipios) == 0 | cubo$municipio %in% municipios)
       & (sexo == "Todos" | cubo$sexo == sexo)
       & (edad == "Todos" | cubo$edad == edad)
       & (zona == "Todos" | cubo$zona == zona)
       & (dificultad == "Todos" | cubo$dificultad == dificultad), , drop = FALSE]
}

agregar <- function(filas, claves) {
  if (nrow(filas) == 0) {
    vacio <- filas[0, claves, drop = FALSE]
    vacio$n <- integer(0)
    vacio$sin_formal <- integer(0)
    return(vacio)
  }
  grupo <- interaction(filas[claves], drop = TRUE, sep = "\r", lex.order = TRUE)
  primeras <- filas[!duplicated(grupo), claves, drop = FALSE]
  orden <- grupo[!duplicated(grupo)]
  primeras$n <- as.integer(tapply(filas$n, grupo, sum)[as.character(orden)])
  primeras$sin_formal <- as.integer(tapply(filas$sin_formal, grupo, sum)[as.character(orden)])
  primeras <- primeras[primeras$n > 0, , drop = FALSE]
  rownames(primeras) <- NULL
  primeras
}

# Límite inferior redondeado; una selección de varios municipios usa el menor de ellos.
cobertura_de <- function(municipios, sexo = "Todos", edad = "Todos", zona = "Todos", dificultad = "Todos") {
  elegidos <- if (length(municipios) > 0) municipios else "Todos"
  valores <- unname(COBERTURA[paste(elegidos, sexo, edad, zona, dificultad, sep = "\r")])
  if (length(valores) == 0 || anyNA(valores)) return(NA_integer_)
  min(valores)
}

tasa_segura <- function(n, cobertura) {
  n >= BASE_TASA_MINIMA && !is.na(cobertura) && cobertura >= COBERTURA_MINIMA
}

# Agregado publicado aparte que describe la misma selección sin cruces adicionales.
referencia_agregada <- function(municipios, sexo, edad, zona, dificultad) {
  if (edad != "Todos" || dificultad != "Todos") return(NULL)
  if (length(municipios) == 1 && sexo == "Todos" && zona == "Todos") {
    fila <- EDA$municipal_overview[EDA$municipal_overview$municipio == municipios, , drop = FALSE]
    if (nrow(fila) == 0) return(NULL)
    return(list(etiqueta = municipios, n = fila$n, sin_formal = fila$sin_formal,
                fuente = "el panorama municipal de esta aplicación"))
  }
  if (length(municipios) == 0) {
    zs <- EDA$zone_sex_summary
    filas <- zs[(sexo == "Todos" | zs$sexo == sexo) & (zona == "Todos" | zs$zona == zona), , drop = FALSE]
    partes <- c(sexo, zona)[c(sexo, zona) != "Todos"]
    grupo <- if (length(partes) > 0) paste(partes, collapse = " · ") else "Toda la cohorte"
    return(list(etiqueta = grupo, n = sum(filas$n), sin_formal = sum(filas$sin_formal),
                fuente = "la comparación por sexo y zona de esta vista"))
  }
  NULL
}

resumen_seleccion <- function(municipios, sexo, edad, zona, dificultad) {
  filas <- filtrar_cubo(municipios, sexo, edad, zona, dificultad)
  n <- sum(filas$n)
  cobertura <- cobertura_de(municipios, sexo, edad, zona, dificultad)
  segura <- tasa_segura(n, cobertura)
  list(filas = filas, n = n, positivos = sum(filas$sin_formal), celdas = nrow(filas), cobertura = cobertura,
       tasa_segura = segura,
       referencia = if (segura) NULL else referencia_agregada(municipios, sexo, edad, zona, dificultad))
}

municipios_visibles <- function(filas, sexo, edad, zona, dificultad) {
  datos <- agregar(filas, "municipio")
  if (nrow(datos) == 0) return(datos)
  datos[vapply(seq_len(nrow(datos)), function(i) {
    tasa_segura(datos$n[i], cobertura_de(datos$municipio[i], sexo, edad, zona, dificultad))
  }, logical(1)), , drop = FALSE]
}

edades_visibles <- function(filas, municipios, sexo, zona) {
  datos <- agregar(filas, c("edad", "dificultad"))
  if (nrow(datos) == 0) return(datos)
  datos[vapply(seq_len(nrow(datos)), function(i) {
    tasa_segura(datos$n[i], cobertura_de(municipios, sexo, datos$edad[i], zona, datos$dificultad[i]))
  }, logical(1)), , drop = FALSE]
}

composicion_visible <- function(filas, municipios, sexo, edad, zona, dificultad) {
  amplia <- length(municipios) == 0 && edad == "Todos" && dificultad == "Todos"
  if (amplia) {
    zs <- EDA$zone_sex_summary
    datos <- zs[(sexo == "Todos" | zs$sexo == sexo) & (zona == "Todos" | zs$zona == zona), , drop = FALSE]
    return(list(datos = datos, amplia = TRUE, omitidos = 0L))
  }
  grupos <- agregar(filas, c("zona", "sexo"))
  if (nrow(grupos) == 0) return(list(datos = grupos, amplia = FALSE, omitidos = 0L))
  visibles <- vapply(seq_len(nrow(grupos)), function(i) {
    tasa_segura(grupos$n[i], cobertura_de(municipios, grupos$sexo[i], edad, grupos$zona[i], dificultad))
  }, logical(1))
  list(datos = grupos[visibles, , drop = FALSE], amplia = FALSE, omitidos = sum(!visibles))
}

fila_umbral <- function(valor) {
  elegido <- MODELO$metadata$chosen_threshold
  # La posición del deslizador más próxima al umbral validado muestra ese umbral exacto.
  objetivo <- if (abs(valor - round(elegido, 2)) < 1e-9) elegido else valor
  tabla <- MODELO$thresholds
  tabla[which.min(abs(tabla$threshold - objetivo)), , drop = FALSE]
}

metricas_umbral <- function(fila) {
  c(sensibilidad = if (fila$tp + fila$fn > 0) fila$tp / (fila$tp + fila$fn) else 0,
    precision = if (fila$tp + fila$fp > 0) fila$tp / (fila$tp + fila$fp) else 0,
    marcadas = fila$tp + fila$fp)
}
