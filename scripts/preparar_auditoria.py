"""Actualiza el resumen publicable de la auditoría de ML sin incluir microdatos."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT
AUDIT = ROOT / "ml_salud" / "experimentos_2026_10" / "salidas"
ORIGINAL = ROOT / "ml_salud" / "resultados" / "resultados.json"
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


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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
    shutil.copyfile(AUDIT / "brecha_dificultad.png", figures_dir / "brecha_dificultad_2026.png")
    print("Auditoría 2026 incorporada al Bookdown, sin cambiar el modelo seleccionado")


if __name__ == "__main__":
    main()
