"""Sensibilidad del modelo vigente por dificultad funcional y edad, en la prueba interna.

Repite el desglose descriptivo que la revisión de octubre hizo con la versión 1.
Uso: python -m ml_salud.experimento_contexto.brecha --data-dir RUTA_A_CSV
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from ml_salud.contexto import prepare_features_v2
from ml_salud.entrenar import group_ids, load_data, split_three
from ml_salud.experimentos_2026_10.ejecutar import wilson

BANDS = ("0-14", "15-59", "60+")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    args = parser.parse_args()
    df, _ = load_data(args.data_dir, with_context=True)
    x = prepare_features_v2(df)
    y = df["SIN_ACCESO"].to_numpy()
    _, _, test = split_three(x, y, group_ids(df))
    artifact = joblib.load(Path(__file__).parents[1] / "resultados" / "modelo_sin_acceso.joblib")
    score = artifact["pipeline"]["clasificador"].predict_proba(x.iloc[test])[:, 1]
    raw = df.iloc[test].reset_index(drop=True)
    age = raw["P_EDADR"].to_numpy()
    bands = np.select([age <= 3, age <= 12], ["0-14", "15-59"], default="60+")
    difficulty = raw["CONDICION_FISICA"].to_numpy()
    yy = y[test]
    pred = score >= artifact["threshold_no_access"]
    rows = []
    for band in BANDS:
        for code in (1, 2):
            mask = (bands == band) & (difficulty == code)
            positives = int(yy[mask].sum())
            hits = int((pred[mask] & (yy[mask] == 1)).sum())
            rows.append({"age_band": band, "difficulty_code": code, "n": int(mask.sum()),
                         "positives": positives, "true_positives": hits,
                         "recall": hits / positives if positives else None,
                         "recall_wilson_95": wilson(hits, positives)})
    weights = {band: float(((bands == band) & (yy == 1)).sum() / yy.sum()) for band in BANDS}
    standardized = {
        str(code): sum(weights[band] * next(row["recall"] for row in rows
                                            if row["age_band"] == band and row["difficulty_code"] == code)
                       for band in BANDS)
        for code in (1, 2)
    }
    # Con el mismo número de personas marcadas, la comparación con v1 no depende del umbral.
    old = joblib.load(Path(__file__).parents[1] / "resultados_v1" / "modelo_sin_acceso.joblib")
    old_pred = old["pipeline"]["clasificador"].predict_proba(x.iloc[test])[:, 1] >= old["threshold_no_access"]
    same = np.zeros(len(yy), dtype=bool)
    same[np.argsort(-score, kind="stable")[:int(old_pred.sum())]] = True
    comparison = {
        name: {"flagged": int(flags.sum()), "recall": float(flags[yy == 1].mean()),
               "precision": float(yy[flags].mean()),
               "recall_difficulty": float(flags[(yy == 1) & (difficulty == 1)].mean()),
               "recall_no_difficulty": float(flags[(yy == 1) & (difficulty == 2)].mean()),
               "recall_60_plus": float(flags[(yy == 1) & (bands == "60+")].mean())}
        for name, flags in (("v1_umbral_validado", old_pred), ("v2_mismas_personas_marcadas", same),
                            ("v2_umbral_validado", pred))
    }
    result = {
        "status": "descriptivo; prueba interna ya expuesta", "age_weights_among_positives": weights,
        "same_flagged_comparison": comparison,
        "rows": rows, "age_standardized_recall": standardized,
        "raw_recall": {str(code): float(pred[(yy == 1) & (difficulty == code)].mean()) for code in (1, 2)},
        "recall_60_plus": float(pred[(yy == 1) & (bands == "60+")].mean()),
        "recall_under_60": float(pred[(yy == 1) & (bands != "60+")].mean()),
    }
    output = Path(__file__).parent / "salidas" / "brecha.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("BRECHA", result["raw_recall"], result["age_standardized_recall"], flush=True)


if __name__ == "__main__":
    main()
