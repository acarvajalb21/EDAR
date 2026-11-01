"""Comparación fijada en PROTOCOLO.md: 26 variables frente a 28 con contexto de salud.

Uso: python -m ml_salud.experimento_contexto.ejecutar --data-dir RUTA_A_CSV
No evalúa la partición de prueba ni modifica ml_salud/resultados/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from ml_salud.contexto import CONTEXT_FEATURES, FEATURES_V2, NUMERIC_V2, add_context, prepare_features_v2
from ml_salud.entrenar import group_ids, load_data, metricas, optimize_threshold, split_three
from ml_salud.esquema import CATEGORICAL, FEATURES, NUMERIC
from ml_salud.experimentos_2026_10.ejecutar import grouped_delta_bootstrap, model_pipeline, topk, write_json

HERE = Path(__file__).resolve().parent
ARCHIVED_VALIDATION_AP = 0.3460616070316228
MIN_GAIN = 0.010
MAX_BRIER_LOSS = 0.002
MAX_SENSITIVITY_LOSS = 0.03


def fit_score(x, y, tr, va, features, numeric):
    model = model_pipeline(CATEGORICAL, numeric)
    model.fit(x.iloc[tr][features], y[tr])
    return model.predict_proba(x.iloc[va][features])[:, 1]


def cross_validate(x, y, folds):
    rows = []
    for tr, va in folds:
        old = fit_score(x, y, tr, va, FEATURES, NUMERIC)
        new = fit_score(x, y, tr, va, FEATURES_V2, NUMERIC_V2)
        rows.append({
            "ap_26": average_precision_score(y[va], old), "ap_28": average_precision_score(y[va], new),
            "roc_auc_26": roc_auc_score(y[va], old), "roc_auc_28": roc_auc_score(y[va], new),
        })
    mean = {key: float(np.mean([row[key] for row in rows])) for key in rows[0]}
    mean["delta_ap"] = mean["ap_28"] - mean["ap_26"]
    mean["pliegues"] = rows
    return mean


def sensitivity(y, score, threshold, mask):
    positives = mask & (y == 1)
    return {"positivos": int(positives.sum()), "sensibilidad": float((score[positives] >= threshold).mean())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    df, source = load_data(args.data_dir)
    df = add_context(df, args.data_dir)
    x = prepare_features_v2(df)
    y = df["SIN_ACCESO"].to_numpy()
    groups = group_ids(df)
    sections = df["SECCION_ID"].to_numpy()
    train, val, _ = split_three(x, y, groups)
    print("PARTICIONES", len(train), len(val), flush=True)

    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=43)
    by_dwelling = [(train[a], train[b]) for a, b in cv.split(x.iloc[train], y[train], groups[train])]
    by_section = [(train[a], train[b]) for a, b in cv.split(x.iloc[train], y[train], sections[train])]
    if any(set(sections[tr]) & set(sections[va]) for tr, va in by_section):
        raise AssertionError("Una sección aparece en ajuste y evaluación")
    cv_dwelling = cross_validate(x, y, by_dwelling)
    print("CV VIVIENDAS", cv_dwelling["ap_26"], cv_dwelling["ap_28"], flush=True)
    cv_section = cross_validate(x, y, by_section)
    print("CV SECCIONES", cv_section["ap_26"], cv_section["ap_28"], flush=True)

    old = fit_score(x, y, train, val, FEATURES, NUMERIC)
    new = fit_score(x, y, train, val, FEATURES_V2, NUMERIC_V2)
    if abs(average_precision_score(y[val], old) - ARCHIVED_VALIDATION_AP) > 1e-9:
        raise AssertionError("La referencia no reproduce la validación archivada")
    yv = y[val]
    threshold_old, _ = optimize_threshold(yv, old)
    threshold_new, _ = optimize_threshold(yv, new)
    validation = {"modelo_26": metricas(yv, old, threshold_old), "modelo_28": metricas(yv, new, threshold_new)}
    paired = grouped_delta_bootstrap(yv, new, old, groups[val])
    difficulty = df["CONDICION_FISICA"].to_numpy()[val]
    age = df["P_EDADR"].to_numpy()[val]
    subgroups = {}
    for name, mask in (("con_dificultad", difficulty == 1), ("sin_dificultad", difficulty == 2),
                       ("60_o_mas", age >= 13), ("menos_de_60", age < 13)):
        subgroups[name] = {"modelo_26": sensitivity(yv, old, threshold_old, mask),
                           "modelo_28": sensitivity(yv, new, threshold_new, mask)}
    sensitivity_loss = (subgroups["con_dificultad"]["modelo_26"]["sensibilidad"]
                        - subgroups["con_dificultad"]["modelo_28"]["sensibilidad"])
    criteria = {
        "ganancia_ap_validacion": paired["delta_ap"] >= MIN_GAIN,
        "intervalo_sobre_cero": paired["delta_ap_interval_95"][0] > 0,
        "brier_no_empeora": validation["modelo_28"]["brier"] <= validation["modelo_26"]["brier"] + MAX_BRIER_LOSS,
        "ganancia_secciones_no_vistas": cv_section["delta_ap"] >= MIN_GAIN,
        "sensibilidad_dificultad": sensitivity_loss <= MAX_SENSITIVITY_LOSS,
    }
    result = {
        "protocolo": "ml_salud/experimento_contexto/PROTOCOLO.md",
        "variables_nuevas": CONTEXT_FEATURES,
        "contexto": {
            "secciones_en_cohorte": int(df["SECCION_ID"].nunique()),
            "sin_otras_personas_en_seccion": int(df["SECCION_PCT_ENFERMOS"].isna().sum()),
            "otros_enfermos_0": int(df["HOGAR_OTROS_ENFERMOS"].eq(0).sum()),
        },
        "fuentes": source["source_sha256"],
        "cv_viviendas_no_vistas": cv_dwelling, "cv_secciones_no_vistas": cv_section,
        "validacion": validation, "comparacion_pareada": paired,
        "topk_validacion": {"modelo_26": topk(yv, old), "modelo_28": topk(yv, new)},
        "sensibilidad_validacion": subgroups, "criterios": criteria,
        "decision": "adoptar" if all(criteria.values()) else "conservar",
        "prueba_consultada": False,
    }
    out = HERE / "salidas"
    out.mkdir(exist_ok=True)
    write_json(out / "decision.json", result)
    print(json.dumps({"validacion_ap": [validation["modelo_26"]["pr_auc"], validation["modelo_28"]["pr_auc"]],
                      "pareada": paired, "criterios": criteria, "decision": result["decision"]},
                     ensure_ascii=False, default=bool), flush=True)


if __name__ == "__main__":
    main()
