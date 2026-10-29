"""Comprobaciones de contrato de las transformaciones y del artefacto nuevo."""

import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_salud.esquema import FEATURES
from ml_salud.experimentos_2026_10.ejecutar import topk
from ml_salud.experimentos_2026_10.preprocesamiento import FeatureBuilder
from ml_salud.pruebas import ejemplo_bruto


class ExperimentoContrato(unittest.TestCase):
    def test_faltante_explicito_y_blanco_se_distinguen(self):
        raw = pd.concat([ejemplo_bruto(), ejemplo_bruto()], ignore_index=True)
        raw.loc[0, "P_EST_CIVIL"] = 9
        raw.loc[1, "P_EST_CIVIL"] = np.nan
        prepared = FeatureBuilder(distinct_missing=True).transform(raw)
        self.assertEqual(prepared.loc[0, "P_EST_CIVIL"], "__NO_INFORMA_EXPLICITO__")
        self.assertEqual(prepared.loc[1, "P_EST_CIVIL"], "__FALTANTE__")

    def test_densidad_no_divide_por_cero(self):
        raw = ejemplo_bruto()
        raw.loc[0, "H_NRO_DORMIT"] = 0
        prepared = FeatureBuilder(density=True).transform(raw)
        self.assertTrue(np.isnan(prepared.loc[0, "PERSONAS_POR_DORMITORIO"]))

    def test_topk_resuelve_empates_por_orden_original(self):
        result = topk(np.array([1, 0, 0, 1]), np.array([0.5, 0.5, 0.2, 0.1]), (0.25,))
        self.assertEqual(result["25pct"]["reviewed"], 1)
        self.assertEqual(result["25pct"]["positives_found"], 1)

    def test_artefacto_acepta_codigos_brutos(self):
        path = Path(__file__).parent / "salidas" / "candidato_separado.joblib"
        if not path.is_file():
            self.skipTest("Ejecute el experimento antes de probar el artefacto")
        artifact = joblib.load(path)
        self.assertEqual(artifact["features"], FEATURES)
        raw = ejemplo_bruto()
        score = artifact["predictor"].predict_proba(raw)
        self.assertEqual(score.shape, (1, 2))
        self.assertAlmostEqual(float(score.sum()), 1.0)
        self.assertTrue(np.isfinite(score).all())


if __name__ == "__main__":
    unittest.main()
