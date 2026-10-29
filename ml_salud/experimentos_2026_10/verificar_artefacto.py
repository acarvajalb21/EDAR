"""Comprueba el artefacto portable contra la referencia en datos reales."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import average_precision_score

from ml_salud.entrenar import group_ids, load_data, split_three
from ml_salud.esquema import FEATURES, prepare_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "salidas" / "verificacion_artefacto.json")
    args = parser.parse_args()
    df, source = load_data(args.data_dir)
    x = prepare_features(df)
    y = df.SIN_ACCESO.to_numpy()
    _, _, test = split_three(x, y, group_ids(df))
    original = joblib.load(Path(__file__).parents[1] / "resultados" / "modelo_sin_acceso.joblib")
    candidate = joblib.load(Path(__file__).parent / "salidas" / "candidato_separado.joblib")
    old_score = original["pipeline"]["clasificador"].predict_proba(x.iloc[test])[:, 1]
    new_score = candidate["predictor"].predict_proba(df.iloc[test][FEATURES])[:, 1]
    gap = float(np.max(np.abs(old_score - new_score)))
    assert gap < 1e-12, f"Las probabilidades no coinciden: {gap}"
    ap = float(average_precision_score(y[test], new_score))
    result = {"n": len(test), "max_abs_probability_delta": gap,
              "average_precision": ap, "source_sha256_matches_artifact":
              source["source_sha256"] == candidate["source_sha256"]}
    assert result["source_sha256_matches_artifact"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("VERIFICADO", result, flush=True)


if __name__ == "__main__":
    main()
