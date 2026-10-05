# Datos para reejecutar el análisis en R

Coloque aquí los microdatos departamentales del CNPV 2018 del DANE:

- `CNPV2018_5PER_A2_08.CSV`: personas, salud, edad, sexo y municipio.
- `CNPV2018_2HOG_A2_08.CSV`: hogares, cuartos y personas del hogar.
- `CNPV2018_1VIV_A2_08.CSV`: viviendas y estrato.

Los CSV se excluyen del repositorio. En este equipo el `.Rmd` también puede leerlos de la carpeta `datos/` del proyecto Python vecino. La ejecución del 5 de octubre de 2026 se verificó con esos tres archivos.

`mgn2018_municipios_atlantico.geojson` procede de la [capa Municipios del MGN integrado 2018 del DANE](https://geoportal.dane.gov.co/mparcgis/rest/services/MGN2018/Serv_CapaMunicipiosInt_2018/MapServer/0), filtrada por `DPTO_CCDGO='08'` y exportada en EPSG:4326. Contiene 23 polígonos con códigos municipales únicos. La unión con los microdatos se comprueba durante la ejecución del mapa.
