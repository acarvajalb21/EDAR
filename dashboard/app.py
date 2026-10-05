"""Dashboard público del EDA de acceso a salud en el Atlántico (CNPV 2018)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, ctx, dcc, html, no_update


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROOT = HERE.parent

MUNICIPAL = pd.read_csv(DATA / "municipios.csv", dtype={"codigo": str})
BREAKDOWNS = pd.read_csv(DATA / "desgloses.csv", dtype={"codigo": str})
AGE_DIFFICULTY = pd.read_csv(DATA / "edad_dificultad.csv", dtype={"codigo": str})
META = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))
GEO = json.loads(
    (ROOT / "datos" / "mgn2018_municipios_atlantico.geojson").read_text(encoding="utf-8")
)
# El GeoJSON del MGN tiene anillos exteriores en sentido contrario al que usa
# el renderizador geográfico de Plotly; sin invertirlos se colorea el exterior.
for feature in GEO["features"]:
    feature["geometry"]["coordinates"][0].reverse()

VARIABLES = {
    "sexo": "Sexo",
    "dificultad": "Condición funcional",
    "edad": "Edad",
    "zona": "Área de residencia",
    "estrato": "Estrato de la vivienda",
    "educacion": "Nivel educativo",
}
ORDERS = {
    "sexo": ["Mujer", "Hombre"],
    "dificultad": ["Sin dificultad funcional", "Con dificultad funcional"],
    "edad": ["0–19", "20–39", "40–59", "60–79", "80 o más"],
    "zona": ["Cabecera municipal", "Centro poblado", "Rural disperso"],
    "estrato": [f"Estrato {n}" for n in range(1, 7)] + ["Sin estrato", "Sin dato"],
    "educacion": [
        "Ninguno", "Preescolar", "Básica primaria", "Básica secundaria",
        "Media académica", "Media técnica", "Normalista", "Técnica o tecnológica",
        "Universitario", "Posgrado", "Sin dato",
    ],
}

INK = "#10374D"
BLUE = "#145B80"
BLUE_LIGHT = "#A8CFE3"
BLUE_PALE = "#E8F2F8"
MUTED = "#647C8B"
GRID = "#E7EEF2"
PAPER = "#FFFFFF"
AGE_ORDER = ORDERS["edad"]
DEPT_N = int(META["population"])
DEPT_ACCESSED = int(META["accessed"])
DEPT_RATE = DEPT_ACCESSED / DEPT_N * 100

MUNICIPAL["tasa"] = MUNICIPAL["accedieron"] / MUNICIPAL["n"] * 100
MUNICIPAL["no_accedieron"] = MUNICIPAL["n"] - MUNICIPAL["accedieron"]
NAMES = dict(zip(MUNICIPAL["codigo"], MUNICIPAL["municipio"]))


def number(value: int | float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def percent(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",") + " %"


def pp(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}".replace(".", ",") + " pp"


def metric_values(frame: pd.DataFrame, metric: str) -> pd.Series:
    access = frame["accedieron"] / frame["n"] * 100
    return access if metric == "access" else 100 - access


def chart_layout(**kwargs) -> dict:
    return {
        "font": {"family": "Inter, Segoe UI, Arial, sans-serif", "color": INK, "size": 12},
        "paper_bgcolor": PAPER,
        "plot_bgcolor": PAPER,
        "margin": {"l": 12, "r": 12, "t": 16, "b": 20},
        "hoverlabel": {"bgcolor": INK, "font_color": "white", "font_size": 12},
        **kwargs,
    }


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"color": MUTED, "size": 14})
    fig.update_layout(**chart_layout(xaxis={"visible": False}, yaxis={"visible": False}))
    return fig


def municipality_frame(code: str) -> tuple[str, int, int, float]:
    if code == "DEP":
        return "Atlántico", DEPT_N, DEPT_ACCESSED, DEPT_RATE
    row = MUNICIPAL.loc[MUNICIPAL["codigo"] == code]
    if row.empty:
        return "Atlántico", DEPT_N, DEPT_ACCESSED, DEPT_RATE
    item = row.iloc[0]
    return str(item["municipio"]), int(item["n"]), int(item["accedieron"]), float(item["tasa"])


def map_figure(code: str, metric: str) -> go.Figure:
    frame = MUNICIPAL.copy()
    frame["valor"] = metric_values(frame, metric)
    custom = frame[["municipio", "n", "accedieron", "no_accedieron"]].to_numpy()
    label = "Accedió" if metric == "access" else "No accedió"

    fig = go.Figure(
        go.Choropleth(
            geojson=GEO,
            featureidkey="properties.MPIO_CCDGO",
            locations=frame["codigo"],
            z=frame["valor"],
            customdata=custom,
            zmin=60 if metric == "access" else 0,
            zmax=100 if metric == "access" else 40,
            colorscale=[[0, "#EEF6FA"], [0.55, "#8FBFD8"], [1, BLUE]],
            marker_line_color="white",
            marker_line_width=0.8,
            colorbar={
                "thickness": 11,
                "len": 0.58,
                "x": 0.98,
                "tickfont": {"size": 10},
                "ticksuffix": "%",
                "outlinewidth": 0,
            },
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                + label
                + ": %{z:.1f} %<br>"
                + "Personas: %{customdata[1]:,}<br>"
                + "Accedieron: %{customdata[2]:,}<extra></extra>"
            ),
        )
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showland=False,
        projection_type="mercator",
    )
    fig.update_layout(**chart_layout(height=490, margin={"l": 0, "r": 0, "t": 0, "b": 0}))
    fig.update_layout(clickmode="event+select", uirevision="map")
    return fig


def ranking_figure(code: str, metric: str) -> go.Figure:
    frame = MUNICIPAL.copy()
    frame["valor"] = metric_values(frame, metric)
    frame = frame.sort_values("valor", ascending=True)
    colors = [BLUE if item == code else BLUE_LIGHT for item in frame["codigo"]]
    custom = frame[["codigo", "n", "accedieron"]].to_numpy()
    label = "Acceso" if metric == "access" else "Sin acceso"
    fig = go.Figure(
        go.Bar(
            x=frame["valor"],
            y=frame["municipio"],
            orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            text=[percent(x) for x in frame["valor"]],
            textposition="outside",
            textfont={"size": 10, "color": INK},
            customdata=custom,
            hovertemplate=(
                "<b>%{y}</b><br>" + label + ": %{x:.1f} %<br>"
                "Personas: %{customdata[1]:,}<extra></extra>"
            ),
        )
    )
    benchmark = DEPT_RATE if metric == "access" else 100 - DEPT_RATE
    fig.add_vline(
        x=benchmark,
        line_color=INK,
        line_width=1,
        line_dash="dot",
        annotation_text="Atlántico",
        annotation_position="top left",
        annotation_font={"size": 10, "color": MUTED},
    )
    fig.update_layout(
        **chart_layout(
            height=590,
            bargap=0.35,
            margin={"l": 8, "r": 50, "t": 12, "b": 28},
            xaxis={
                "range": [0, 108], "ticksuffix": "%", "showgrid": True,
                "gridcolor": GRID, "zeroline": False, "fixedrange": True,
            },
            yaxis={"showgrid": False, "tickfont": {"size": 10}, "fixedrange": True, "automargin": True},
        )
    )
    fig.update_layout(clickmode="event+select")
    return fig


def breakdown_figure(code: str, variable: str) -> tuple[go.Figure, str]:
    frame = BREAKDOWNS.loc[
        (BREAKDOWNS["codigo"] == code) & (BREAKDOWNS["variable"] == variable)
    ].copy()
    if frame.empty:
        return empty_figure("No hay grupos con tamaño suficiente en esta selección."), ""

    order = ORDERS.get(variable, [])
    frame["order"] = frame["categoria"].map({value: i for i, value in enumerate(order)})
    frame = frame.sort_values(["order", "categoria"], na_position="last")
    frame["pct_acceso"] = frame["accedieron"] / frame["n"] * 100
    frame["pct_no"] = 100 - frame["pct_acceso"]
    categories = frame["categoria"].tolist()[::-1]
    frame = frame.iloc[::-1]
    custom = frame[["n", "accedieron"]].to_numpy()

    fig = go.Figure()
    for name, values, color in [
        ("Accedió", frame["pct_acceso"], BLUE),
        ("No accedió", frame["pct_no"], BLUE_LIGHT),
    ]:
        fig.add_trace(
            go.Bar(
                name=name,
                x=values,
                y=categories,
                orientation="h",
                marker_color=color,
                customdata=custom,
                text=[percent(x, 0) if x >= 10 else "" for x in values],
                textposition="inside",
                insidetextanchor="middle",
                textfont={"color": "white" if name == "Accedió" else INK, "size": 11},
                hovertemplate=(
                    "<b>%{y}</b><br>" + name + ": %{x:.1f} %<br>"
                    "Base del grupo: %{customdata[0]:,}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **chart_layout(
            barmode="stack",
            height=max(290, 44 * len(frame) + 100),
            margin={"l": 10, "r": 20, "t": 18, "b": 24},
            legend={"orientation": "h", "y": 1.13, "x": 0, "font": {"size": 11}},
            xaxis={
                "range": [0, 100], "ticksuffix": "%", "showgrid": True,
                "gridcolor": GRID, "zeroline": False, "fixedrange": True,
            },
            yaxis={"showgrid": False, "automargin": True, "fixedrange": True},
        )
    )
    note = (
        "Los grupos con menos de 30 personas no se muestran. "
        if code != "DEP" else ""
    ) + "Cada barra usa como denominador las personas de su propia categoría."
    return fig, note


def age_figure(code: str) -> tuple[go.Figure, str]:
    frame = AGE_DIFFICULTY.loc[AGE_DIFFICULTY["codigo"] == code].copy()
    if frame.empty:
        return empty_figure("No hay cruces de edad con tamaño suficiente."), ""
    fig = go.Figure()
    for difficulty, color in [
        ("Sin dificultad funcional", BLUE_LIGHT),
        ("Con dificultad funcional", BLUE),
    ]:
        line = frame.loc[frame["dificultad"] == difficulty].copy()
        line["edad"] = pd.Categorical(line["edad"], categories=AGE_ORDER, ordered=True)
        line = line.sort_values("edad")
        if line.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=line["edad"].astype(str),
                y=line["accedieron"] / line["n"] * 100,
                mode="lines+markers",
                name=difficulty,
                line={"color": color, "width": 3},
                marker={"size": 9, "line": {"color": PAPER, "width": 1.5}},
                customdata=line[["n", "accedieron"]].to_numpy(),
                hovertemplate=(
                    "<b>%{x} años</b><br>" + difficulty + ": %{y:.1f} %<br>"
                    "Personas: %{customdata[0]:,}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **chart_layout(
            height=350,
            margin={"l": 40, "r": 16, "t": 24, "b": 44},
            legend={"orientation": "h", "y": 1.20, "x": 0, "font": {"size": 11}},
            xaxis={"title": "Edad (años)", "showgrid": False, "categoryorder": "array", "categoryarray": AGE_ORDER},
            yaxis={
                "title": "Acceso (%)", "range": [0, 100], "ticksuffix": "%",
                "gridcolor": GRID, "zeroline": False,
            },
        )
    )
    note = "Se omiten cruces municipales con menos de 30 personas." if code != "DEP" else ""
    return fig, note


def kpi(label: str, value: str, detail: str, emphasis: bool = False) -> html.Div:
    return html.Div(
        [html.Span(label, className="kpi-label"), html.Strong(value), html.Small(detail)],
        className="kpi" + (" kpi-emphasis" if emphasis else ""),
    )


app = Dash(__name__, assets_folder=str(HERE / "assets"))
app.title = "Atlas de acceso a salud · Atlántico 2018"
server = app.server

app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.P("ATLAS INTERACTIVO  /  CNPV 2018", className="eyebrow"),
                        html.H1("¿Quién accedió a atención formal en el Atlántico?"),
                        html.P(
                            "Explora la brecha territorial y las diferencias entre grupos de personas "
                            "que reportaron un problema de salud.",
                            className="hero-lead",
                        ),
                        html.Div(
                            [
                                html.Span("23 municipios", className="hero-tag"),
                                html.Span("136.034 respuestas clasificables", className="hero-tag"),
                                html.Span("Censo 2018", className="hero-tag"),
                            ],
                            className="hero-tags",
                        ),
                    ],
                    className="hero-content",
                ),
                html.Div(
                    [
                        html.Span("LECTURA CLAVE", className="hero-aside-label"),
                        html.Strong(percent(DEPT_RATE)),
                        html.P(
                            "accedió a atención formal entre quienes reportaron un problema "
                            "de salud y tuvieron respuesta clasificable"
                        ),
                    ],
                    className="hero-aside",
                ),
            ],
            className="hero",
        ),
        html.Main(
            [
                html.Section(
                    [
                        html.Div(
                            [
                                html.Label("Territorio", htmlFor="municipality-select"),
                                dcc.Dropdown(
                                    id="municipality-select",
                                    options=[{"label": "Todo el Atlántico", "value": "DEP"}]
                                    + [
                                        {"label": row.municipio, "value": row.codigo}
                                        for row in MUNICIPAL.itertuples()
                                    ],
                                    value="DEP",
                                    clearable=False,
                                    searchable=True,
                                    className="control-dropdown",
                                ),
                            ],
                            className="control-field municipality-field",
                        ),
                        html.Div(
                            [
                                html.Label("Indicador territorial"),
                                dcc.RadioItems(
                                    id="metric-select",
                                    options=[
                                        {"label": "Acceso", "value": "access"},
                                        {"label": "Sin acceso", "value": "no_access"},
                                    ],
                                    value="access",
                                    inline=True,
                                    className="segmented",
                                ),
                            ],
                            className="control-field",
                        ),
                        html.Button("Restablecer", id="reset-button", n_clicks=0, className="reset-button"),
                    ],
                    className="controls",
                    **{"aria-label": "Filtros del dashboard"},
                ),
                html.Div(id="selection-label", className="selection-label"),
                html.Section(id="kpi-grid", className="kpi-grid"),
                html.Section(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.Span("01 / TERRITORIO", className="section-kicker"),
                                     html.H2("El mapa cuenta una historia desigual"),
                                     html.P("Pasa el cursor para ver el municipio. Haz clic para explorarlo en todo el tablero.")],
                                    className="section-heading",
                                ),
                                dcc.Loading(dcc.Graph(id="municipality-map", config={"displaylogo": False}), type="circle"),
                                html.P("El color representa la proporción dentro de cada municipio; el tamaño de la base aparece al pasar el cursor.", className="chart-note"),
                                html.Details(
                                    [
                                        html.Summary("Ver los 23 nombres ubicados en el mapa"),
                                        html.A(
                                            html.Img(
                                                src=app.get_asset_url("mapa_municipios_con_nombres.png"),
                                                alt="Mapa del Atlántico con el nombre de cada uno de sus 23 municipios",
                                            ),
                                            href=app.get_asset_url("mapa_municipios_con_nombres.png"),
                                            target="_blank",
                                            rel="noopener noreferrer",
                                        ),
                                    ],
                                    className="map-labels",
                                ),
                            ],
                            className="panel map-panel",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [html.Span("02 / COMPARACIÓN", className="section-kicker"),
                                     html.H2("Los 23 municipios, uno a uno"),
                                     html.P("Selecciona una barra para fijar el municipio.")],
                                    className="section-heading",
                                ),
                                dcc.Graph(id="municipality-ranking", config={"displaylogo": False}),
                            ],
                            className="panel ranking-panel",
                        ),
                    ],
                    className="territory-grid",
                ),
                html.Section(
                    [
                        html.Div(
                            [
                                html.Span("03 / EXPLORACIÓN", className="section-kicker"),
                                html.H2("Mira la brecha desde distintos ángulos"),
                                html.P("Cambia la variable para comparar acceso y no acceso con la misma escala de 0 a 100 %.")
                            ],
                            className="section-heading explore-heading",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Label("Desglosar por", htmlFor="variable-select"),
                                        dcc.Dropdown(
                                            id="variable-select",
                                            options=[{"label": name, "value": key} for key, name in VARIABLES.items()],
                                            value="dificultad",
                                            clearable=False,
                                            searchable=False,
                                            className="control-dropdown",
                                        ),
                                    ],
                                    className="control-field breakdown-control",
                                ),
                                html.Button("Descargar estos datos", id="download-button", n_clicks=0, className="download-button"),
                                dcc.Download(id="download-data"),
                            ],
                            className="explore-controls",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [dcc.Graph(id="breakdown-chart", config={"displaylogo": False}),
                                     html.P(id="breakdown-note", className="chart-note")],
                                    className="panel breakdown-panel",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [html.Span("EDAD Y CONDICIÓN", className="section-kicker"),
                                             html.H3("La edad modifica la lectura"),
                                             html.P("Tasa de acceso por tramo de edad y dificultad funcional.")],
                                            className="section-heading",
                                        ),
                                        dcc.Graph(id="age-chart", config={"displaylogo": False}),
                                        html.P(id="age-note", className="chart-note"),
                                    ],
                                    className="panel age-panel",
                                ),
                            ],
                            className="explore-grid",
                        ),
                    ],
                    className="explore-section",
                ),
                html.Section(
                    [
                        html.Div(
                            [html.Span("04 / INTERPRETACIÓN", className="section-kicker"),
                             html.H2("Qué significa la selección"),
                             html.P(id="insight-text")],
                            className="insight-copy",
                        ),
                        html.Div(
                            [html.Strong("Lee con cuidado"),
                             html.P("Estas son asociaciones descriptivas. No prueban que sexo, edad, dificultad funcional o lugar de residencia causen el acceso observado.")],
                            className="insight-caution",
                        ),
                    ],
                    className="insight-section",
                ),
                html.Details(
                    [
                        html.Summary("Datos, definiciones y límites del análisis"),
                        html.Div(
                            [
                                html.P("Universo: personas del Atlántico que declararon un problema de salud en los 30 días previos al CNPV 2018 y cuya respuesta de atención pudo clasificarse. El indicador combina tratamiento principal y atención recibida en una entidad de seguridad social; no equivale a afiliación ni a cobertura universal."),
                                html.P("Los conteos proceden del EDA en R. Este dashboard solo distribuye tablas agregadas. Se omiten cruces municipales de menos de 30 personas; por eso la suma de algunas categorías visibles puede no coincidir con el total del municipio."),
                                html.P("Fuente: DANE, CNPV 2018. Geometría: MGN integrado 2018. Los porcentajes usan el número de personas de cada grupo como denominador. No se aplicó ponderación por omisión censal."),
                                html.A("Leer metodología y análisis completo en Bookdown ↗", href="https://acarvajalb21.github.io/EDAR/", target="_blank", rel="noopener noreferrer"),
                            ],
                            className="method-body",
                        ),
                    ],
                    className="methodology",
                ),
            ],
            className="page-content",
        ),
        html.Footer(
            [html.Span("Alejandro Carvajal y Mateo Chang · Universidad del Norte"),
             html.Span("CNPV 2018 · Atlántico · Dashboard descriptivo")],
            className="footer",
        ),
    ],
    className="app-shell",
)


@callback(
    Output("municipality-select", "value"),
    Input("municipality-map", "clickData"),
    Input("municipality-ranking", "clickData"),
    Input("reset-button", "n_clicks"),
    prevent_initial_call=True,
)
def select_municipality(map_click, ranking_click, _reset_clicks):
    source = ctx.triggered_id
    if source == "reset-button":
        return "DEP"
    if source == "municipality-map" and map_click:
        code = map_click["points"][0].get("location")
        return code if code in NAMES else no_update
    if source == "municipality-ranking" and ranking_click:
        code = ranking_click["points"][0].get("customdata", [None])[0]
        return code if code in NAMES else no_update
    return no_update


@callback(
    Output("selection-label", "children"),
    Output("kpi-grid", "children"),
    Output("municipality-map", "figure"),
    Output("municipality-ranking", "figure"),
    Output("insight-text", "children"),
    Input("municipality-select", "value"),
    Input("metric-select", "value"),
)
def update_overview(code, metric):
    code = code if code in NAMES else "DEP"
    name, n, accessed, rate = municipality_frame(code)
    no_access = n - accessed
    difference = rate - DEPT_RATE
    scope_label = "Vista departamental" if code == "DEP" else f"Municipio seleccionado · {name}"
    cards = [
        kpi("Personas en la base", number(n), "Con respuesta clasificable"),
        kpi("Accedieron", percent(rate, 2), f"{number(accessed)} personas", emphasis=True),
        kpi("No accedieron", percent(100 - rate, 2), f"{number(no_access)} personas"),
        kpi("Frente al Atlántico", "—" if code == "DEP" else pp(difference),
            "Base departamental: " + percent(DEPT_RATE, 2)),
    ]
    if code == "DEP":
        insight = (
            f"En el Atlántico, {number(accessed)} de {number(n)} personas de la base "
            f"accedieron a atención formal ({percent(rate, 2)}). Elige un municipio "
            "para ver su distancia respecto al promedio departamental y explorar sus grupos."
        )
    else:
        position = "por encima" if difference > 0 else "por debajo" if difference < 0 else "igual"
        distance = f"{abs(difference):.1f}".replace(".", ",")
        comparison = (
            f"{distance} puntos porcentuales {position} del total del Atlántico"
            if position != "igual" else "la misma tasa que el total del Atlántico"
        )
        insight = (
            f"{name} registró {number(accessed)} accesos entre {number(n)} personas "
            f"({percent(rate, 2)}), {comparison} "
            f"({percent(DEPT_RATE, 2)}). Compara el tamaño de cada grupo antes de interpretar la diferencia."
        )
    return (
        scope_label, cards, map_figure(code, metric), ranking_figure(code, metric),
        insight,
    )


@callback(
    Output("breakdown-chart", "figure"),
    Output("breakdown-note", "children"),
    Input("municipality-select", "value"),
    Input("variable-select", "value"),
)
def update_breakdown(code, variable):
    code = code if code in NAMES else "DEP"
    variable = variable if variable in VARIABLES else "dificultad"
    return breakdown_figure(code, variable)


@callback(
    Output("age-chart", "figure"),
    Output("age-note", "children"),
    Input("municipality-select", "value"),
)
def update_age(code):
    code = code if code in NAMES else "DEP"
    return age_figure(code)


@callback(
    Output("download-data", "data"),
    Input("download-button", "n_clicks"),
    State("municipality-select", "value"),
    State("variable-select", "value"),
    prevent_initial_call=True,
)
def download_breakdown(_clicks, code, variable):
    code = code if code in NAMES else "DEP"
    variable = variable if variable in VARIABLES else "dificultad"
    frame = BREAKDOWNS.loc[
        (BREAKDOWNS["codigo"] == code) & (BREAKDOWNS["variable"] == variable)
    ].copy()
    frame["porcentaje_acceso"] = (frame["accedieron"] / frame["n"] * 100).round(2)
    frame["no_accedieron"] = frame["n"] - frame["accedieron"]
    return dcc.send_data_frame(
        frame.to_csv,
        f"eda_atlantico_{code}_{variable}.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
