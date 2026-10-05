if (.Platform$OS.type == "windows") {
  try(Sys.setlocale("LC_CTYPE", "Spanish_Colombia.utf8"), silent = TRUE)
  pandoc_dir <- "C:/Program Files/RStudio/resources/app/bin/quarto/bin/tools"
  if (file.exists(file.path(pandoc_dir, "pandoc.exe")) &&
      !nzchar(Sys.getenv("RSTUDIO_PANDOC"))) {
    Sys.setenv(RSTUDIO_PANDOC = pandoc_dir)
  }
}

if (!requireNamespace("bookdown", quietly = TRUE)) {
  stop("Falta bookdown. Instálelo con install.packages('bookdown').")
}

bookdown::render_book("index.Rmd", output_format = "bookdown::gitbook")
