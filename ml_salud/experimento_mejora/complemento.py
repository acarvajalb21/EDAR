"""Complemento exploratorio (decidido después de ver validación): CV por sección de F4.

F4 usa solo agregados sin etiqueta, disponibles también en secciones sin etiquetas.
Uso (desde proyecto_salud/):
    ml_salud\\.venv\\Scripts\\python.exe -m ml_salud.experimento_mejora.complemento --data-dir datos
No consulta la prueba.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold

from ml_salud.contexto import FEATURES_V2, prepare_features_v2
from ml_salud.entrenar import group_ids, load_data, split_three
from ml_salud.experimento_mejora.ejecutar import (
    FEATURE_SETS, GRID, SEED_CV, build, cfg_name, fit_hgb, fit_lgb_staged, territorial_aggregates, write_json,
)

VARIANTS = ["F4_v2+agregados_sin_etiqueta|hgb_v2_params", "F4_v2+agregados_sin_etiqueta|lgb_nl63_lr0.02_mc100_cwNone_n700"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    t0 = time.time()
    df, _ = load_data(args.data_dir, with_context=True)
    x = prepare_features_v2(df)[FEATURES_V2]
    y = df["SIN_ACCESO"].to_numpy()
    groups = group_ids(df)
    train, _val, _test = split_three(x, y, groups)
    agg, _ = territorial_aggregates(df, args.data_dir)
    sections = df["SECCION_ID"].to_numpy()
    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED_CV)
    sfolds = [(train[a], train[b]) for a, b in cv.split(x.iloc[train], y[train], sections[train])]
    res = {}
    for name in VARIANTS:
        fs, model = name.split("|")
        cols = FEATURE_SETS[fs]
        aps = []
        for tr, va in sfolds:
            xf, xe = build(x, agg, tr, va, y, {}, None, cols)
            if model == "hgb_v2_params":
                s = fit_hgb(xf, y[tr], xe, cols)
            else:
                p = next(p for p in GRID if cfg_name(p, 0).rsplit("_n", 1)[0] == model.rsplit("_n", 1)[0])
                n = int(model.rsplit("_n", 1)[1])
                s = fit_lgb_staged(xf, y[tr], xe, p, (n,))[n]
            aps.append(float(average_precision_score(y[va], s)))
        res[name] = {"ap_pliegues": aps, "ap_media": float(np.mean(aps)), "ap_de": float(np.std(aps, ddof=1))}
        print(name, res[name], flush=True)
    write_json("cv_seccion_complemento.json", {
        "nota": "Exploratorio, decidido tras ver la validación; mismos pliegues por sección que cv_seccion.json.",
        "cv_por_seccion": res, "tiempo_s": time.time() - t0, "prueba_consultada": False})


if __name__ == "__main__":
    main()
