"""Genera tablas y figuras agregadas para el Bookdown, sin exportar microdatos.

Ejecutar desde la raíz EDAR:
    python scripts/preparar_resumen.py --data-dir RUTA_CSV_DANE

Reutiliza exactamente la construcción de la etiqueta y las uniones auditadas en
``ml_salud.entrenar.load_data``. Verifica que los CSV correspondan a los usados
por el experimento antes de combinar resultados descriptivos y predictivos.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve
from sklearn.metrics import roc_auc_score, roc_curve


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT
sys.path.insert(0, str(ROOT))

from ml_salud.entrenar import group_ids, load_data, split_three  # noqa: E402
from ml_salud.esquema import FEATURES  # noqa: E402


DEFAULT_DATA_DIR = ROOT / "datos"
DATA = BOOK / "data"
FIGURES = BOOK / "figures"
RESULTS = ROOT / "ml_salud" / "resultados"

BLUE = "#147D91"
RED = "#C64F43"
INK = "#183246"
MUTED = "#667B89"
GRID = "#DDE9EC"

AGE_LABELS = {
    1: "0–4", 2: "5–9", 3: "10–14", 4: "15–19", 5: "20–24",
    6: "25–29", 7: "30–34", 8: "35–39", 9: "40–44", 10: "45–49",
    11: "50–54", 12: "55–59", 13: "60–64", 14: "65–69", 15: "70–74",
    16: "75–79", 17: "80–84", 18: "85–89", 19: "90–94", 20: "95–99",
    21: "100 o más",
}
MUNICIPALITIES = {
    1: "Barranquilla", 78: "Baranoa", 137: "Campo de la Cruz",
    141: "Candelaria", 296: "Galapa", 372: "Juan de Acosta",
    421: "Luruaco", 433: "Malambo", 436: "Manatí",
    520: "Palmar de Varela", 549: "Piojó", 558: "Polonuevo",
    560: "Ponedera", 573: "Puerto Colombia", 606: "Repelón",
    634: "Sabanagrande", 638: "Sabanalarga", 675: "Santa Lucía",
    685: "Santo Tomás", 758: "Soledad", 770: "Suan",
    832: "Tubará", 849: "Usiacurí",
}
FEATURE_LABELS = {
    "U_MPIO": ("Municipio", "Territorio", "Categórica"),
    "UA_CLASE": ("Clase de área censal", "Territorio", "Categórica"),
    "P_SEXO": ("Sexo registrado", "Persona", "Categórica"),
    "P_EDADR": ("Grupo quinquenal de edad", "Persona", "Ordinal"),
    "P_PARENTESCOR": ("Parentesco con la jefatura del hogar", "Persona", "Categórica"),
    "PA1_GRP_ETNIC": ("Autorreconocimiento étnico", "Persona", "Categórica"),
    "CONDICION_FISICA": ("Alguna dificultad funcional diaria", "Persona", "Categórica"),
    "P_ALFABETA": ("Sabe leer y escribir", "Persona", "Categórica"),
    "P_NIVEL_ANOSR": ("Nivel educativo registrado", "Persona", "Ordinal"),
    "P_EST_CIVIL": ("Estado civil", "Persona", "Categórica"),
    "H_NRO_CUARTOS": ("Cuartos del hogar", "Hogar", "Recuento"),
    "H_NRO_DORMIT": ("Cuartos para dormir", "Hogar", "Recuento"),
    "H_DONDE_PREPALIM": ("Lugar de preparación de alimentos", "Hogar", "Categórica"),
    "H_AGUA_COCIN": ("Fuente de agua para cocinar", "Hogar", "Categórica"),
    "HA_TOT_PER": ("Personas en el hogar", "Hogar", "Recuento"),
    "V_TIPO_VIV": ("Tipo de vivienda", "Vivienda", "Categórica"),
    "V_MAT_PARED": ("Material de las paredes", "Vivienda", "Categórica"),
    "V_MAT_PISO": ("Material del piso", "Vivienda", "Categórica"),
    "VA_EE": ("Energía eléctrica", "Vivienda", "Categórica"),
    "VA1_ESTRATO": ("Estrato del recibo de energía", "Vivienda", "Ordinal"),
    "VB_ACU": ("Acueducto", "Vivienda", "Categórica"),
    "VC_ALC": ("Alcantarillado", "Vivienda", "Categórica"),
    "VD_GAS": ("Gas natural", "Vivienda", "Categórica"),
    "VE_RECBAS": ("Recolección de basuras", "Vivienda", "Categórica"),
    "VF_INTERNET": ("Internet", "Vivienda", "Categórica"),
    "V_TIPO_SERSA": ("Tipo de servicio sanitario", "Vivienda", "Categórica"),
}


def configure_plot() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelcolor": INK, "text.color": INK,
        "axes.edgecolor": GRID, "axes.spines.top": False,
        "axes.spines.right": False, "axes.titleweight": "bold",
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "grid.color": GRID,
    })


def finish(fig: plt.Figure, name: str) -> None:
    fig.tight_layout(pad=1.8)
    fig.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def aggregate(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = frame.groupby(cols, dropna=False, observed=True)["SIN_ACCESO"].agg(
        n="size", sin_formal="sum"
    ).reset_index()
    out["con_formal"] = out["n"] - out["sin_formal"]
    out["porcentaje_sin_formal"] = out["sin_formal"] / out["n"] * 100
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    frame.to_csv(DATA / name, index=False, encoding="utf-8-sig", float_format="%.6f")


def make_eda(frame: pd.DataFrame, source: dict, quality: dict) -> dict:
    frame = frame.copy()
    frame["grupo_edad"] = frame["P_EDADR"].map(AGE_LABELS)
    frame["sexo"] = frame["P_SEXO"].map({1: "Hombre", 2: "Mujer"})
    frame["dificultad"] = frame["CONDICION_FISICA"].map(
        {1: "Con dificultad", 2: "Sin dificultad"}
    )
    frame["clase_area"] = frame["UA_CLASE"].map(
        {1: "Cabecera", 2: "Centro poblado", 3: "Rural disperso"}
    )
    frame["municipio"] = frame["U_MPIO"].map(MUNICIPALITIES)
    if frame["municipio"].isna().any():
        raise AssertionError("Hay códigos de municipio sin nombre verificado")

    total = len(frame)
    positives = int(frame["SIN_ACCESO"].sum())
    summary = {
        **source,
        "con_formal": total - positives,
        "pct_sin_formal": positives / total * 100,
        "pct_con_formal": (total - positives) / total * 100,
    }
    (DATA / "resumen_general.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv("resumen_general.csv", pd.DataFrame([{
        "personas_censo": source["people"], "problema_salud": source["sick"],
        "sin_etiqueta": source["unlabeled"], "cohorte": total,
        "sin_formal": positives, "con_formal": total - positives,
        "porcentaje_sin_formal": positives / total * 100,
        "porcentaje_con_formal": (total - positives) / total * 100,
        "union_hogar": source["house_match"], "union_vivienda": source["dwell_match"],
    }]))
    write_csv("huellas_archivos.csv", pd.DataFrame([
        {"archivo": name, "sha256": digest}
        for name, digest in source["source_sha256"].items()
    ]))

    label = pd.DataFrame([
        ("EPS/entidad, atendido", source["label_breakdown"]["eps_atendido"], "Con acceso según regla"),
        ("Médico particular", source["label_breakdown"]["medico_particular"], "Con acceso según regla"),
        ("EPS/entidad, no atendido", source["label_breakdown"]["eps_no_atendido"], "Sin acceso según regla"),
        ("Otras acciones o ninguna", source["label_breakdown"]["otras_acciones_o_ninguna"], "Sin acceso según regla"),
    ], columns=["tratamiento_principal", "n", "clasificacion"])
    label["porcentaje"] = label["n"] / total * 100
    write_csv("composicion_etiqueta.csv", label)

    groups = {
        "dificultad": ["dificultad"],
        "sexo": ["sexo"],
        "sexo_dificultad": ["sexo", "dificultad"],
        "edad": ["P_EDADR", "grupo_edad"],
        "edad_dificultad": ["P_EDADR", "grupo_edad", "dificultad"],
        "municipio": ["U_MPIO", "municipio"],
        "clase_area": ["UA_CLASE", "clase_area"],
        "estrato": ["VA1_ESTRATO"],
    }
    for name, cols in groups.items():
        tab = aggregate(frame, cols)
        if name in ("edad_dificultad", "sexo_dificultad"):
            # No publicar celdas de combinaciones pequeñas, ni siquiera en CSV.
            tab = tab.loc[(tab["n"] >= 30) & (tab["sin_formal"] >= 5)
                          & (tab["con_formal"] >= 5)].copy()
            tab["publicable"] = True
        if name in ("municipio", "edad"):
            tab = tab.loc[(tab["n"] >= 30) & (tab["sin_formal"] >= 5)
                          & (tab["con_formal"] >= 5)].copy()
        write_csv(f"{name}.csv", tab)

    q = pd.DataFrame(quality["features"])
    q["descripcion"] = q["feature"].map(lambda x: FEATURE_LABELS[x][0])
    q = q.sort_values("pct", ascending=False)
    write_csv("calidad_variables.csv", q)

    dictionary = pd.DataFrame([
        {"variable": feature, "descripcion": FEATURE_LABELS[feature][0],
         "nivel": FEATURE_LABELS[feature][1], "escala": FEATURE_LABELS[feature][2]}
        for feature in FEATURES
    ])
    write_csv("diccionario_modelo.csv", dictionary)

    # Los cuadros para publicación nunca incluyen filas individuales.
    return summary


def plot_eda(summary: dict) -> None:
    lab = pd.read_csv(DATA / "composicion_etiqueta.csv")
    fig, ax = plt.subplots(figsize=(8.3, 3.7))
    labels = lab["tratamiento_principal"].tolist()[::-1]
    vals = lab["n"].tolist()[::-1]
    colors = [BLUE if item == "Con acceso según regla" else RED
              for item in lab["clasificacion"].tolist()[::-1]]
    ax.barh(labels, vals, color=colors, height=0.58)
    for y, value in enumerate(vals):
        ax.text(value + 1300, y, f"{value:,.0f}".replace(",", "."), va="center", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_xlabel("Personas")
    ax.set_title("Composición de la etiqueta operativa", loc="left")
    ax.grid(axis="x", alpha=.7)
    ax.set_axisbelow(True)
    finish(fig, "composicion_etiqueta.png")

    dif = pd.read_csv(DATA / "dificultad.csv")
    fig, ax = plt.subplots(figsize=(7.8, 3.8))
    dif = dif.set_index("dificultad").reindex(["Con dificultad", "Sin dificultad"])
    ax.barh(dif.index, 100 - dif["porcentaje_sin_formal"], color=BLUE, label="Con acceso según regla")
    ax.barh(dif.index, dif["porcentaje_sin_formal"], left=100 - dif["porcentaje_sin_formal"], color=RED, label="Sin acceso según regla")
    for y, row in enumerate(dif.itertuples()):
        ax.text(102, y, f"n = {row.n:,.0f}".replace(",", "."), va="center", fontsize=9)
    ax.set_xlim(0, 121)
    ax.set_xlabel("Porcentaje dentro de cada grupo")
    ax.set_title("Clasificación por dificultad funcional declarada", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.19), ncol=2, frameon=False)
    ax.invert_yaxis()
    finish(fig, "dificultad.png")

    age = pd.read_csv(DATA / "edad_dificultad.csv")
    age = age.loc[age["publicable"] == True].sort_values("P_EDADR")  # noqa: E712
    fig, ax = plt.subplots(figsize=(11.2, 4.5))
    for name, color in [("Con dificultad", RED), ("Sin dificultad", BLUE)]:
        part = age.loc[age["dificultad"] == name]
        ax.plot(part["P_EDADR"], part["porcentaje_sin_formal"], marker="o", markersize=4,
                linewidth=2.3, label=name, color=color)
    ax.set_xticks(list(AGE_LABELS), list(AGE_LABELS.values()), rotation=60, ha="right")
    ax.set_ylabel("Sin acceso formal según regla (%)")
    ax.set_xlabel("Edad al censo (grupos quinquenales)")
    ax.set_title("La relación cambia con la edad", loc="left")
    ax.grid(axis="y", alpha=.8)
    ax.legend(frameon=False)
    finish(fig, "edad_dificultad.png")

    sex = pd.read_csv(DATA / "sexo_dificultad.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    positions = np.arange(2)
    width = .34
    for offset, name, color in [(-width / 2, "Con dificultad", RED),
                                (width / 2, "Sin dificultad", BLUE)]:
        part = sex.set_index(["sexo", "dificultad"])
        values = [part.loc[(s, name), "porcentaje_sin_formal"] for s in ("Hombre", "Mujer")]
        ax.bar(positions + offset, values, width, label=name, color=color)
    ax.set_xticks(positions, ["Hombres", "Mujeres"])
    ax.set_ylabel("Sin acceso formal según regla (%)")
    ax.set_title("Sexo y dificultad funcional", loc="left")
    ax.grid(axis="y", alpha=.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    finish(fig, "sexo_dificultad.png")

    mun = pd.read_csv(DATA / "municipio.csv").sort_values("porcentaje_sin_formal")
    fig, ax = plt.subplots(figsize=(9.1, 8.7))
    ax.barh(mun["municipio"], mun["porcentaje_sin_formal"], color=BLUE, height=.7)
    ax.axvline(summary["pct_sin_formal"], color=RED, linestyle="--", linewidth=1.7,
               label=f"Atlántico: {summary['pct_sin_formal']:.1f} %")
    ax.set_xlabel("Sin acceso formal según regla (%)")
    ax.set_title("Municipios con recuentos publicables", loc="left")
    ax.grid(axis="x", alpha=.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    finish(fig, "municipio.png")

    quality = pd.read_csv(DATA / "calidad_variables.csv").head(12).sort_values("pct")
    fig, ax = plt.subplots(figsize=(8.5, 5.1))
    ax.barh(quality["descripcion"], quality["pct"], color=BLUE)
    ax.set_xlabel("Faltantes o códigos de no informa (%)")
    ax.set_title("Variables con mayor ausencia en los predictores", loc="left")
    ax.grid(axis="x", alpha=.7)
    ax.set_axisbelow(True)
    finish(fig, "faltantes.png")


def make_model(results: dict, frame: pd.DataFrame) -> None:
    names = {
        "baseline": "Prevalencia",
        "logistica": "Regresión logística",
        "random_forest": "Random Forest",
        "hist_gradient_boosting": "Boosting de histogramas",
    }
    rows = []
    for key, label in names.items():
        model = results["models"][key]
        test = results["test_metrics"][key]
        rows.append({"modelo": label, "codigo": key,
                     "ap_cv": model["cv_pr_auc"], "ap_validacion": model["validation"]["pr_auc"],
                     "ap_prueba": test["pr_auc"], "roc_auc_prueba": test["roc_auc"],
                     "brier_prueba": test["brier"], "f1_prueba": test["f1"],
                     "precision_prueba": test["precision"], "recall_prueba": test["recall"],
                     "umbral": test["threshold"]})
    write_csv("comparacion_modelos.csv", pd.DataFrame(rows))
    write_csv("hiperparametros.csv", pd.DataFrame([
        {"parametro": key.removeprefix("model__"), "valor": str(value)}
        for key, value in results["models"][results["selected_model"]]["best_params"].items()
    ]))

    split = pd.DataFrame([
        {"particion": label, "n": results["split"][key]["n"],
         "viviendas": results["split"][key]["dwellings"],
         "n_sin_formal": results["split"][key]["no_access"],
         "porcentaje_sin_formal": results["split"][key]["prevalence"] * 100}
        for key, label in (("train", "Entrenamiento"), ("validation", "Validación"), ("test", "Prueba"))
    ])
    write_csv("particiones.csv", split)

    imp = pd.DataFrame(results["permutation_importance_validation"])
    imp["descripcion"] = imp["feature"].map(lambda x: FEATURE_LABELS[x][0])
    write_csv("importancia.csv", imp)

    calibration = pd.DataFrame(results["calibration_deciles_test"])
    write_csv("calibracion.csv", calibration)

    chosen = results["test_metrics"][results["selected_model"]]
    at_half = results["selected_test_at_0_5"]
    write_csv("umbrales_prueba.csv", pd.DataFrame([
        {"criterio": "Elegido en validación", **{
            key: chosen[key] for key in ("threshold", "f1", "precision", "recall", "specificity")
        }},
        {"criterio": "Umbral convencional 0,5", **{
            key: at_half[key] for key in ("threshold", "f1", "precision", "recall", "specificity")
        }},
    ]))
    conf = chosen["confusion"]
    write_csv("matriz_confusion.csv", pd.DataFrame([{
        "verdaderos_negativos": conf["tn"], "falsos_positivos": conf["fp"],
        "falsos_negativos": conf["fn"], "verdaderos_positivos": conf["tp"],
        "marcados": conf["fp"] + conf["tp"],
    }]))
    bounds = results["test_uncertainty"]["intervals_95"]
    write_csv("incertidumbre.csv", pd.DataFrame([
        {"metrica": key, "inferior": value[0], "superior": value[1]}
        for key, value in bounds.items()
    ]))
    sub = results["subgroups_test"]["CONDICION_FISICA"]
    write_csv("equidad_dificultad.csv", pd.DataFrame([
        {"grupo": "Con dificultad", **sub["1.0"]},
        {"grupo": "Sin dificultad", **sub["2.0"]},
    ]))

    models = pd.read_csv(DATA / "comparacion_modelos.csv")
    fig, ax = plt.subplots(figsize=(8, 4.3))
    p = np.arange(len(models))
    ax.barh(p + .16, models["ap_validacion"], height=.31, color=BLUE, label="Validación")
    ax.barh(p - .16, models["ap_prueba"], height=.31, color=RED, label="Prueba")
    ax.set_yticks(p, models["modelo"])
    ax.set_xlim(0, .42)
    ax.set_xlabel("Average Precision de la clase operativa sin acceso")
    ax.set_title("Comparación bajo el mismo protocolo", loc="left")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=.6)
    ax.set_axisbelow(True)
    finish(fig, "comparacion_modelos.png")

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    top = imp.head(10).sort_values("mean_ap_drop")
    ax.barh(top["descripcion"], top["mean_ap_drop"], color=BLUE)
    ax.set_xlabel("Caída de AP al permutar la variable en validación")
    ax.set_title("Importancia predictiva, sin interpretación causal", loc="left")
    ax.grid(axis="x", alpha=.6)
    ax.set_axisbelow(True)
    finish(fig, "importancia_modelo.png")

    conf = results["test_metrics"][results["selected_model"]]["confusion"]
    matrix = np.array([[conf["tn"], conf["fp"]], [conf["fn"], conf["tp"]]])
    fig, ax = plt.subplots(figsize=(5.2, 4.7))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], ["Con acceso", "Sin acceso"])
    ax.set_yticks([0, 1], ["Con acceso", "Sin acceso"])
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Observado")
    ax.set_title("Matriz de confusión en prueba", loc="left")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{matrix[i, j]:,.0f}".replace(",", "."),
                    ha="center", va="center", color="white" if matrix[i, j] > 5000 else INK,
                    fontsize=13, fontweight="bold")
    finish(fig, "matriz_confusion.png")

    artifact = joblib.load(RESULTS / "modelo_sin_acceso.joblib")
    groups = group_ids(frame)
    _, _, test = split_three(frame[FEATURES], frame["SIN_ACCESO"], groups)
    observed = frame["SIN_ACCESO"].iloc[test].to_numpy()
    scores = artifact["pipeline"].predict_proba(frame.iloc[test][FEATURES])[:, 1]
    audits = {
        "pr_auc": average_precision_score(observed, scores),
        "roc_auc": roc_auc_score(observed, scores),
        "brier": brier_score_loss(observed, scores),
    }
    for name, value in audits.items():
        if not np.isclose(value, chosen[name], atol=1e-10, rtol=0):
            raise AssertionError(f"La curva recalculada no reproduce {name}")
    fpr, tpr, _ = roc_curve(observed, scores)
    precision, recall, _ = precision_recall_curve(observed, scores)
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5))
    axes[0].plot(fpr, tpr, color=BLUE, linewidth=2.1)
    axes[0].plot([0, 1], [0, 1], color=MUTED, linestyle="--", linewidth=1)
    axes[0].set(xlabel="Tasa de falsos positivos", ylabel="Sensibilidad",
                title=f"ROC · AUC {audits['roc_auc']:.3f}")
    axes[1].plot(recall, precision, color=RED, linewidth=2.1)
    axes[1].axhline(observed.mean(), color=MUTED, linestyle="--", linewidth=1,
                    label="Prevalencia")
    axes[1].set(xlabel="Sensibilidad", ylabel="Precisión",
                title=f"Precisión–recall · AP {audits['pr_auc']:.3f}")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(alpha=.55)
    fig.suptitle("Modelo seleccionado · conjunto de prueba", fontweight="bold", x=.06, ha="left")
    finish(fig, "curvas_modelo.png")

    cal = pd.read_csv(DATA / "calibracion.csv")
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.plot([0, .5], [0, .5], color=MUTED, linestyle="--", label="Calibración perfecta")
    ax.plot(cal["mean_predicted"], cal["observed"], "o-", color=BLUE,
            linewidth=2.1, label="Deciles en prueba")
    ax.set(xlabel="Probabilidad media predicha", ylabel="Frecuencia observada",
           title="Calibración interna")
    ax.set_xlim(0, .5)
    ax.set_ylim(0, .5)
    ax.grid(alpha=.6)
    ax.legend(frameon=False)
    finish(fig, "calibracion_modelo.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Carpeta de los CSV originales del CNPV 2018 Atlántico")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    configure_plot()
    results = json.loads((RESULTS / "resultados.json").read_text(encoding="utf-8"))
    quality = json.loads((RESULTS / "perfil_calidad.json").read_text(encoding="utf-8"))
    frame, source = load_data(args.data_dir)
    if source["source_sha256"] != results["source"]["source_sha256"]:
        raise RuntimeError("Los CSV no coinciden con los usados por el modelo auditado. "
                           "Reentrene y audite antes de mezclar resultados.")
    for key in ("people", "sick", "unlabeled", "labeled", "no_access",
                "house_match", "dwell_match", "label_breakdown"):
        if source[key] != results["source"][key]:
            raise AssertionError(f"Diferencia con la auditoría en {key}")
    if source["labeled"] != quality["n"]:
        raise AssertionError("El perfil de calidad no coincide con la cohorte")
    summary = make_eda(frame, source, quality)
    plot_eda(summary)
    make_model(results, frame)
    print(f"Agregados y figuras actualizados en {BOOK}")
    print(f"Personas analizadas: {summary['labeled']:,}; clase operativa sin acceso: {summary['no_access']:,}")


if __name__ == "__main__":
    main()
