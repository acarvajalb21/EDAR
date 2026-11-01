"""Pruebas de contrato para la inferencia con códigos censales brutos."""

import unittest
import hashlib
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_salud.contexto import (
    CONTEXT_FEATURES, FEATURES_V2, MGN_FILE, PERSON_FILE, add_context, prepare_features_v2,
)
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

    def test_modelo_v1_archivado_acepta_entrada_bruta(self):
        artifact_path = Path(__file__).parent / "resultados_v1" / "modelo_sin_acceso.joblib"
        if not artifact_path.is_file():
            self.skipTest("El modelo archivado no está disponible")
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


class ContratoContexto(unittest.TestCase):
    def ejemplo(self):
        return ejemplo_bruto().assign(HOGAR_OTROS_ENFERMOS=1, SECCION_PCT_ENFERMOS=0.06)

    def test_contexto_invalido_o_ausente(self):
        with self.assertRaisesRegex(ValueError, "Faltan variables"):
            prepare_features_v2(ejemplo_bruto())
        with self.assertRaisesRegex(ValueError, "HOGAR_OTROS_ENFERMOS"):
            prepare_features_v2(self.ejemplo().assign(HOGAR_OTROS_ENFERMOS=1.5))
        with self.assertRaisesRegex(ValueError, "SECCION_PCT_ENFERMOS"):
            prepare_features_v2(self.ejemplo().assign(SECCION_PCT_ENFERMOS=1.2))

    def test_seccion_vacia_se_conserva_como_faltante(self):
        prepared = prepare_features_v2(self.ejemplo().assign(SECCION_PCT_ENFERMOS=np.nan))
        self.assertTrue(np.isnan(prepared.loc[0, "SECCION_PCT_ENFERMOS"]))
        self.assertEqual(list(prepared.columns), FEATURES_V2)

    def test_contexto_excluye_a_la_persona_y_a_su_hogar(self):
        clave = {"U_DPTO": 8, "U_MPIO": 1, "UA_CLASE": 1, "COD_ENCUESTAS": 1, "P_NROHOG": 1}
        personas = pd.DataFrame([
            {**clave, "U_VIVIENDA": 1, "P_ENFERMO": 1},
            {**clave, "U_VIVIENDA": 1, "P_ENFERMO": 1},
            {**clave, "U_VIVIENDA": 1, "P_ENFERMO": 2},
            {**clave, "U_VIVIENDA": 2, "P_ENFERMO": 1},
            {**clave, "U_VIVIENDA": 2, "P_ENFERMO": 2},
            {**clave, "U_VIVIENDA": 2, "P_ENFERMO": 2},
            {**clave, "U_VIVIENDA": 2, "P_ENFERMO": 2},
            {**clave, "U_VIVIENDA": 2, "P_ENFERMO": 9},
        ])
        mgn = pd.DataFrame([{**{k: v for k, v in clave.items() if k != "P_NROHOG"}, "U_VIVIENDA": vivienda,
                             "U_SECT_RUR": "0", "U_SECC_RUR": "0", "UA2_CPOB": "0",
                             "U_SECT_URB": "1", "U_SECC_URB": "1"} for vivienda in (1, 2)])
        with tempfile.TemporaryDirectory() as folder:
            personas.to_csv(Path(folder) / PERSON_FILE, index=False)
            mgn.to_csv(Path(folder) / MGN_FILE, index=False)
            cohorte = pd.DataFrame([{**clave, "U_VIVIENDA": 1, "P_NRO_PER": 1}])
            enriquecida = add_context(cohorte, Path(folder))
        self.assertEqual(enriquecida.loc[0, "HOGAR_OTROS_ENFERMOS"], 1)
        # Fuera del hogar hay 1 enfermo entre 4 respuestas válidas: el 9 no cuenta.
        self.assertAlmostEqual(enriquecida.loc[0, "SECCION_PCT_ENFERMOS"], 0.25)

    def test_modelo_vigente_acepta_entrada_bruta(self):
        artifact_path = Path(__file__).parent / "resultados" / "modelo_sin_acceso.joblib"
        if not artifact_path.is_file():
            self.skipTest("El modelo todavía no se ha entrenado")
        artifact = joblib.load(artifact_path)
        for field, name in (("schema_sha256", "esquema.py"), ("context_sha256", "contexto.py")):
            content = (Path(__file__).parent / name).read_bytes()
            self.assertEqual(artifact[field], hashlib.sha256(content).hexdigest())
        self.assertEqual(artifact["features"], FEATURES + CONTEXT_FEATURES)
        raw = self.ejemplo()
        score = artifact["pipeline"].predict_proba(raw)[:, 1]
        self.assertTrue(0 <= score[0] <= 1)
        expected = artifact["pipeline"]["clasificador"].predict_proba(
            prepare_features_v2(raw)
        )[:, 1]
        np.testing.assert_allclose(score, expected, rtol=0, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
