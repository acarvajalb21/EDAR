"""Pruebas de contrato para la inferencia con códigos censales brutos."""

import unittest
import hashlib
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_salud.esquema import FEATURES, prepare_features


def ejemplo_bruto():
    row = {column: 1 for column in FEATURES}
    row.update({
        "P_EDADR": 12, "H_NRO_CUARTOS": 3,
        "H_NRO_DORMIT": 2, "HA_TOT_PER": 4,
    })
    return pd.DataFrame([row])


class ContratoInferencia(unittest.TestCase):
    def test_codigos_de_no_respuesta_como_texto(self):
        raw = ejemplo_bruto()
        raw["P_EST_CIVIL"] = "9"
        raw["H_DONDE_PREPALIM"] = "9"
        raw["H_NRO_CUARTOS"] = "99"
        prepared = prepare_features(raw)
        self.assertEqual(prepared.loc[0, "P_EST_CIVIL"], "__FALTANTE__")
        self.assertEqual(prepared.loc[0, "H_DONDE_PREPALIM"], "__FALTANTE__")
        self.assertTrue(np.isnan(prepared.loc[0, "H_NRO_CUARTOS"]))

    def test_entrada_incompleta_o_invalida(self):
        raw = ejemplo_bruto()
        with self.assertRaisesRegex(ValueError, "Faltan variables"):
            prepare_features(raw.drop(columns="P_SEXO"))
        raw.loc[0, "P_EDADR"] = 22
        with self.assertRaisesRegex(ValueError, "P_EDADR"):
            prepare_features(raw)
        raw = ejemplo_bruto()
        raw.loc[0, "U_MPIO"] = 999
        with self.assertRaisesRegex(ValueError, "U_MPIO"):
            prepare_features(raw)

    def test_modelo_guardado_acepta_entrada_bruta(self):
        artifact_path = Path(__file__).parent / "resultados" / "modelo_sin_acceso.joblib"
        if not artifact_path.is_file():
            self.skipTest("El modelo todavía no se ha entrenado")
        artifact = joblib.load(artifact_path)
        schema_path = Path(__file__).parent / "esquema.py"
        schema_hash = hashlib.sha256(schema_path.read_bytes()).hexdigest()
        self.assertEqual(artifact["schema_sha256"], schema_hash)
        raw = ejemplo_bruto()
        score = artifact["pipeline"].predict_proba(raw)[:, 1]
        self.assertEqual(score.shape, (1,))
        self.assertTrue(0 <= score[0] <= 1)
        expected = artifact["pipeline"]["clasificador"].predict_proba(
            prepare_features(raw)
        )[:, 1]
        np.testing.assert_allclose(score, expected, rtol=0, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
