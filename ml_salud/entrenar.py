"""Experimento reproducible: riesgo de no acceder a atención formal, CNPV 2018 Atlántico.

Uso: python -m ml_salud.entrenar --data-dir RUTA_A_CSV --output-dir RUTA_SALIDA
La clase positiva del modelo es SIN_ACCESO=1 (ACCESO_FORMAL_SALUD=0).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, OrdinalEncoder, StandardScaler

from ml_salud.esquema import (
    CATEGORICAL, DWELL_FEATURES, EXCLUDED_TEMPORAL, FEATURES, HOUSE_FEATURES,
    LEAKAGE_COLUMNS, NUMERIC, PERSON_SOURCE_FEATURES, prepare_features,
)

SEED = 42
PERSON_FILE = "CNPV2018_5PER_A2_08.CSV"
HOUSE_FILE = "CNPV2018_2HOG_A2_08.CSV"
DWELL_FILE = "CNPV2018_1VIV_A2_08.CSV"
DWELL_KEY = ["U_DPTO", "U_MPIO", "UA_CLASE", "COD_ENCUESTAS", "U_VIVIENDA"]
HOUSE_KEY = DWELL_KEY + ["P_NROHOG"]
PERSON_KEY = HOUSE_KEY + ["P_NRO_PER"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data(data_dir: Path):
    paths = [data_dir / name for name in (PERSON_FILE, HOUSE_FILE, DWELL_FILE)]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    person_cols = (
        PERSON_KEY + PERSON_SOURCE_FEATURES +
        ["P_ENFERMO", "P_QUEHIZO_PPAL", "PA_LO_ATENDIERON", "PA1_CALIDAD_SERV"]
    )
    person = pd.read_csv(paths[0], usecols=list(dict.fromkeys(person_cols)), low_memory=False)
    n_people = len(person)
    sick = person.loc[person["P_ENFERMO"].eq(1)].copy()
    action = sick["P_QUEHIZO_PPAL"]
    attended = sick["PA_LO_ATENDIERON"]
    formal = (action.eq(1) & attended.eq(1)) | action.eq(2)
    no_formal = (action.eq(1) & attended.eq(2)) | action.isin(range(3, 10))
    if (formal & no_formal).any():
        raise AssertionError("Definición de la etiqueta contradictoria")
    label_breakdown = {
        "eps_atendido": int((action.eq(1) & attended.eq(1)).sum()),
        "medico_particular": int(action.eq(2).sum()),
        "eps_no_atendido": int((action.eq(1) & attended.eq(2)).sum()),
        "otras_acciones_o_ninguna": int(action.isin(range(3, 10)).sum()),
        "accion_no_clasificable": int(action.eq(0).sum()),
        "eps_atencion_no_informa": int((action.eq(1) & attended.eq(9)).sum()),
    }
    sick["SIN_ACCESO"] = np.select(
        [no_formal, formal], [1, 0], default=np.nan
    )
    n_sick = len(sick)
    n_unlabeled = int(sick["SIN_ACCESO"].isna().sum())
    sick = sick.dropna(subset=["SIN_ACCESO"]).copy()
    sick["SIN_ACCESO"] = sick["SIN_ACCESO"].astype("int8")
    if sick.duplicated(PERSON_KEY).any():
        raise AssertionError("Hay claves de persona duplicadas")
    house = pd.read_csv(
        paths[1], usecols=DWELL_KEY + ["H_NROHOG"] + HOUSE_FEATURES,
        low_memory=False,
    ).rename(columns={"H_NROHOG": "P_NROHOG"})
    dwell = pd.read_csv(paths[2], usecols=DWELL_KEY + DWELL_FEATURES, low_memory=False)
    if house.duplicated(HOUSE_KEY).any() or dwell.duplicated(DWELL_KEY).any():
        raise AssertionError("Las claves de hogar/vivienda no son únicas")
    sick = sick.merge(house, on=HOUSE_KEY, how="left", validate="many_to_one", indicator=True)
    house_match = int(sick["_merge"].eq("both").sum())
    sick = sick.drop(columns="_merge").merge(
        dwell, on=DWELL_KEY, how="left", validate="many_to_one", indicator=True
    )
    dwell_match = int(sick["_merge"].eq("both").sum())
    sick = sick.drop(columns="_merge")
    if house_match != len(sick) or dwell_match != len(sick):
        raise AssertionError("Hay personas sin hogar o vivienda enlazados")
    source = {
        "people": n_people, "sick": n_sick, "unlabeled": n_unlabeled,
        "labeled": len(sick), "no_access": int(sick["SIN_ACCESO"].sum()),
        "label_breakdown": label_breakdown,
        "house_match": house_match, "dwell_match": dwell_match,
        "source_sha256": {p.name: sha256(p) for p in paths},
    }
    return sick, source


def group_ids(df: pd.DataFrame) -> np.ndarray:
    # Separa viviendas completas, incluso cuando contienen más de un hogar.
    # Incluye municipio y clase: COD_ENCUESTAS no se presume global.
    return (
        df[DWELL_KEY].fillna(-1).astype("int64").astype("string")
        .agg("|".join, axis=1).to_numpy()
    )


def split_three(x, y, groups):
    splitter = StratifiedGroupKFold(n_splits=7, shuffle=True, random_state=SEED)
    folds = [test for _, test in splitter.split(x, y, groups)]
    train = np.concatenate(folds[2:])
    val, test = folds[1], folds[0]
    if (
        set(groups[train]) & set(groups[val]) or
        set(groups[train]) & set(groups[test]) or
        set(groups[val]) & set(groups[test])
    ):
        raise AssertionError("Una vivienda aparece en más de una partición")
    return train, val, test


def encoded_preprocessor(age_as_category=False):
    cats = CATEGORICAL + (["P_EDADR"] if age_as_category else [])
    nums = [column for column in NUMERIC if column not in cats]
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=50), cats),
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]), nums),
    ])


def hist_preprocessor():
    return ColumnTransformer([
        ("cat", OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1,
        ), CATEGORICAL),
        ("num", SimpleImputer(strategy="median", add_indicator=True), NUMERIC),
    ], sparse_threshold=0)


def metricas(y, score, threshold=0.5):
    pred = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "brier": float(brier_score_loss(y, score)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def optimize_threshold(y, score):
    precision, recall, threshold = precision_recall_curve(y, score)
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(
        precision[:-1] + recall[:-1], 1e-12
    )
    best = int(np.argmax(f1))
    return float(threshold[best]), float(f1[best])


def calibration_bins(y, score, bins=10):
    frame = pd.DataFrame({"y": np.asarray(y), "score": score})
    frame["bin"] = pd.qcut(frame["score"], q=bins, duplicates="drop")
    return [
        {"n": int(len(group)), "mean_predicted": float(group.score.mean()),
         "observed": float(group.y.mean())}
        for _, group in frame.groupby("bin", observed=True)
    ]


def subgroups(y, score, threshold, raw, column):
    result = {}
    for code, positions in raw.groupby(column, dropna=False).indices.items():
        if len(positions) < 50:
            continue
        yy = y[positions]
        ss = score[positions]
        pp = ss >= threshold
        result[str(code)] = {
            "n": int(len(positions)),
            "prevalence": float(yy.mean()),
            "recall_no_access": float(recall_score(yy, pp, zero_division=0)),
            "precision_no_access": float(precision_score(yy, pp, zero_division=0)),
            "predicted_positive_rate": float(pp.mean()),
        }
    return result


def bootstrap_test(y, scores, groups, selected, competitor, thresholds, repetitions=250):
    """Intervalos por remuestreo de viviendas, solo para incertidumbre."""
    _, inverse = np.unique(groups, return_inverse=True)
    order = np.argsort(inverse)
    counts = np.bincount(inverse)
    members = np.split(order, np.cumsum(counts)[:-1])
    rng = np.random.default_rng(SEED + 2)
    draws = {
        "selected_ap": [], "selected_roc_auc": [], "selected_brier": [],
        "selected_f1": [], "selected_precision": [], "selected_recall": [],
        "delta_ap_vs_competitor": [],
    }
    for _ in range(repetitions):
        sampled = rng.integers(0, len(members), size=len(members))
        idx = np.concatenate([members[j] for j in sampled])
        yy = y[idx]
        if len(np.unique(yy)) < 2:
            continue
        ss = scores[selected][idx]
        cc = scores[competitor][idx]
        pp = ss >= thresholds[selected]
        draws["selected_ap"].append(average_precision_score(yy, ss))
        draws["selected_roc_auc"].append(roc_auc_score(yy, ss))
        draws["selected_brier"].append(brier_score_loss(yy, ss))
        draws["selected_f1"].append(f1_score(yy, pp, zero_division=0))
        draws["selected_precision"].append(precision_score(yy, pp, zero_division=0))
        draws["selected_recall"].append(recall_score(yy, pp, zero_division=0))
        draws["delta_ap_vs_competitor"].append(
            average_precision_score(yy, ss) - average_precision_score(yy, cc)
        )
    return {
        "method": "Percentiles 2.5 y 97.5 de bootstrap agrupado por vivienda",
        "repetitions": repetitions, "competitor": competitor,
        "intervals_95": {
            name: [float(v) for v in np.quantile(values, [0.025, 0.975])]
            for name, values in draws.items()
        },
    }


def plot_curves(y, scores, selected, out: Path):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    prevalence = float(y.mean())
    axes[0].plot([0, 1], [0, 1], color="0.6", linestyle="--")
    axes[1].axhline(prevalence, color="0.6", linestyle="--")
    for name, score in scores.items():
        if name == "baseline":
            continue  # Un clasificador constante no tiene curva PR/ROC útil.
        fpr, tpr, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        axes[0].plot(fpr, tpr, label=name)
        axes[1].plot(recall, precision, label=name)
    axes[0].set(xlabel="Tasa de falsos positivos", ylabel="Recall", title="ROC")
    axes[1].set(xlabel="Recall", ylabel="Precisión", title="Precisión–recall")
    bins = calibration_bins(y, scores[selected])
    axes[2].plot([0, 1], [0, 1], color="0.6", linestyle="--")
    axes[2].plot(
        [b["mean_predicted"] for b in bins],
        [b["observed"] for b in bins],
        marker="o", label=selected,
    )
    axes[2].set(xlabel="Riesgo predicho", ylabel="Frecuencia observada",
                title="Calibración")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / "curvas.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "resultados")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    df, source = load_data(args.data_dir)
    x = prepare_features(df)
    quality = {
        "n": len(df),
        "excluded_temporal_missing": {
            column: {
                "raw_missing": int(df[column].isna().sum()),
                "pct": float(100 * df[column].isna().mean()),
            }
            for column in EXCLUDED_TEMPORAL
        },
        "features": [
            {
                "feature": column,
                "raw_missing": int(df[column].isna().sum()),
                "missing_or_sentinel": int(
                    x[column].eq("__FALTANTE__").sum()
                    if column in CATEGORICAL else x[column].isna().sum()
                ),
                "pct": float(
                    100 * (
                        x[column].eq("__FALTANTE__").mean()
                        if column in CATEGORICAL else x[column].isna().mean()
                    )
                ),
                "unique": int(df[column].nunique(dropna=True)),
            }
            for column in FEATURES
        ],
    }
    (out / "perfil_calidad.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    y = df["SIN_ACCESO"].to_numpy()
    groups = group_ids(df)
    train, val, test = split_three(x, y, groups)
    split_info = {
        name: {
            "n": int(len(idx)), "dwellings": int(len(set(groups[idx]))),
            "no_access": int(y[idx].sum()), "prevalence": float(y[idx].mean()),
        }
        for name, idx in (("train", train), ("validation", val), ("test", test))
    }
    print("DATOS", json.dumps(source, ensure_ascii=False), flush=True)
    print("PARTICIONES", json.dumps(split_info, ensure_ascii=False), flush=True)
    xt, xv, xh = x.iloc[train], x.iloc[val], x.iloc[test]
    yt, yv, yh = y[train], y[val], y[test]
    gt = groups[train]
    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + 1)
    specs = {
        "logistica": (
            Pipeline([("prep", encoded_preprocessor(age_as_category=True)),
                      ("model", LogisticRegression(max_iter=1000, solver="lbfgs"))]),
            {"model__C": [0.05, 0.5, 5.0], "model__class_weight": [None, "balanced"]},
        ),
        "random_forest": (
            Pipeline([("prep", encoded_preprocessor()),
                      ("model", RandomForestClassifier(
                          n_estimators=120, n_jobs=4, random_state=SEED
                      ))]),
            {"model__max_depth": [12, 20],
             "model__min_samples_leaf": [10, 40]},
        ),
        "hist_gradient_boosting": (
            Pipeline([("prep", hist_preprocessor()),
                      ("model", HistGradientBoostingClassifier(
                          categorical_features=list(range(len(CATEGORICAL))),
                          early_stopping=False, random_state=SEED,
                      ))]),
            {"model__learning_rate": [0.04, 0.1],
             "model__max_leaf_nodes": [15, 31],
             "model__min_samples_leaf": [30],
             "model__max_iter": [180, 320, 500]},
        ),
    }
    dummy = DummyClassifier(strategy="prior").fit(xt, yt)
    fitted = {"baseline": dummy}
    model_results = {
        "baseline": {
            "cv_pr_auc": None, "best_params": {},
            "validation": metricas(yv, dummy.predict_proba(xv)[:, 1]),
        }
    }
    for name, (pipe, grid) in specs.items():
        print("ENTRENANDO", name, flush=True)
        search = GridSearchCV(
            pipe, grid, scoring="average_precision",
            cv=cv.split(xt, yt, gt), n_jobs=1, refit=True,
            error_score="raise", return_train_score=False,
        )
        search.fit(xt, yt)
        fitted[name] = search.best_estimator_
        score = search.predict_proba(xv)[:, 1]
        model_results[name] = {
            "cv_pr_auc": float(search.best_score_),
            "best_params": search.best_params_,
            "validation": metricas(yv, score),
            "cv_candidates": [
                {
                    "params": p,
                    "mean_pr_auc": float(m),
                    "std_pr_auc": float(s),
                }
                for p, m, s in zip(
                    search.cv_results_["params"],
                    search.cv_results_["mean_test_score"],
                    search.cv_results_["std_test_score"],
                )
            ],
        }
        print("VALIDACIÓN", name, model_results[name]["validation"], flush=True)
    selected = max(
        specs, key=lambda name: (
            model_results[name]["validation"]["pr_auc"],
            -model_results[name]["validation"]["brier"],
        )
    )
    thresholds = {"baseline": 0.5}
    for name in specs:
        val_score = fitted[name].predict_proba(xv)[:, 1]
        thresholds[name], best_f1 = optimize_threshold(yv, val_score)
        model_results[name]["validation_optimal_threshold"] = thresholds[name]
        model_results[name]["validation_f1_at_optimal_threshold"] = best_f1
    threshold = thresholds[selected]
    val_best_f1 = model_results[selected]["validation_f1_at_optimal_threshold"]
    print("SELECCIONADO", selected, "UMBRAL", threshold, flush=True)
    test_scores = {name: model.predict_proba(xh)[:, 1] for name, model in fitted.items()}
    test_metrics = {
        name: metricas(yh, score, thresholds[name])
        for name, score in test_scores.items()
    }
    selected_test = test_scores[selected]
    competitor = max(
        (name for name in specs if name != selected),
        key=lambda name: model_results[name]["validation"]["pr_auc"],
    )
    uncertainty = bootstrap_test(
        yh, test_scores, groups[test], selected, competitor, thresholds
    )
    importance = permutation_importance(
        fitted[selected], xv, yv, scoring="average_precision",
        n_repeats=3, random_state=SEED, n_jobs=1,
    )
    ranking = sorted(
        [
            {
                "feature": feature, "mean_ap_drop": float(mean),
                "std_ap_drop": float(std),
            }
            for feature, mean, std in zip(
                FEATURES, importance.importances_mean, importance.importances_std
            )
        ],
        key=lambda item: item["mean_ap_drop"], reverse=True,
    )
    raw_test = df.iloc[test].reset_index(drop=True)
    subgroup_metrics = {
        column: subgroups(yh, selected_test, threshold, raw_test, column)
        for column in ("P_SEXO", "CONDICION_FISICA", "UA_CLASE", "U_MPIO")
    }
    result = {
        "target": "SIN_ACCESO=1 equivale a ACCESO_FORMAL_SALUD=0",
        "metric_definition": (
            "pr_auc almacena average_precision_score de scikit-learn "
            "(Average Precision no interpolada), no el área trapezoidal PR"
        ),
        "source": source, "split": split_info, "features": FEATURES,
        "numeric_features": NUMERIC, "excluded_leakage": sorted(LEAKAGE_COLUMNS),
        "excluded_temporal": EXCLUDED_TEMPORAL,
        "models": model_results, "selected_model": selected,
        "thresholds_from_validation": thresholds,
        "threshold_from_validation": threshold,
        "validation_f1_at_selected_threshold": val_best_f1,
        "test_metrics": test_metrics,
        "selected_test_at_0_5": metricas(yh, selected_test, 0.5),
        "test_uncertainty": uncertainty,
        "calibration_deciles_test": calibration_bins(yh, selected_test),
        "permutation_importance_validation": ranking,
        "subgroups_test": subgroup_metrics,
        "versions": {
            "python": platform.python_version(), "pandas": pd.__version__,
            "numpy": np.__version__, "scikit_learn": sklearn.__version__,
        },
        "seed": SEED,
        "schema_sha256": sha256(Path(__file__).parent / "esquema.py"),
    }
    (out / "resultados.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    inference_pipeline = Pipeline([
        ("normalizar_entrada", FunctionTransformer(prepare_features, validate=False)),
        ("clasificador", fitted[selected]),
    ])
    raw_sample = df.iloc[test[:100]][FEATURES]
    if not np.allclose(
        inference_pipeline.predict_proba(raw_sample)[:, 1],
        selected_test[:100], rtol=0, atol=1e-12,
    ):
        raise AssertionError("La inferencia con entrada bruta difiere de la evaluación")
    joblib.dump(
        {
            "pipeline": inference_pipeline, "features": FEATURES,
            "threshold_no_access": threshold,
            "target": result["target"], "source_sha256": source["source_sha256"],
            "schema_sha256": result["schema_sha256"],
            "versions": result["versions"],
        },
        out / "modelo_sin_acceso.joblib", compress=3,
    )
    plot_curves(yh, test_scores, selected, out)
    print("PRUEBA", json.dumps(test_metrics, ensure_ascii=False), flush=True)
    print("SALIDA", out, flush=True)


if __name__ == "__main__":
    main()
