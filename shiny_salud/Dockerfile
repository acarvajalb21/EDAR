FROM rocker/r-ver:4.6.1

ENV PORT=8080

# La etiqueta de rocker fija la fecha del repositorio de paquetes.
RUN install2.r --error --skipinstalled --ncpus 2 shiny bslib plotly jsonlite

WORKDIR /app
COPY app.R ./
COPY R/ R/
COPY data/ data/
COPY www/ www/

EXPOSE 8080
CMD ["Rscript", "-e", "shiny::runApp('/app', host = '0.0.0.0', port = as.integer(Sys.getenv('PORT')), launch.browser = FALSE)"]
