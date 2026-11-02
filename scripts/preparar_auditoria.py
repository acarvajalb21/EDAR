"""Actualiza el resumen publicable de la auditoría de ML sin incluir microdatos."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT
AUDIT = ROOT / "ml_salud" / "experimentos_2026_10" / "salidas"
ORIGINAL = ROOT / "ml_salud" / "resultados_v1" / "resultados.json"
LABELS = {
    "referencia": "Boosting original reproducido",
    "faltantes_distintos": "Distinguir blancos y códigos sin respuesta",
    "personas_por_dormitorio": "Personas por dormitorio",
    "faltantes_y_densidad": "Faltantes y personas por dormitorio",
    "edad_categorica_y_densidad": "Edad categórica y personas por dormitorio",
    "boost_mas_regularizado": "Boosting más regularizado",
    "l2_1": "Regularización L2 = 1",
    "features_07": "Fracción de variables = 0,7",
    "aprendizaje_lento": "Aprendizaje más lento",
    "mezcla_fija_75_25": "Mezcla fija: boosting y logística",
}

# Mismos tokens que scripts/preparar_resumen.py: añil y ocre comparan grupos.
ANIL = "#5B6FB5"
OCRE = "#A86C00"
INK = "#10293B"
MUTED = "#54697A"
GRID = "#D9E1E7"
HOJA = "#F7F9FB"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def entero(valor: int) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def figura_brecha(breach: dict, destino: Path) -> None:
    """Redibuja la figura de la auditoría con la paleta del libro; el registro original no cambia."""
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Atkinson Hyperlegible Next", "DejaVu Sans"], "font.size": 10,
        "axes.labelcolor": MUTED, "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "normal",
        "figure.facecolor": HOJA, "axes.facecolor": HOJA, "savefig.facecolor": HOJA, "grid.color": GRID,
    })
    bandas = ["0-14", "15-59", "60+"]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    for codigo, desplazamiento, nombre, color in ((1, -.14, "Con dificultad", OCRE), (2, .14, "Sin dificultad", ANIL)):
        filas = [next(r for r in breach["rows"] if r["age_band"] == banda and r["difficulty_code"] == codigo) for banda in bandas]
        valores = np.array([r["recall"] for r in filas])
        abajo = valores - np.array([r["recall_wilson_95"][0] for r in filas])
        arriba = np.array([r["recall_wilson_95"][1] for r in filas]) - valores
        ax.errorbar(np.arange(3) + desplazamiento, valores, yerr=[abajo, arriba], fmt="o-", capsize=4,
                    color=color, linewidth=2, markersize=7, label=nombre)
        # Las etiquetas van al lado del punto, hacia donde no pasa la línea.
        for i, r in enumerate(filas):
            ax.annotate(f"{entero(r['true_positives'])}/{entero(r['positives'])}", (i + desplazamiento, valores[i]),
                        xytext=(-10, 0) if codigo == 1 else ((10, -10), (10, 10), (10, 0))[i], textcoords="offset points", ha="right" if codigo == 1 else "left",
                        va="center", fontsize=8.5, color=MUTED)
    ax.set_xticks(range(3), ["0 a 14", "15 a 59", "60 o más"])
    ax.set_xlim(-.65, 2.65)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
    ax.set_xlabel("Edad en años")
    ax.set_ylabel("Sensibilidad entre quienes están fuera de la ruta")
    ax.set_title("Sensibilidad por edad y dificultad funcional declarada", loc="left")
    ax.grid(axis="y", alpha=.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    fig.tight_layout(pad=1.8)
    fig.savefig(destino, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    original = read(ORIGINAL)
    audit = read(AUDIT / "auditoria.json")
    first = read(AUDIT / "experimentos.json")
    second = read(AUDIT / "ampliacion.json")
    breach = read(AUDIT / "brecha_dificultad.json")
    territory = read(AUDIT / "territorio.json")
    integrity = read(AUDIT / "verificacion_artefacto.json")
    if audit["source_sha256"] != original["source"]["source_sha256"]:
        raise RuntimeError("La auditoría no corresponde a los CSV del Bookdown")
    if integrity["max_abs_probability_delta"] != 0:
        raise RuntimeError("El artefacto no reproduce el modelo original")
    if first["decision"]["selected"] != "referencia" or second["selected"] != "referencia":
        raise RuntimeError("La selección cambió; actualice primero el modelo y el libro de forma integral")

    rows = []
    for phase, candidates in (("Primera ronda", first["candidates"]),
                              ("Ampliación", second["candidates"])):
        for row in candidates:
            rows.append({"fase": phase, "ensayo": LABELS[row["name"]],
                         "ap_cv": row["cv_mean_ap"], "ap_validacion": row["validation"]["ap"],
                         "brier_validacion": row["validation"]["brier"]})
    data_dir = BOOK / "data"
    figures_dir = BOOK / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(data_dir / "auditoria_modelo_2026.csv", index=False,
                              encoding="utf-8-sig")

    best_first = first["decision"]["paired_validation"]
    best_second = second["paired_validation"]
    pd.DataFrame([{
        "ap_original_validacion": first["candidates"][0]["validation"]["ap"],
        "ap_original_prueba": original["test_metrics"]["hist_gradient_boosting"]["pr_auc"],
        "ap_maxima_validacion_ampliacion": max(r["validation"]["ap"] for r in second["candidates"]),
        "delta_primera": best_first["delta_ap"],
        "delta_primera_inf": best_first["delta_ap_interval_95"][0],
        "delta_primera_sup": best_first["delta_ap_interval_95"][1],
        "delta_ampliacion": best_second["delta_ap"],
        "delta_ampliacion_inf": best_second["delta_ap_interval_95"][0],
        "delta_ampliacion_sup": best_second["delta_ap_interval_95"][1],
        "recall_dificultad": breach["raw_recall"]["1"],
        "recall_sin_dificultad": breach["raw_recall"]["2"],
        "recall_ajustada_dificultad": breach["age_standardized_recall"]["1"],
        "recall_ajustada_sin_dificultad": breach["age_standardized_recall"]["2"],
    }]).to_csv(data_dir / "auditoria_resumen_2026.csv", index=False,
               encoding="utf-8-sig")

    municipality_names = {1: "Barranquilla", 758: "Soledad", 433: "Malambo"}
    pd.DataFrame([{
        "municipio": municipality_names[item["municipio_codigo"]],
        "n": item["held_out"]["n"], "positivos": item["held_out"]["positives"],
        "prevalencia": item["prevalence_baseline_ap"],
        "ap": item["held_out"]["ap"],
        "roc_auc": item["held_out"]["roc_auc"],
    } for item in territory["results"]]).to_csv(
        data_dir / "auditoria_territorio_2026.csv", index=False, encoding="utf-8-sig")
    figura_brecha(breach, figures_dir / "brecha_dificultad_2026.png")
    pd.DataFrame([{
        "edad": row["age_band"], "dificultad": "Con dificultad" if row["difficulty_code"] == 1 else "Sin dificultad",
        "positivos": row["positives"], "detectados": row["true_positives"], "sensibilidad": row["recall"],
        "inferior": row["recall_wilson_95"][0], "superior": row["recall_wilson_95"][1],
    } for row in breach["rows"]]).to_csv(data_dir / "auditoria_brecha_2026.csv", index=False, encoding="utf-8-sig")
    print("Auditoría 2026 incorporada al Bookdown, sin cambiar el modelo seleccionado")


if __name__ == "__main__":
    main()
