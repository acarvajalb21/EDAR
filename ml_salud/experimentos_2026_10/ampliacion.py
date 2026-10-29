"""Segunda ronda fija sobre entrenamiento agrupado; no usa prueba histórica."""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from ml_salud.entrenar import SEED, encoded_preprocessor, group_ids, load_data, split_three
from ml_salud.esquema import FEATURES, prepare_features
from ml_salud.experimentos_2026_10.ejecutar import grouped_delta_bootstrap, metrics_rank, model_pipeline
from ml_salud.experimentos_2026_10.preprocesamiento import CandidatePredictor, FeatureBuilder, WeightedEnsemble


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "salidas")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    df, source = load_data(args.data_dir)
    x = prepare_features(df)
    y = df.SIN_ACCESO.to_numpy()
    groups = group_ids(df)
    train, val, _ = split_three(x, y, groups)
    xt, xv, yt, yv = x.iloc[train], x.iloc[val], y[train], y[val]
    folds = list(StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + 1)
                 .split(xt, yt, groups[train]))
    old_artifact = joblib.load(Path(__file__).parents[1] / "resultados" / "modelo_sin_acceso.joblib")
    old_score = old_artifact["pipeline"]["clasificador"].predict_proba(xv)[:, 1]
    baseline_val = metrics_rank(yv, old_score)
    models = {
        "l2_1": {"model__l2_regularization": 1.0},
        "features_07": {"model__max_features": 0.7},
        "aprendizaje_lento": {"model__learning_rate": 0.025, "model__max_iter": 500},
    }
    records = []
    fitted_models = {}
    scores_val = {}
    for name, change in models.items():
        t0 = time.perf_counter()
        template = model_pipeline(
            [c for c in FEATURES if c not in ("P_EDADR", "H_NRO_CUARTOS", "H_NRO_DORMIT", "HA_TOT_PER")],
            ["P_EDADR", "H_NRO_CUARTOS", "H_NRO_DORMIT", "HA_TOT_PER"],
        ).set_params(**change)
        fold_ap = []
        for fit_idx, hold_idx in folds:
            m = clone(template).fit(xt.iloc[fit_idx], yt[fit_idx])
            score = m.predict_proba(xt.iloc[hold_idx])[:, 1]
            fold_ap.append(float(average_precision_score(yt[hold_idx], score)))
        fit = clone(template).fit(xt, yt)
        score_val = fit.predict_proba(xv)[:, 1]
        record = {"name": name, "parameters_changed": change, "fold_ap": fold_ap,
                  "cv_mean_ap": float(np.mean(fold_ap)), "validation": metrics_rank(yv, score_val),
                  "elapsed_seconds": round(time.perf_counter() - t0, 3)}
        records.append(record)
        fitted_models[name], scores_val[name] = fit, score_val
        print("AMPLIACIÓN", name, record["cv_mean_ap"], record["validation"], flush=True)

    # Peso fijado en protocolo. Cada pliegue ajusta ambos miembros solo con su entrenamiento.
    t0 = time.perf_counter()
    hist = old_artifact["pipeline"]["clasificador"]
    logistic = Pipeline([
        ("prep", encoded_preprocessor(age_as_category=True)),
        ("model", LogisticRegression(C=0.05, class_weight=None,
                                      max_iter=1000, solver="lbfgs")),
    ])
    fold_ap = []
    for fit_idx, hold_idx in folds:
        h = clone(hist).fit(xt.iloc[fit_idx], yt[fit_idx])
        l = clone(logistic).fit(xt.iloc[fit_idx], yt[fit_idx])
        score = (0.75 * h.predict_proba(xt.iloc[hold_idx])[:, 1] +
                 0.25 * l.predict_proba(xt.iloc[hold_idx])[:, 1])
        fold_ap.append(float(average_precision_score(yt[hold_idx], score)))
    h = clone(hist).fit(xt, yt)
    l = clone(logistic).fit(xt, yt)
    blend = WeightedEnsemble(h, l, 0.75)
    blend_val = blend.predict_proba(xv)[:, 1]
    records.append({"name": "mezcla_fija_75_25", "parameters_changed":
                    {"boosting_weight": 0.75, "logistic_weight": 0.25,
                     "logistic_C": 0.05},
                    "fold_ap": fold_ap, "cv_mean_ap": float(np.mean(fold_ap)),
                    "validation": metrics_rank(yv, blend_val),
                    "elapsed_seconds": round(time.perf_counter() - t0, 3)})
    fitted_models["mezcla_fija_75_25"] = blend
    scores_val["mezcla_fija_75_25"] = blend_val
    print("AMPLIACIÓN", records[-1]["name"], records[-1]["cv_mean_ap"],
          records[-1]["validation"], flush=True)

    best = sorted(records, key=lambda r: (-r["cv_mean_ap"], r["name"]))[0]
    paired = grouped_delta_bootstrap(yv, scores_val[best["name"]], old_score, groups[val])
    pass_rule = (paired["delta_ap"] >= 0.010 and paired["delta_ap_interval_95"][0] > 0 and
                 best["validation"]["brier"] - baseline_val["brier"] <= 0.002)
    result = {"status": "ampliación exploratoria; prueba histórica no consultada",
              "baseline_validation": baseline_val, "candidates": records,
              "best_by_cv": best["name"], "paired_validation": paired,
              "promotion_rule_passed": pass_rule,
              "selected": best["name"] if pass_rule else "referencia",
              "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                           "numpy": np.__version__, "scikit_learn": sklearn.__version__},
              "seed": SEED, "total_elapsed_seconds": round(time.perf_counter() - started, 3)}
    (args.output_dir / "ampliacion.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if pass_rule:
        raw_pipeline = Pipeline([("normalizar_entrada", FeatureBuilder()),
                                 ("clasificador", fitted_models[best["name"]])])
        predictor = CandidatePredictor(raw_pipeline)
        sample = df.iloc[val[:100]][FEATURES]
        np.testing.assert_allclose(predictor.predict_proba(sample)[:, 1],
                                   scores_val[best["name"]][:100], rtol=0, atol=1e-12)
        joblib.dump({"predictor": predictor, "features": FEATURES,
                     "target": "SIN_ACCESO=1", "source_sha256": source["source_sha256"],
                     "protocol": "ampliacion_2026_10", "versions": result["versions"]},
                    args.output_dir / "candidato_ampliacion.joblib", compress=3)
    print("DECISIÓN AMPLIACIÓN", result["selected"], paired, flush=True)


if __name__ == "__main__":
    main()
