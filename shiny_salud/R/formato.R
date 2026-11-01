# Formatos numéricos en español: punto de miles y coma decimal.

fmt_int <- function(x) formatC(round(x), format = "d", big.mark = ".", decimal.mark = ",")

fmt_dec <- function(x, digitos = 3) formatC(x, format = "f", digits = digitos, decimal.mark = ",")

# Espacio no separable: el signo % no queda solo en otra línea.
fmt_pct <- function(x, digitos = 1) paste0(fmt_dec(100 * x, digitos), " %")

oracion_omitidos <- function(presentes, lugar, razon) {
  faltan <- setdiff(sort(ATLANTICO_MUNICIPIOS), presentes)
  if (length(faltan) == 0) return("")
  verbo <- if (length(faltan) == 1) "no aparece" else "no aparecen"
  paste0(" ", paste(faltan, collapse = ", "), " ", verbo, " ", lugar, ": ", razon, ".")
}
