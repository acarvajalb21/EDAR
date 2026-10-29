"""Auditoría y candidatos; ejecutar desde la raíz de DATAVIZ.

python -m ml_salud.experimentos_2026_10.ejecutar --data-dir RUTA_A_CSV
No escribe en ml_salud/resultados, Bookdown ni Dash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from scipy.special import logit
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from ml_salud.entrenar import (
    PERSON_KEY, SEED, group_ids, load_data,
    metricas, optimize_threshold, split_three,
)
from ml_salud.esquema import (
    CATEGORICAL, EXCLUDED_TEMPORAL, FEATURES, LEAKAGE_COLUMNS, NUMERIC, prepare_features,
)
from ml_salud.experimentos_2026_10.preprocesamiento import (
    CandidatePredictor, FeatureBuilder, feature_frame,
)

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "resultados"
BOOTSTRAPS = 250


def as_json(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(type(value).__name__)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=as_json), encoding="utf-8")


def model_pipeline(cats: list[str], nums: list[str], *, leaves=31, iterations=320):
    prep = ColumnTransformer([
        ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), cats),
        ("num", SimpleImputer(strategy="median", add_indicator=True), nums),
    ], sparse_threshold=0)
    model = HistGradientBoostingClassifier(
        categorical_features=list(range(len(cats))),
        learning_rate=0.04, max_iter=iterations, max_leaf_nodes=leaves,
        min_samples_leaf=30, early_stopping=False, random_state=SEED,
    )
    return Pipeline([("prep", prep), ("model", model)])


def metrics_rank(y, score):
    return {"n": len(y), "positives": int(np.sum(y)),
            "ap": float(average_precision_score(y, score)),
            "roc_auc": float(roc_auc_score(y, score)),
            "brier": float(brier_score_loss(y, score))}


def topk(y, score, fractions=(0.05, 0.10, 0.20)):
    # Orden estable: en empate prevalece la posición original de la partición.
    order = np.argsort(-np.asarray(score), kind="stable")
    prevalence = float(np.mean(y))
    total = int(np.sum(y))
    out = {}
    for fraction in fractions:
        k = int(np.ceil(len(y) * fraction))
        positives = int(np.sum(y[order[:k]]))
        precision = positives / k
        out[f"{int(fraction * 100)}pct"] = {
            "reviewed": k, "positives_found": positives,
            "precision": precision, "recall": positives / total,
            "lift": precision / prevalence,
        }
    return out


def wilson(successes, n, z=1.959963984540054):
    if n == 0:
        return None
    p = successes / n
    den = 1 + z * z / n
    middle = (p + z * z / (2 * n)) / den
    radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(middle - radius), float(middle + radius)]


def subgroup_report(y, score, threshold, raw):
    out = {}
    for col in ("CONDICION_FISICA", "P_SEXO", "P_EDADR", "U_MPIO"):
        by = {}
        for code, positions in raw.groupby(col, dropna=False).indices.items():
            yy = y[positions]
            if len(positions) < 50 or yy.sum() < 10:
                continue
            ss = score[positions]
            pred = ss >= threshold
            tp = int(np.sum(pred & (yy == 1)))
            positive = int(np.sum(yy))
            flagged = int(np.sum(pred))
            by[str(code)] = {
                "n": len(positions), "positives": positive,
                "prevalence": positive / len(positions),
                "ap": float(average_precision_score(yy, ss)),
                "recall": tp / positive, "recall_wilson_95": wilson(tp, positive),
                "precision": tp / flagged if flagged else None,
                "flagged": flagged,
            }
        out[col] = by
    return out


def grouped_delta_bootstrap(y, a, b, groups, reps=BOOTSTRAPS):
    _, inverse = np.unique(groups, return_inverse=True)
    order = np.argsort(inverse)
    members = np.split(order, np.cumsum(np.bincount(inverse))[:-1])
    rng = np.random.default_rng(44)
    deltas = []
    for _ in range(reps):
        choice = rng.integers(0, len(members), len(members))
        idx = np.concatenate([members[j] for j in choice])
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        deltas.append(average_precision_score(yy, a[idx]) - average_precision_score(yy, b[idx]))
    return {"method": "paired dwelling bootstrap percentile",
            "repetitions": len(deltas), "delta_ap": float(average_precision_score(y, a) - average_precision_score(y, b)),
            "delta_ap_interval_95": [float(v) for v in np.quantile(deltas, [0.025, 0.975])]}


def calibration_bins(y, score, n_bins=10):
    frame = pd.DataFrame({"y": y, "score": score})
    frame["bin"] = pd.qcut(frame.score, n_bins, duplicates="drop")
    return [{"n": len(part), "mean_predicted": float(part.score.mean()),
             "observed": float(part.y.mean())}
            for _, part in frame.groupby("bin", observed=True)]


def figures(y, old, new, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].axhline(float(np.mean(y)), color="gray", ls="--", label="Prevalencia")
    axes[1].plot([0, 1], [0, 1], color="gray", ls="--")
    curves = (("Original", old),) if np.array_equal(old, new) else (("Original", old), ("Candidato", new))
    for label, score in curves:
        p, r, _ = precision_recall_curve(y, score)
        axes[0].plot(r, p, label=f"{label} AP={average_precision_score(y, score):.3f}")
        bins = calibration_bins(y, score)
        axes[1].plot([v["mean_predicted"] for v in bins],
                     [v["observed"] for v in bins], "o-", label=label)
    axes[0].set(xlabel="Sensibilidad", ylabel="Precisión", title="Precisión–recall")
    axes[1].set(xlabel="Probabilidad predicha", ylabel="Frecuencia observada", title="Calibración")
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def audit(df, source, groups, train, val, test, original):
    archived = json.loads((ORIGINAL / "resultados.json").read_text(encoding="utf-8"))
    keys = {"train": train, "validation": val, "test": test}
    split = {name: {"n": len(idx), "dwellings": len(set(groups[idx])),
                    "no_access": int(df.SIN_ACCESO.iloc[idx].sum())}
             for name, idx in keys.items()}
    stored_split = archived["split"]
    assert source == archived["source"], "Fuente o cohorte discrepa del resultado archivado"
    assert all(split[n][k] == stored_split[n][k] for n in keys for k in split[n]), "Partición discrepa"
    assert not set(groups[train]) & set(groups[val])
    assert not set(groups[train]) & set(groups[test])
    assert not set(groups[val]) & set(groups[test])
    assert not df.duplicated(PERSON_KEY).any()
    assert not set(FEATURES) & LEAKAGE_COLUMNS
    assert not set(FEATURES) & set(EXCLUDED_TEMPORAL)
    assert original["features"] == FEATURES
    schema_hash = hashlib.sha256((HERE.parent / "esquema.py").read_bytes()).hexdigest()
    assert original["schema_sha256"] == schema_hash
    assert source["labeled"] == 136034 and source["no_access"] == 28650
    x = prepare_features(df)
    original_est = original["pipeline"]["clasificador"]
    fitted_imputer = original_est["prep"].named_transformers_["num"]
    medians_train = np.nanmedian(x.iloc[train][NUMERIC].to_numpy(float), axis=0)
    assert np.allclose(fitted_imputer.statistics_[:len(NUMERIC)], medians_train, equal_nan=True)
    distinctions = {col: {"blank": int(df[col].isna().sum()),
                          "explicit_sentinel": int(df[col].isin(values).sum())}
                    for col, values in SENTINELS.items() if col in FEATURES}
    return {"source_matches_archive": True, "group_overlap": 0,
            "person_duplicates": 0, "split": split, "predictors": FEATURES,
            "source_sha256": source["source_sha256"],
            "schema_sha256_matches_artifact": True,
            "numeric_train_medians_match_artifact": True,
            "missing_code_counts": distinctions,
            "archived_versions": archived["versions"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=HERE / "salidas")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    df, source = load_data(args.data_dir)
    y = df.SIN_ACCESO.to_numpy()
    groups = group_ids(df)
    x_base, _, _ = feature_frame(df)
    train, val, test = split_three(x_base, y, groups)
    original = joblib.load(ORIGINAL / "modelo_sin_acceso.joblib")
    audit_result = audit(df, source, groups, train, val, test, original)
    old = original["pipeline"]["clasificador"]
    old_val = old.predict_proba(x_base.iloc[val])[:, 1]
    archived = json.loads((ORIGINAL / "resultados.json").read_text(encoding="utf-8"))
    archived_val = archived["models"]["hist_gradient_boosting"]["validation"]
    assert abs(average_precision_score(y[val], old_val) - archived_val["pr_auc"]) < 1e-12
    assert abs(brier_score_loss(y[val], old_val) - archived_val["brier"]) < 1e-12
    audit_result["original_artifact_validation"] = metrics_rank(y[val], old_val)
    write_json(out / "auditoria.json", audit_result)
    print("AUDITORÍA OK", audit_result["split"], flush=True)

    # Reajuste de referencia: un solo ajuste con los parámetros ya seleccionados.
    baseline = clone(old).fit(x_base.iloc[train], y[train])
    ref_val = baseline.predict_proba(x_base.iloc[val])[:, 1]
    max_abs = float(np.max(np.abs(ref_val - old_val)))
    if max_abs > 1e-10:
        raise AssertionError(f"El reajuste original no reproduce el artefacto: {max_abs}")
    audit_result["reference_refit_max_abs_score_delta_validation"] = max_abs
    write_json(out / "auditoria.json", audit_result)
    print("REFERENCIA REAJUSTADA", metrics_rank(y[val], ref_val), flush=True)

    specs = [
        {"name": "referencia", "distinct_missing": False, "density": False,
         "age_category": False, "leaves": 31, "iterations": 320},
        {"name": "faltantes_distintos", "distinct_missing": True, "density": False,
         "age_category": False, "leaves": 31, "iterations": 320},
        {"name": "personas_por_dormitorio", "distinct_missing": False, "density": True,
         "age_category": False, "leaves": 31, "iterations": 320},
        {"name": "faltantes_y_densidad", "distinct_missing": True, "density": True,
         "age_category": False, "leaves": 31, "iterations": 320},
        {"name": "edad_categorica_y_densidad", "distinct_missing": False, "density": True,
         "age_category": True, "leaves": 31, "iterations": 320},
        {"name": "boost_mas_regularizado", "distinct_missing": False, "density": False,
         "age_category": False, "leaves": 15, "iterations": 240},
    ]
    fold_splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + 1)
    folds = list(fold_splitter.split(x_base.iloc[train], y[train], groups[train]))
    results = []
    fitted = {}
    val_scores = {}
    oof_scores = {}
    for spec in specs:
        name = spec["name"]
        t0 = time.perf_counter()
        x, cats, nums = feature_frame(df, distinct_missing=spec["distinct_missing"],
                                      density=spec["density"], age_category=spec["age_category"])
        xt, xv = x.iloc[train], x.iloc[val]
        yt, yv = y[train], y[val]
        pipe = model_pipeline(cats, nums, leaves=spec["leaves"], iterations=spec["iterations"])
        oof = np.full(len(train), np.nan)
        fold_ap = []
        for fit_idx, hold_idx in folds:
            m = clone(pipe).fit(xt.iloc[fit_idx], yt[fit_idx])
            s = m.predict_proba(xt.iloc[hold_idx])[:, 1]
            oof[hold_idx] = s
            fold_ap.append(float(average_precision_score(yt[hold_idx], s)))
        assert np.isfinite(oof).all()
        if name == "referencia":
            model = baseline
            score = ref_val
        else:
            model = clone(pipe).fit(xt, yt)
            score = model.predict_proba(xv)[:, 1]
        record = {"name": name, "spec": spec, "fold_ap": fold_ap,
                  "cv_mean_ap": float(np.mean(fold_ap)),
                  "cv_sd_ap": float(np.std(fold_ap, ddof=1)),
                  "validation": metrics_rank(yv, score),
                  "elapsed_seconds": round(time.perf_counter() - t0, 3)}
        results.append(record)
        fitted[name], val_scores[name], oof_scores[name] = model, score, oof
        write_json(out / "experimentos.json", {"candidates": results, "complete": False})
        print("CANDIDATO", name, record["cv_mean_ap"], record["validation"], flush=True)

    # CV decide; validación corrobora. Se compara siempre con la misma referencia.
    ranked = sorted(results[1:], key=lambda r: (-r["cv_mean_ap"], r["name"]))
    challenger = ranked[0]["name"]
    paired_val = grouped_delta_bootstrap(y[val], val_scores[challenger], old_val, groups[val])
    ref_brier = results[0]["validation"]["brier"]
    candidate_brier = next(r for r in results if r["name"] == challenger)["validation"]["brier"]
    promote = (paired_val["delta_ap"] >= 0.010 and
               paired_val["delta_ap_interval_95"][0] > 0 and
               candidate_brier - ref_brier <= 0.002)
    selected = challenger if promote else "referencia"
    # Calibración de Platt con scores fuera de pliegue, sin usar validación al ajustar.
    raw_oof = oof_scores[selected]
    calibrator = LogisticRegression(solver="lbfgs", random_state=SEED).fit(
        logit(np.clip(raw_oof, 1e-6, 1 - 1e-6)).reshape(-1, 1), y[train]
    )
    selected_val = val_scores[selected]
    calibrated_val = calibrator.predict_proba(
        logit(np.clip(selected_val, 1e-6, 1 - 1e-6)).reshape(-1, 1)
    )[:, 1]
    calibrate = (brier_score_loss(y[val], calibrated_val) <
                 brier_score_loss(y[val], selected_val) - 0.001 and
                 average_precision_score(y[val], calibrated_val) >=
                 average_precision_score(y[val], selected_val) - 0.001)
    chosen_val = calibrated_val if calibrate else selected_val
    threshold, f1_val = optimize_threshold(y[val], chosen_val)
    decision = {"best_challenger_by_cv": challenger, "paired_validation": paired_val,
                "promotion_rule_passed": promote, "selected": selected,
                "calibration": {"method": "Platt on grouped OOF training scores",
                                "raw_validation": metrics_rank(y[val], selected_val),
                                "calibrated_validation": metrics_rank(y[val], calibrated_val),
                                "adopted": calibrate},
                "threshold_from_validation_f1": threshold, "f1_validation": f1_val}
    write_json(out / "decision_validacion.json", decision)
    print("DECISIÓN FIJADA ANTES DE PRUEBA", decision, flush=True)

    # Una única consulta a la prueba histórica, después de fijar la decisión.
    x_selected, _, _ = feature_frame(df,
        distinct_missing=next(s for s in specs if s["name"] == selected)["distinct_missing"],
        density=next(s for s in specs if s["name"] == selected)["density"],
        age_category=next(s for s in specs if s["name"] == selected)["age_category"])
    old_test = old.predict_proba(x_base.iloc[test])[:, 1]
    selected_test = fitted[selected].predict_proba(x_selected.iloc[test])[:, 1]
    if calibrate:
        selected_test = calibrator.predict_proba(
            logit(np.clip(selected_test, 1e-6, 1 - 1e-6)).reshape(-1, 1)
        )[:, 1]
    historical = {
        "status": "comparación interna exploratoria; prueba expuesta previamente",
        "original": metrics_rank(y[test], old_test),
        "selected": metrics_rank(y[test], selected_test),
        "selected_at_validation_threshold": metricas(y[test], selected_test, threshold),
        "original_at_original_threshold": metricas(y[test], old_test,
            archived["threshold_from_validation"]),
        "topk_original": topk(y[test], old_test),
        "topk_selected": topk(y[test], selected_test),
        "paired_delta_ap": grouped_delta_bootstrap(y[test], selected_test, old_test, groups[test]),
        "calibration_original": calibration_bins(y[test], old_test),
        "calibration_selected": calibration_bins(y[test], selected_test),
        "subgroups_selected": subgroup_report(y[test], selected_test, threshold,
                                               df.iloc[test].reset_index(drop=True)),
    }
    write_json(out / "comparacion_historica.json", historical)
    figures(y[test], old_test, selected_test, out / "curvas_pr_calibracion.png")
    # Artefacto separado, incluso si la regla conserva la referencia.
    chosen_spec = next(s for s in specs if s["name"] == selected)
    raw_pipeline = Pipeline([
        ("normalizar_entrada", FeatureBuilder(
            distinct_missing=chosen_spec["distinct_missing"],
            density=chosen_spec["density"], age_category=chosen_spec["age_category"])),
        ("clasificador", fitted[selected]),
    ])
    predictor = CandidatePredictor(raw_pipeline, calibrator if calibrate else None)
    raw_sample = df.iloc[test[:100]][FEATURES]
    if not np.allclose(predictor.predict_proba(raw_sample)[:, 1], selected_test[:100], atol=1e-12, rtol=0):
        raise AssertionError("La inferencia con entrada bruta difiere de la evaluación")
    artifact = {"predictor": predictor, "calibrator": calibrator if calibrate else None,
                "features": FEATURES, "selected_spec": next(s for s in specs if s["name"] == selected),
                "target": "SIN_ACCESO=1", "threshold_exploratory": threshold,
                "source_sha256": source["source_sha256"],
                "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                             "numpy": np.__version__, "scikit_learn": sklearn.__version__}}
    joblib.dump(artifact, out / "candidato_separado.joblib", compress=3)
    write_json(out / "experimentos.json", {
        "complete": True, "candidates": results, "decision": decision,
        "versions": artifact["versions"], "seed": SEED,
        "total_elapsed_seconds": round(time.perf_counter() - started, 3),
        "packages_unavailable": ["catboost", "lightgbm", "xgboost"],
    })
    print("TERMINADO", out, flush=True)


if __name__ == "__main__":
    main()
