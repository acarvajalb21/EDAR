"""Análisis de sensibilidad en validación; no consulta la prueba.

Ejecutar desde la raíz: python -m ml_salud.auditoria_sensibilidad --data-dir RUTA
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from ml_salud.entrenar import SEED, group_ids, load_data, metricas, split_three
from ml_salud.esquema import FULL_FEATURES, NUMERIC, prepare_features

CATEGORICAL = [column for column in FULL_FEATURES if column not in NUMERIC]


def logistic_age_categorical():
    cats = CATEGORICAL + ["P_EDADR"]
    nums = [column for column in NUMERIC if column != "P_EDADR"]
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=50), cats),
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]), nums),
    ])


def boosting_pipeline(cats, nums, iterations, early_stopping):
    prep = ColumnTransformer([
        ("cat", OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1,
        ), cats),
        ("num", SimpleImputer(strategy="median", add_indicator=True), nums),
    ], sparse_threshold=0)
    model = HistGradientBoostingClassifier(
        categorical_features=list(range(len(cats))),
        learning_rate=0.04, max_leaf_nodes=31, min_samples_leaf=30,
        max_iter=iterations, early_stopping=early_stopping,
        random_state=SEED,
    )
    return Pipeline([("prep", prep), ("model", model)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).parent / "resultados" / "sensibilidad_validacion.json",
    )
    args = parser.parse_args()
    df, _ = load_data(args.data_dir)
    x = prepare_features(df, FULL_FEATURES)
    y = df["SIN_ACCESO"].to_numpy()
    groups = group_ids(df)
    train, val, _ = split_three(x, y, groups)
    xt, xv, yt, yv = x.iloc[train], x.iloc[val], y[train], y[val]
    gt = groups[train]
    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + 1)
    logistic = GridSearchCV(
        Pipeline([
            ("prep", logistic_age_categorical()),
            ("model", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]),
        {"model__C": [0.05, 0.5, 5.0],
         "model__class_weight": [None, "balanced"]},
        scoring="average_precision", cv=cv.split(xt, yt, gt), n_jobs=1,
        error_score="raise",
    ).fit(xt, yt)
    result = {
        "logistica_edad_categorica": {
            "cv_pr_auc": float(logistic.best_score_),
            "params": logistic.best_params_,
            "validacion": metricas(
                yv, logistic.best_estimator_.predict_proba(xv)[:, 1]
            ),
        }
    }
    print("LOGISTICA", result["logistica_edad_categorica"], flush=True)
    variants = [
        ("boost_180_original", [], 180, True),
        ("boost_320_sin_parada", [], 320, False),
        ("boost_320_sin_trabajo_asistencia", ["P_TRABAJO", "PA_ASISTENCIA"], 320, False),
        ("boost_320_sin_municipio", ["U_MPIO"], 320, False),
    ]
    for name, removed, iterations, early_stopping in variants:
        cats = [column for column in CATEGORICAL if column not in removed]
        nums = [column for column in NUMERIC if column not in removed]
        pipe = boosting_pipeline(cats, nums, iterations, early_stopping)
        pipe.fit(xt.drop(columns=removed), yt)
        result[name] = {
            "excluded": removed,
            "n_iter": int(pipe["model"].n_iter_),
            "validacion": metricas(
                yv, pipe.predict_proba(xv.drop(columns=removed))[:, 1]
            ),
        }
        print(name, result[name], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SALIDA", args.output, flush=True)


if __name__ == "__main__":
    main()
