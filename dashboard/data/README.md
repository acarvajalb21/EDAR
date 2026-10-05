# Datos públicos del dashboard

Estas tablas contienen **conteos agregados**, nunca filas de personas. Se generaron con
`dashboard/prepare_data.py` a partir de la base analítica local del EDA en R.

- `municipios.csv`: total y accesos en cada uno de los 23 municipios.
- `desgloses.csv`: conteos por municipio y una variable de análisis; `DEP` identifica
  el total departamental. Los grupos municipales de menos de 30 personas se omiten.
- `edad_dificultad.csv`: cruces amplios de edad y dificultad funcional; también se
  omiten los grupos municipales menores de 30 personas.
- `metadata.json`: cifras de control y procedencia.

Los porcentajes se calculan como `accedieron / n` dentro de cada grupo. La base
analítica está condicionada a personas que reportaron un problema de salud en los
30 días previos y cuya respuesta pudo clasificarse. No mide la cobertura de toda la
población ni permite concluir causalidad.
