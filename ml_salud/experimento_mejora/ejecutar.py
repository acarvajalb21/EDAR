"""Búsqueda de mejora del modelo v2 fijada en INFORME.md (sección 1).

Uso (desde proyecto_salud/):
    ml_salud\\.venv\\Scripts\\python.exe -m ml_salud.experimento_mejora.ejecutar --data-dir datos

No consulta la partición de prueba ni modifica ningún archivo fuera de esta carpeta.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from ml_salud.contexto import DWELL_KEY, FEATURES_V2, MGN_FILE, NUMERIC_V2, PERSON_FILE, SECTION_COLUMNS, prepare_features_v2
from ml_salud.entrenar import DWELL_FILE, group_ids, hist_preprocessor, load_data, metricas, optimize_threshold, split_three
from ml_salud.esquema import CATEGORICAL

HERE = Path(__file__).resolve().parent
OUT = HERE / "salidas"
SEED_MODEL, SEED_CV, SEED_BOOT, SEED_TE = 42, 43, 44, 45
TE_M, TE_FOLDS, BOOT_REPS = 20.0, 5, 250
ARCHIVED_V2_VAL_AP = 0.38605411340936086
TE_SEC = ["TE_SECCION", "N_SECCION"]
TE_MZA = ["TE_MANZANA", "N_MANZANA"]
AGG = ["SEC_PCT_DIFICULTAD", "SEC_EDU_MEDIA", "SEC_PCT_60MAS", "SEC_ESTRATO_MEDIO",
       "SEC_PCT_INTERNET", "SEC_LOG_PERSONAS", "MZA_PCT_ENFERMOS"]
FEATURE_SETS = {
    "F0_v2": [],
    "F1_v2+TE_seccion": TE_SEC,
    "F2_v2+TE_seccion+TE_manzana": TE_SEC + TE_MZA,
    "F3_F2+agregados": TE_SEC + TE_MZA + AGG,
    "F4_v2+agregados_sin_etiqueta": AGG,
}
GRID = [dict(num_leaves=nl, learning_rate=lr, min_child_samples=mc, class_weight=cw)
        for nl in (15, 31, 63) for lr in (0.02, 0.05) for mc in (20, 100) for cw in (None, "balanced")]
N_EST = (200, 400, 700, 1000)
T0 = time.time()


def log(*args):
    print(f"[{time.time() - T0:7.1f}s]", *args, flush=True)


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------- agregados sin etiqueta
def territorial_aggregates(df: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """Agregados de sección/manzana con todo el censo, excluyendo la propia vivienda."""
    mgn = pd.read_csv(data_dir / MGN_FILE, usecols=list(dict.fromkeys(DWELL_KEY + SECTION_COLUMNS + ["U_MZA"])),
                      dtype={**{c: "string" for c in SECTION_COLUMNS[2:]}, "U_MZA": "string"}, low_memory=False)
    # Misma construcción que contexto.py para que SECCION_ID coincida.
    mgn["SECCION_ID"] = mgn[SECTION_COLUMNS].astype("string").agg("|".join, axis=1)
    mgn["MANZANA_ID"] = mgn["SECCION_ID"] + "|" + mgn["U_MZA"].fillna("NA")
    mgn = mgn[DWELL_KEY + ["SECCION_ID", "MANZANA_ID"]]
    p = pd.read_csv(data_dir / PERSON_FILE, usecols=DWELL_KEY + ["P_ENFERMO", "CONDICION_FISICA", "P_NIVEL_ANOSR", "P_EDADR"],
                    low_memory=False)
    p = pd.DataFrame({
        **{k: p[k] for k in DWELL_KEY},
        "n_pers": 1,
        "enf_v": p["P_ENFERMO"].isin([1, 2]).astype(int), "enf_1": p["P_ENFERMO"].eq(1).astype(int),
        "dif_v": p["CONDICION_FISICA"].isin([1, 2]).astype(int), "dif_1": p["CONDICION_FISICA"].eq(1).astype(int),
        "edu_v": p["P_NIVEL_ANOSR"].between(1, 10).astype(int),
        "edu_s": p["P_NIVEL_ANOSR"].where(p["P_NIVEL_ANOSR"].between(1, 10), 0),
        "age_v": p["P_EDADR"].notna().astype(int), "age_60": p["P_EDADR"].ge(13).astype(int),
    })
    per_dw = p.groupby(DWELL_KEY, sort=False).sum().reset_index()
    d = pd.read_csv(data_dir / DWELL_FILE, usecols=DWELL_KEY + ["VA1_ESTRATO", "VF_INTERNET"], low_memory=False)
    d = pd.DataFrame({
        **{k: d[k] for k in DWELL_KEY},
        "est_v": d["VA1_ESTRATO"].between(0, 6).astype(int),
        "est_s": d["VA1_ESTRATO"].where(d["VA1_ESTRATO"].between(0, 6), 0),
        "int_v": d["VF_INTERNET"].isin([1, 2]).astype(int), "int_1": d["VF_INTERNET"].eq(1).astype(int),
    })
    dw = d.merge(per_dw, on=DWELL_KEY, how="left").fillna(0).merge(mgn, on=DWELL_KEY, how="left", validate="one_to_one")
    if dw["SECCION_ID"].isna().any():
        raise AssertionError("Viviendas sin sección en el MGN")
    sums = [c for c in dw.columns if c not in DWELL_KEY + ["SECCION_ID", "MANZANA_ID"]]
    sec = dw.groupby("SECCION_ID")[sums].sum()
    mza = dw.groupby("MANZANA_ID")[["enf_v", "enf_1"]].sum()
    own = df[DWELL_KEY].merge(dw, on=DWELL_KEY, how="left", validate="many_to_one")
    if len(own) != len(df) or not np.array_equal(own["SECCION_ID"].to_numpy(), df["SECCION_ID"].to_numpy()):
        raise AssertionError("La sección no coincide con contexto.py")
    s = sec.reindex(own["SECCION_ID"]).to_numpy()
    s = pd.DataFrame(s, columns=sums) - own[sums].reset_index(drop=True)
    m = mza.reindex(own["MANZANA_ID"]).reset_index(drop=True) - own[["enf_v", "enf_1"]].reset_index(drop=True)

    def ratio(a, b):
        return (a / b.where(b > 0)).astype(float).to_numpy()

    out = pd.DataFrame({
        "SEC_PCT_DIFICULTAD": ratio(s["dif_1"], s["dif_v"]),
        "SEC_EDU_MEDIA": ratio(s["edu_s"], s["edu_v"]),
        "SEC_PCT_60MAS": ratio(s["age_60"], s["age_v"]),
        "SEC_ESTRATO_MEDIO": ratio(s["est_s"], s["est_v"]),
        "SEC_PCT_INTERNET": ratio(s["int_1"], s["int_v"]),
        "SEC_LOG_PERSONAS": np.log1p(s["n_pers"].clip(lower=0).astype(float)).to_numpy(),
        "MZA_PCT_ENFERMOS": ratio(m["enf_1"], m["enf_v"]),
    }, index=df.index)
    return out, own["MANZANA_ID"].to_numpy()


# ---------------------------------------------------------------- codificación por objetivo
def _rate(src_keys, src_y, dst_keys, prior):
    stats = pd.DataFrame({"k": src_keys, "y": src_y}).groupby("k")["y"].agg(["sum", "count"])
    dst = pd.Series(dst_keys)
    s = dst.map(stats["sum"]).fillna(0).to_numpy(float)
    n = dst.map(stats["count"]).fillna(0).to_numpy(float)
    return (s + TE_M * prior) / (n + TE_M), n


def target_encode(fit_idx, eval_idx, y, keys: dict, inner_fold):
    """TE solo con etiquetas de fit_idx; filas de ajuste fuera de pliegue interno por vivienda."""
    res_fit = {f: np.empty(len(fit_idx)) for k in keys for f in (f"TE_{k}", f"N_{k}")}
    res_eval = {}
    folds = inner_fold[fit_idx]
    for k, arr in keys.items():
        for f in range(TE_FOLDS):
            dst = folds == f
            src = fit_idx[~dst]
            r, n = _rate(arr[src], y[src], arr[fit_idx[dst]], y[src].mean())
            res_fit[f"TE_{k}"][dst], res_fit[f"N_{k}"][dst] = r, n
        r, n = _rate(arr[fit_idx], y[fit_idx], arr[eval_idx], y[fit_idx].mean())
        res_eval[f"TE_{k}"], res_eval[f"N_{k}"] = r, n
    return pd.DataFrame(res_fit), pd.DataFrame(res_eval)


# ---------------------------------------------------------------- matrices y modelos
def build(base, extra_all, fit_idx, eval_idx, y, keys, inner_fold, cols):
    xf = base.iloc[fit_idx].reset_index(drop=True)
    xe = base.iloc[eval_idx].reset_index(drop=True)
    te_cols = [c for c in cols if c.startswith(("TE_", "N_"))]
    agg_cols = [c for c in cols if c in AGG]
    if te_cols:
        tf, tev = target_encode(fit_idx, eval_idx, y, keys, inner_fold)
        xf, xe = pd.concat([xf, tf[te_cols]], axis=1), pd.concat([xe, tev[te_cols]], axis=1)
    if agg_cols:
        xf = pd.concat([xf, extra_all.iloc[fit_idx][agg_cols].reset_index(drop=True)], axis=1)
        xe = pd.concat([xe, extra_all.iloc[eval_idx][agg_cols].reset_index(drop=True)], axis=1)
    return xf, xe


def to_lgb(xf, xe):
    xf, xe = xf.copy(), xe.copy()
    for c in CATEGORICAL:
        cats = pd.Index(sorted(xf[c].unique()))  # categorías aprendidas solo en el ajuste
        xf[c] = pd.Categorical(xf[c], categories=cats)
        xe[c] = pd.Categorical(xe[c], categories=cats)
    return xf, xe


def fit_hgb(xf, yf, xe, extra_numeric):
    pipe = Pipeline([("prep", hist_preprocessor(numeric=NUMERIC_V2 + extra_numeric)),
                     ("model", HistGradientBoostingClassifier(
                         categorical_features=list(range(len(CATEGORICAL))), learning_rate=0.04,
                         max_leaf_nodes=15, min_samples_leaf=30, max_iter=500,
                         early_stopping=False, random_state=SEED_MODEL))])
    pipe.fit(xf, yf)
    return pipe.predict_proba(xe)[:, 1]


def fit_lgb_staged(xf, yf, xe, params, n_list=N_EST):
    xf, xe = to_lgb(xf, xe)
    model = lgb.LGBMClassifier(n_estimators=max(n_list), colsample_bytree=0.8, reg_lambda=1.0,
                               random_state=SEED_MODEL, n_jobs=8, deterministic=True, force_row_wise=True,
                               verbose=-1, **params)
    model.fit(xf, yf, categorical_feature=CATEGORICAL)
    return {n: model.predict_proba(xe, num_iteration=n)[:, 1] for n in n_list}


def cfg_name(p, n):
    return f"lgb_nl{p['num_leaves']}_lr{p['learning_rate']}_mc{p['min_child_samples']}_cw{p['class_weight']}_n{n}"


# ---------------------------------------------------------------- métricas e inferencia
def threshold_metrics(y, s, thr):
    m = metricas(y, s, thr)
    pred = (s >= thr).astype(int)
    m["accuracy"] = float(accuracy_score(y, pred))
    m["balanced_accuracy"] = float(balanced_accuracy_score(y, pred))
    m["flagged_fraction"] = float(pred.mean())
    return m


def paired_bootstrap(y, cand, ref, groups, reps=BOOT_REPS, seed=SEED_BOOT):
    """Diferencia candidato − referencia; remuestrea viviendas completas y recalcula AP/Brier completos."""
    _, inv = np.unique(groups, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    members = np.split(order, np.cumsum(np.bincount(inv))[:-1])
    rng = np.random.default_rng(seed)
    d_ap, d_br, d_auc, failed = [], [], [], 0
    for _ in range(reps):
        idx = np.concatenate([members[j] for j in rng.integers(0, len(members), len(members))])
        yy = y[idx]
        if yy.min() == yy.max():
            failed += 1
            continue
        d_ap.append(average_precision_score(yy, cand[idx]) - average_precision_score(yy, ref[idx]))
        d_auc.append(roc_auc_score(yy, cand[idx]) - roc_auc_score(yy, ref[idx]))
        d_br.append(brier_score_loss(yy, cand[idx]) - brier_score_loss(yy, ref[idx]))
    q = lambda v: [float(x) for x in np.quantile(v, [0.025, 0.975])]
    return {
        "definicion": "candidato menos v2; AP y ROC-AUC positivos favorecen al candidato, Brier negativo lo favorece",
        "metodo": "bootstrap percentil pareado remuestreando viviendas completas", "semilla": seed,
        "replicas_solicitadas": reps, "replicas_validas": len(d_ap), "replicas_fallidas": failed,
        "unidades_remuestreadas": len(members),
        "delta_ap": float(average_precision_score(y, cand) - average_precision_score(y, ref)), "ic95_delta_ap": q(d_ap),
        "delta_roc_auc": float(roc_auc_score(y, cand) - roc_auc_score(y, ref)), "ic95_delta_roc_auc": q(d_auc),
        "delta_brier": float(brier_score_loss(y, cand) - brier_score_loss(y, ref)), "ic95_delta_brier": q(d_br),
        "nota": "Condicionado a modelos ya entrenados: no incluye variabilidad de entrenamiento ni de selección.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df, source = load_data(args.data_dir, with_context=True)
    x = prepare_features_v2(df)[FEATURES_V2]
    y = df["SIN_ACCESO"].to_numpy()
    groups = group_ids(df)
    train, val, _test_no_usada = split_three(x, y, groups)
    del _test_no_usada
    log("datos", len(df), "train", len(train), "val", len(val))
    agg, manzana = territorial_aggregates(df, args.data_dir)
    sections = df["SECCION_ID"].to_numpy()
    keys = {"SECCION": sections, "MANZANA": manzana}
    dwell_code = pd.factorize(groups)[0]
    inner_fold = np.random.default_rng(SEED_TE).permutation(dwell_code.max() + 1)[dwell_code] % TE_FOLDS
    log("agregados listos; secciones", len(set(sections)), "manzanas", len(set(manzana)))

    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED_CV)
    folds = [(train[a], train[b]) for a, b in cv.split(x.iloc[train], y[train], groups[train])]
    if any(set(groups[a]) & set(groups[b]) for a, b in folds):
        raise AssertionError("Vivienda compartida entre pliegues")

    cv_scores = {}  # nombre -> lista AP por pliegue

    def record(name, fold_aps):
        cv_scores[name] = {"ap_pliegues": [float(v) for v in fold_aps],
                           "ap_media": float(np.mean(fold_aps)), "ap_de": float(np.std(fold_aps, ddof=1))}

    # Fase 1: rejilla LightGBM sobre F0
    t = time.time()
    per_cfg = {}
    for i, p in enumerate(GRID):
        aps = {n: [] for n in N_EST}
        for tr, va in folds:
            xf, xe = build(x, agg, tr, va, y, keys, inner_fold, [])
            for n, s in fit_lgb_staged(xf, y[tr], xe, p).items():
                aps[n].append(average_precision_score(y[va], s))
        for n in N_EST:
            record("F0_v2|" + cfg_name(p, n), aps[n])
            per_cfg[(i, n)] = np.mean(aps[n])
        log("rejilla", i + 1, "/", len(GRID), cfg_name(p, max(N_EST, key=lambda n: np.mean(aps[n]))),
            round(max(np.mean(v) for v in aps.values()), 5))
    grid_time = time.time() - t
    best_cfg_idx = sorted({i: max(per_cfg[(i, n)] for n in N_EST) for i in range(len(GRID))}.items(),
                          key=lambda kv: -kv[1])[:3]
    top3 = [GRID[i] for i, _ in best_cfg_idx]
    log("top3", top3)
    write_json("cv_rejilla_lightgbm.json", {"tiempo_s": grid_time, "cv": cv_scores, "top3": top3})

    # Fase 2: conjuntos de variables con HGB-v2 y top-3 LightGBM
    t = time.time()
    for fs, cols in FEATURE_SETS.items():
        hgb_aps = []
        lgb_aps = [{n: [] for n in N_EST} for _ in top3]
        for tr, va in folds:
            xf, xe = build(x, agg, tr, va, y, keys, inner_fold, cols)
            hgb_aps.append(average_precision_score(y[va], fit_hgb(xf, y[tr], xe, cols)))
            if fs != "F0_v2":
                for j, p in enumerate(top3):
                    for n, s in fit_lgb_staged(xf, y[tr], xe, p).items():
                        lgb_aps[j][n].append(average_precision_score(y[va], s))
        record(f"{fs}|hgb_v2_params", hgb_aps)
        if fs != "F0_v2":
            for j, p in enumerate(top3):
                for n in N_EST:
                    record(f"{fs}|" + cfg_name(p, n), lgb_aps[j][n])
        log("conjunto", fs, "HGB", round(np.mean(hgb_aps), 5))
    feat_time = time.time() - t
    write_json("cv_todas.json", {"tiempo_s_rejilla": grid_time, "tiempo_s_conjuntos": feat_time, "cv": cv_scores})

    # Fase 3: ajuste final en entrenamiento y evaluación en validación
    t = time.time()
    finals = {}
    for fs, cols in FEATURE_SETS.items():
        finals[f"{fs}|hgb_v2_params"] = None
        lgb_names = [k for k in cv_scores if k.startswith(fs + "|lgb")]
        finals[max(lgb_names, key=lambda k: cv_scores[k]["ap_media"])] = None
    candidate = max(cv_scores, key=lambda k: cv_scores[k]["ap_media"])  # regla preregistrada
    finals.setdefault(candidate, None)
    ref = "F0_v2|hgb_v2_params"
    yv = y[val]
    val_scores = {}
    for name in finals:
        fs, model = name.split("|")
        xf, xe = build(x, agg, train, val, y, keys, inner_fold, FEATURE_SETS[fs])
        if model == "hgb_v2_params":
            s = fit_hgb(xf, y[train], xe, FEATURE_SETS[fs])
        else:
            p = next(p for p in GRID if cfg_name(p, 0).rsplit("_n", 1)[0] == model.rsplit("_n", 1)[0])
            n = int(model.rsplit("_n", 1)[1])
            s = fit_lgb_staged(xf, y[train], xe, p, (n,))[n]
        val_scores[name] = s
        log("validación", name, round(average_precision_score(yv, s), 5))
    if abs(average_precision_score(yv, val_scores[ref]) - ARCHIVED_V2_VAL_AP) > 1e-9:
        raise AssertionError("La v2 reproducida no coincide con la validación archivada")
    final_time = time.time() - t
    table = {
        name: {"ap_cv_media": cv_scores[name]["ap_media"], "ap_cv_de": cv_scores[name]["ap_de"],
               "ap_val": float(average_precision_score(yv, s)), "roc_auc_val": float(roc_auc_score(yv, s)),
               "brier_val": float(brier_score_loss(yv, s))}
        for name, s in val_scores.items()
    }
    table["prevalencia"] = {"ap_cv_media": None, "ap_cv_de": None, "ap_val": float(yv.mean()), "roc_auc_val": 0.5,
                            "brier_val": float(brier_score_loss(yv, np.full(len(yv), y[train].mean())))}
    boot = paired_bootstrap(yv, val_scores[candidate], val_scores[ref], groups[val])
    thr = {k: optimize_threshold(yv, val_scores[k])[0] for k in (ref, candidate)}
    thresholds = {k: {"umbral_f1_validacion": threshold_metrics(yv, val_scores[k], thr[k]),
                      "umbral_0_5": threshold_metrics(yv, val_scores[k], 0.5)} for k in (ref, candidate)}
    dif = df["CONDICION_FISICA"].to_numpy()[val] == 1
    sens_dif = {k: float((val_scores[k][dif & (yv == 1)] >= thr[k]).mean()) for k in (ref, candidate)}
    br_ref, br_cand = table[ref]["brier_val"], table[candidate]["brier_val"]
    criteria = {
        "ganancia_ap_val_>=0.010": boot["delta_ap"] >= 0.010,
        "ic95_sobre_cero": boot["ic95_delta_ap"][0] > 0,
        "brier_no_empeora_>0.002": br_cand <= br_ref + 0.002,
    }
    pd.DataFrame({"fila_cohorte": val, "vivienda": dwell_code[val], "y": yv,
                  "p_v2": val_scores[ref], "p_candidato": val_scores[candidate]}).to_csv(
        OUT / "predicciones_validacion.csv.gz", index=False, compression="gzip")
    write_json("validacion.json", {"candidato": candidate, "referencia": ref, "tabla": table,
                                   "bootstrap_pareado": boot, "umbrales": thresholds,
                                   "sensibilidad_dificultad_umbral_f1": sens_dif, "criterios": criteria,
                                   "decision": "cumple" if all(criteria.values()) else "no cumple",
                                   "tiempo_s_final": final_time})
    log("CANDIDATO", candidate, json.dumps(table[candidate]), "BOOT", boot["delta_ap"], boot["ic95_delta_ap"])

    # Fase 4: CV agrupada por sección (informativa) para v2 y candidato
    t = time.time()
    sfolds = [(train[a], train[b]) for a, b in cv.split(x.iloc[train], y[train], sections[train])]
    if any(set(sections[a]) & set(sections[b]) for a, b in sfolds):
        raise AssertionError("Sección compartida entre pliegues")
    sec_cv = {}
    for name in dict.fromkeys([ref, candidate]):
        fs, model = name.split("|")
        aps = []
        for tr, va in sfolds:
            xf, xe = build(x, agg, tr, va, y, keys, inner_fold, FEATURE_SETS[fs])
            if model == "hgb_v2_params":
                s = fit_hgb(xf, y[tr], xe, FEATURE_SETS[fs])
            else:
                p = next(p for p in GRID if cfg_name(p, 0).rsplit("_n", 1)[0] == model.rsplit("_n", 1)[0])
                n = int(model.rsplit("_n", 1)[1])
                s = fit_lgb_staged(xf, y[tr], xe, p, (n,))[n]
            aps.append(average_precision_score(y[va], s))
        sec_cv[name] = {"ap_pliegues": aps, "ap_media": float(np.mean(aps)), "ap_de": float(np.std(aps, ddof=1))}
        log("CV sección", name, round(np.mean(aps), 5))
    write_json("cv_seccion.json", {"cv_por_seccion": sec_cv, "tiempo_s": time.time() - t})
    write_json("ejecucion.json", {
        "tiempo_total_s": time.time() - T0, "prueba_consultada": False,
        "semillas": {"particion": 42, "cv": SEED_CV, "modelo": SEED_MODEL, "bootstrap": SEED_BOOT, "te_pliegues": SEED_TE},
        "te": {"m": TE_M, "pliegues_internos": TE_FOLDS}, "fuentes_sha256": source["source_sha256"],
        "versiones": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                      "scikit_learn": sklearn.__version__, "lightgbm": lgb.__version__},
        "n_secciones": int(len(set(sections))), "n_manzanas": int(len(set(manzana))),
        "faltantes_agregados": {c: int(agg[c].isna().sum()) for c in AGG},
    })
    log("FIN")


if __name__ == "__main__":
    main()
