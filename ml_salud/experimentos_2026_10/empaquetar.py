"""Añade preparación de códigos brutos al artefacto de un experimento anterior."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
from sklearn.pipeline import Pipeline

from ml_salud.experimentos_2026_10.preprocesamiento import CandidatePredictor, FeatureBuilder
from ml_salud.pruebas import ejemplo_bruto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=Path(__file__).parent / "salidas" / "candidato_separado.joblib")
    args = parser.parse_args()
    artifact = joblib.load(args.artifact)
    if "predictor" in artifact:
        print("El artefacto ya contiene el preprocesamiento bruto")
        return
    spec = artifact["selected_spec"]
    builder = FeatureBuilder(spec["distinct_missing"], spec["density"], spec["age_category"])
    raw_pipeline = Pipeline([("normalizar_entrada", builder),
                             ("clasificador", artifact.pop("model"))])
    predictor = CandidatePredictor(raw_pipeline, artifact["calibrator"])
    sample = ejemplo_bruto()
    prepared = builder.transform(sample)
    expected = raw_pipeline["clasificador"].predict_proba(prepared)[:, 1]
    if artifact["calibrator"] is None:
        np.testing.assert_allclose(predictor.predict_proba(sample)[:, 1], expected, atol=1e-12)
    artifact["predictor"] = predictor
    joblib.dump(artifact, args.artifact, compress=3)
    check = joblib.load(args.artifact)
    np.testing.assert_allclose(check["predictor"].predict_proba(sample),
                               predictor.predict_proba(sample), atol=1e-12)
    print("Artefacto completo verificado:", args.artifact)


if __name__ == "__main__":
    main()
