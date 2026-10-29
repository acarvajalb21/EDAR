"""Sensibilidad exploratoria: municipios ausentes del ajuste, solo entrenamiento histórico."""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone

from ml_salud.entrenar import group_ids, load_data, split_three
from ml_salud.esquema import CATEGORICAL, NUMERIC, prepare_features
from ml_salud.experimentos_2026_10.ejecutar import metrics_rank, model_pipeline


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--output", type=Path, default=Path(__file__).parent / "salidas" / "territorio.json")
    args = p.parse_args()
    started = time.perf_counter()
    df, _ = load_data(args.data_dir)
    x = prepare_features(df)
    y = df.SIN_ACCESO.to_numpy()
    groups = group_ids(df)
    train, _, _ = split_three(x, y, groups)
    x = x.iloc[train].drop(columns="U_MPIO")
    yy = y[train]
    cities = df.U_MPIO.iloc[train].to_numpy()
    top = df.U_MPIO.iloc[train].value_counts().head(3).index.tolist()
    model = model_pipeline([c for c in CATEGORICAL if c != "U_MPIO"], NUMERIC)
    results = []
    for city in top:
        hold = cities == city
        assert np.all(cities[~hold] != city)
        fitted = clone(model).fit(x.iloc[np.flatnonzero(~hold)], yy[~hold])
        score = fitted.predict_proba(x.iloc[np.flatnonzero(hold)])[:, 1]
        results.append({"municipio_codigo": int(city), "train_n": int((~hold).sum()),
                        "excluded_feature": "U_MPIO", "held_out": metrics_rank(yy[hold], score),
                        "prevalence_baseline_ap": float(yy[hold].mean())})
        print("MUNICIPIO", city, results[-1]["held_out"], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "status": "sensibilidad territorial exploratoria dentro de entrenamiento histórico",
        "selection": "tres municipios con mayor n en entrenamiento; no se usó validación ni prueba histórica",
        "model": "boosting original, sin U_MPIO, sin retuning",
        "seed": 42,
        "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                     "numpy": np.__version__, "scikit_learn": sklearn.__version__},
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
