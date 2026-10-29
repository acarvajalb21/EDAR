"""Convierte los JSON verificados en tablas CSV de lectura y revisión."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "salidas"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    archived = read(HERE.parent / "resultados" / "resultados.json")
    experiments = read(OUT / "experimentos.json")
    historical = read(OUT / "comparacion_historica.json")
    rows = []
    for name, detail in archived["models"].items():
        for partition, metric in (("validacion", detail["validation"]),
                                  ("prueba_historica", archived["test_metrics"][name])):
            rows.append({"protocolo": "original_archivado", "modelo": name,
                         "particion": partition, "ap": metric["pr_auc"],
                         "roc_auc": metric["roc_auc"], "brier": metric["brier"],
                         "cv_ap_media": detail["cv_pr_auc"], "tiempo_segundos": None})
    for detail in experiments["candidates"]:
        rows.append({"protocolo": "revision_2026_10", "modelo": detail["name"],
                     "particion": "validacion", "ap": detail["validation"]["ap"],
                     "roc_auc": detail["validation"]["roc_auc"],
                     "brier": detail["validation"]["brier"],
                     "cv_ap_media": detail["cv_mean_ap"],
                     "tiempo_segundos": detail["elapsed_seconds"]})
    expansion_path = OUT / "ampliacion.json"
    if expansion_path.is_file():
        expansion = read(expansion_path)
        for detail in expansion["candidates"]:
            rows.append({"protocolo": "ampliacion_2026_10", "modelo": detail["name"],
                         "particion": "validacion", "ap": detail["validation"]["ap"],
                         "roc_auc": detail["validation"]["roc_auc"],
                         "brier": detail["validation"]["brier"],
                         "cv_ap_media": detail["cv_mean_ap"],
                         "tiempo_segundos": detail["elapsed_seconds"]})
    pd.DataFrame(rows).to_csv(OUT / "comparacion_modelos.csv", index=False, encoding="utf-8-sig")
    subgroups = []
    for variable, categories in historical["subgroups_selected"].items():
        for code, metric in categories.items():
            subgroups.append({"variable": variable, "codigo": code,
                              "n": metric["n"], "positivos": metric["positives"],
                              "prevalencia": metric["prevalence"], "ap": metric["ap"],
                              "senalados": metric["flagged"],
                              "precision": metric["precision"], "sensibilidad": metric["recall"],
                              "sensibilidad_wilson_95_inf": metric["recall_wilson_95"][0],
                              "sensibilidad_wilson_95_sup": metric["recall_wilson_95"][1]})
    pd.DataFrame(subgroups).to_csv(OUT / "subgrupos_prueba_historica.csv",
                                   index=False, encoding="utf-8-sig")
    print("CSV generados:", OUT / "comparacion_modelos.csv",
          OUT / "subgrupos_prueba_historica.csv")


if __name__ == "__main__":
    main()
