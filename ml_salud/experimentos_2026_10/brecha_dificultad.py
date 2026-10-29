"""Desglose descriptivo de sensibilidad por dificultad y edad en prueba histórica."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_salud.entrenar import group_ids, load_data, split_three
from ml_salud.esquema import prepare_features
from ml_salud.experimentos_2026_10.ejecutar import wilson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "salidas" / "brecha_dificultad.json")
    args = parser.parse_args()
    df, _ = load_data(args.data_dir)
    x = prepare_features(df)
    y = df.SIN_ACCESO.to_numpy()
    _, _, test = split_three(x, y, group_ids(df))
    artifact = joblib.load(Path(__file__).parents[1] / "resultados" / "modelo_sin_acceso.joblib")
    score = artifact["pipeline"]["clasificador"].predict_proba(x.iloc[test])[:, 1]
    raw = df.iloc[test].reset_index(drop=True)
    age = raw.P_EDADR.to_numpy()
    bands = np.select([age <= 3, age <= 12], ["0-14", "15-59"], default="60+")
    yy = y[test]
    pred = score >= artifact["threshold_no_access"]
    difficulty = raw.CONDICION_FISICA.to_numpy()
    rows = []
    for band in ("0-14", "15-59", "60+"):
        for code in (1, 2):
            mask = (bands == band) & (difficulty == code)
            positive = int(np.sum(yy[mask]))
            tp = int(np.sum(pred[mask] & (yy[mask] == 1)))
            rows.append({"age_band": band, "difficulty_code": code, "n": int(mask.sum()),
                         "positives": positive, "true_positives": tp,
                         "recall": tp / positive if positive else None,
                         "recall_wilson_95": wilson(tp, positive),
                         "flagged": int(np.sum(pred[mask])),
                         "mean_score_positives": float(np.mean(score[mask & (yy == 1)])) if positive else None})
    weights = {band: float(np.sum((bands == band) & (yy == 1)) / yy.sum())
               for band in ("0-14", "15-59", "60+")}
    standardized = {str(code): sum(weights[band] * next(row["recall"] for row in rows
                                    if row["age_band"] == band and row["difficulty_code"] == code)
                                for band in weights) for code in (1, 2)}
    result = {"status": "descriptivo; prueba histórica ya expuesta", "age_weights_among_positives": weights,
              "rows": rows, "age_standardized_recall": standardized,
              "raw_recall": {str(code): float(np.mean(pred[(yy == 1) & (difficulty == code)]))
                             for code in (1, 2)}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("BRECHA", result["raw_recall"], result["age_standardized_recall"], flush=True)


if __name__ == "__main__":
    main()
