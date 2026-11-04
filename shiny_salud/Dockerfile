FROM rocker/r-ver:4.6.1

ENV PORT=8080

# `fs`, dependencia de Shiny/bslib, necesita libuv en tiempo de ejecución.
RUN apt-get update && apt-get install -y --no-install-recommends libuv1-dev \
    && rm -rf /var/lib/apt/lists/*

# La etiqueta de rocker fija la fecha del repositorio de paquetes.
RUN install2.r --error --skipinstalled --ncpus 2 shiny bslib plotly jsonlite

WORKDIR /app
COPY app.R ./
COPY R/ R/
COPY data/ data/
COPY www/ www/

EXPOSE 8080
CMD ["Rscript", "-e", "shiny::runApp('/app', host = '0.0.0.0', port = as.integer(Sys.getenv('PORT')), launch.browser = FALSE)"]
