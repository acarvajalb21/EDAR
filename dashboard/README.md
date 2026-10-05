# Atlas interactivo del acceso a salud en el Atlántico

Dashboard en **Plotly Dash** que complementa el [EDA en Bookdown](https://acarvajalb21.github.io/EDAR/).
**Versión pública:** [abrir el dashboard en Google Cloud Run](https://eda-salud-atlantico-409319239507.us-east1.run.app/).
Permite seleccionar un municipio desde el mapa, el ranking o el buscador; cambiar entre acceso y
no acceso; examinar desgloses por sexo, dificultad funcional, edad, zona, estrato y educación;
y descargar la tabla agregada de la vista actual.

## Ejecutar localmente

Desde la raíz del repositorio:

```powershell
python -m venv dashboard/.venv
dashboard/.venv/Scripts/python.exe -m pip install -r dashboard/requirements.txt
dashboard/.venv/Scripts/python.exe dashboard/app.py
```

Abrir <http://127.0.0.1:8050>. En macOS o Linux, usar `dashboard/.venv/bin/python`.

## Actualizar los datos

El dashboard usa solo tablas agregadas dentro de `dashboard/data/`. La base de personas permanece
fuera de Git. Si se regenera el EDA, volver a crear los agregados con:

```powershell
python dashboard/prepare_data.py --input ruta/a/base_analitica_acceso_salud.csv
```

El script exige las cifras de control del EDA verificado (136.034 personas y 107.384 accesos),
comprueba los 23 códigos municipales y omite los cruces municipales con menos de 30 personas.
No se necesita el archivo de personas para ejecutar el dashboard publicado.

## Publicación en Google Cloud Run

GitHub Pages publica el libro estático, pero no ejecuta el servidor de Dash. El `Dockerfile`
incluido prepara una imagen que contiene **solo** la app, las tablas agregadas y el GeoJSON.
Cloud Run asigna una URL pública al servicio; se necesita un proyecto de Google Cloud con
facturación habilitada para desplegarlo.
El archivo `.gcloudignore` deja fuera los microdatos y permite enviar los CSV agregados que
requiere la app. La cuenta de Google Cloud puede ser distinta de la cuenta de GitHub.

Proyecto creado para este trabajo: `eda-salud-atlantico-2018`. Tras activar la facturación,
desde la raíz del repositorio con `gcloud` autenticado:

```powershell
gcloud config set project eda-salud-atlantico-2018
gcloud run deploy eda-salud-atlantico --source . --region us-east1 --allow-unauthenticated --min-instances 0 --max-instances 2 --memory 512Mi --cpu 1
```

El servicio no necesita los microdatos CSV. `--min-instances 0` evita mantener una instancia
encendida cuando nadie consulta el dashboard, aunque la primera visita puede tardar más.

## Lectura responsable

El universo son personas que reportaron un problema de salud en los 30 días previos al CNPV 2018
y cuya respuesta pudo clasificarse. Las diferencias son descriptivas y no establecen causalidad.
Los porcentajes se calculan dentro de cada grupo; los cruces omitidos pueden hacer que las
categorías visibles no sumen el total municipal.
