# Carga los agregados publicables. La app no lee microdatos ni el modelo serializado.

EDA <- jsonlite::fromJSON("data/eda.json")
MODELO <- jsonlite::fromJSON("data/modelo.json")
CONTENIDO <- jsonlite::fromJSON("data/contenido.json", simplifyVector = FALSE)
NOMBRE <- CONTENIDO$nombre

EXACTO <- list(n = EDA$metadata$total_labeled_exact, sin_formal = EDA$metadata$no_access_exact)
EDADES <- EDA$metadata$age_bands
MUNICIPIOS_CUBO <- sort(unique(EDA$cube$municipio))
SEXOS <- c("Hombre", "Mujer")
ZONAS <- c("Cabecera", "Centros poblados y rural disperso")
DIFICULTADES <- c("Con dificultad funcional", "Sin dificultad funcional")

# Los 23 municipios DIVIPOLA; un municipio ausente del cubo se nombra en la interfaz.
ATLANTICO_MUNICIPIOS <- c(
  "Barranquilla", "Baranoa", "Campo de la Cruz", "Candelaria", "Galapa", "Juan de Acosta",
  "Luruaco", "Malambo", "Manatí", "Palmar de Varela", "Piojó", "Polonuevo", "Ponedera",
  "Puerto Colombia", "Repelón", "Sabanagrande", "Sabanalarga", "Santa Lucía", "Santo Tomás",
  "Soledad", "Suan", "Tubará", "Usiacurí"
)

COBERTURA <- local({
  claves <- vapply(EDA$coverage_index$key, paste, character(1), collapse = "\r")
  stats::setNames(EDA$coverage_index$coverage_floor_5pct, claves)
})

NOMBRES_MODELO <- c(
  baseline = "Referencia (prevalencia)", logistica = "Regresión logística",
  random_forest = "Bosque aleatorio", hist_gradient_boosting = "Boosting de histogramas"
)
NOMBRES_VARIABLE <- c(
  U_MPIO = "Municipio", P_EDADR = "Edad agrupada", H_DONDE_PREPALIM = "Lugar de preparación de alimentos",
  P_NIVEL_ANOSR = "Nivel educativo", VA1_ESTRATO = "Estrato reportado", HA_TOT_PER = "Personas en el hogar",
  CONDICION_FISICA = "Dificultad funcional", UA_CLASE = "Clase de asentamiento", P_SEXO = "Sexo reportado",
  V_MAT_PISO = "Material del piso", V_MAT_PARED = "Material de las paredes", P_PARENTESCOR = "Parentesco",
  VF_INTERNET = "Internet en la vivienda", HOGAR_OTROS_ENFERMOS = "Otros enfermos en el hogar",
  SECCION_PCT_ENFERMOS = "Enfermos en la sección censal"
)
VARIABLES_NUEVAS <- c("HOGAR_OTROS_ENFERMOS", "SECCION_PCT_ENFERMOS")
