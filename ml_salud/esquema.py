"""Contrato de entrada bruto compartido por entrenamiento e inferencia."""

from __future__ import annotations

import numpy as np
import pandas as pd

PERSON_SOURCE_FEATURES = [
    "U_MPIO", "UA_CLASE", "P_SEXO", "P_EDADR", "P_PARENTESCOR",
    "PA1_GRP_ETNIC", "CONDICION_FISICA", "P_ALFABETA", "PA_ASISTENCIA",
    "P_NIVEL_ANOSR", "P_TRABAJO", "P_EST_CIVIL",
]
EXCLUDED_TEMPORAL = ["PA_ASISTENCIA", "P_TRABAJO"]
PERSON_FEATURES = [
    column for column in PERSON_SOURCE_FEATURES
    if column not in EXCLUDED_TEMPORAL
]
HOUSE_FEATURES = [
    "H_NRO_CUARTOS", "H_NRO_DORMIT", "H_DONDE_PREPALIM",
    "H_AGUA_COCIN", "HA_TOT_PER",
]
DWELL_FEATURES = [
    "V_TIPO_VIV", "V_MAT_PARED", "V_MAT_PISO", "VA_EE",
    "VA1_ESTRATO", "VB_ACU", "VC_ALC", "VD_GAS", "VE_RECBAS",
    "VF_INTERNET", "V_TIPO_SERSA",
]
FEATURES = PERSON_FEATURES + HOUSE_FEATURES + DWELL_FEATURES
FULL_FEATURES = PERSON_SOURCE_FEATURES + HOUSE_FEATURES + DWELL_FEATURES
NUMERIC = ["P_EDADR", "H_NRO_CUARTOS", "H_NRO_DORMIT", "HA_TOT_PER"]
CATEGORICAL = [column for column in FEATURES if column not in NUMERIC]
SENTINELS = {
    "PA1_GRP_ETNIC": [9], "P_ALFABETA": [9], "PA_ASISTENCIA": [9],
    "P_NIVEL_ANOSR": [99], "P_TRABAJO": [0], "P_EST_CIVIL": [9],
    "H_NRO_CUARTOS": [99], "H_NRO_DORMIT": [99],
    "H_DONDE_PREPALIM": [9], "H_AGUA_COCIN": [99],
    "VA1_ESTRATO": [9], "VD_GAS": [9],
    "VF_INTERNET": [9], "V_TIPO_SERSA": [9],
}
LEAKAGE_COLUMNS = {
    "P_QUEHIZO_PPAL", "PA_LO_ATENDIERON", "PA1_CALIDAD_SERV",
    "ACCESO_FORMAL_SALUD", "ACCESO_SALUD", "P_ENFERMO",
}
VALID_CODES = {
    # Códigos observados en los microdatos del Atlántico usados para entrenar.
    "U_MPIO": {1, 78, 137, 141, 296, 372, 421, 433, 436, 520, 549,
               558, 560, 573, 606, 634, 638, 675, 685, 758, 770, 832, 849},
    "UA_CLASE": {1, 2, 3},
    "P_SEXO": {1, 2},
    "P_PARENTESCOR": {1, 2, 3, 4, 5},
    "PA1_GRP_ETNIC": {1, 2, 3, 4, 5, 6, 9},
    "CONDICION_FISICA": {1, 2},
    "P_ALFABETA": {1, 2, 9},
    "P_NIVEL_ANOSR": set(range(1, 11)) | {99},
    "P_EST_CIVIL": set(range(1, 8)) | {9},
    "H_DONDE_PREPALIM": set(range(1, 7)) | {9},
    "H_AGUA_COCIN": set(range(1, 12)) | {99},
    "V_TIPO_VIV": set(range(1, 7)),
    "V_MAT_PARED": set(range(1, 10)),
    "V_MAT_PISO": set(range(1, 7)),
    "VA_EE": {1, 2},
    "VA1_ESTRATO": set(range(0, 7)) | {9},
    "VB_ACU": {1, 2},
    "VC_ALC": {1, 2},
    "VD_GAS": {1, 2, 9},
    "VE_RECBAS": {1, 2},
    "VF_INTERNET": {1, 2, 9},
    "V_TIPO_SERSA": set(range(1, 7)) | {9},
}


def prepare_features(
    raw: pd.DataFrame, feature_columns: list[str] | None = None
) -> pd.DataFrame:
    """Normaliza códigos censales brutos sin aprender del conjunto."""
    selected = FEATURES if feature_columns is None else feature_columns
    if not isinstance(raw, pd.DataFrame):
        raise TypeError("La entrada debe ser un pandas.DataFrame.")
    if not set(selected).issubset(FULL_FEATURES):
        raise ValueError("La lista de variables contiene columnas desconocidas")
    missing = sorted(set(selected) - set(raw.columns))
    if missing:
        raise ValueError(f"Faltan variables requeridas: {missing}")
    if set(selected) & LEAKAGE_COLUMNS:
        raise AssertionError("Hay una variable de fuga en FEATURES")
    features = raw[selected].copy()
    for column in selected:
        # Convertir antes de aplicar centinelas: Dash puede entregar "9"
        # mientras que el CSV de entrenamiento entrega 9.
        values = pd.to_numeric(features[column], errors="raise")
        if np.isinf(values.to_numpy(dtype=float, na_value=np.nan)).any():
            raise ValueError(f"{column} contiene valores infinitos")
        if (values.notna() & values.mod(1).ne(0)).any():
            raise ValueError(f"{column} requiere códigos enteros")
        features[column] = values
    for column in (name for name in selected if name in VALID_CODES):
        invalid = features[column].notna() & ~features[column].isin(VALID_CODES[column])
        if invalid.any():
            raise ValueError(f"{column} contiene un código no válido para estos datos")
    for column, values in SENTINELS.items():
        if column in features:
            features[column] = features[column].replace(values, np.nan)
    if "P_EDADR" in features and (
        features["P_EDADR"].dropna().lt(1) |
        features["P_EDADR"].dropna().gt(21)
    ).any():
        raise ValueError("P_EDADR debe estar entre 1 y 21")
    for column in ("H_NRO_CUARTOS", "H_NRO_DORMIT", "HA_TOT_PER"):
        if column in features and features[column].dropna().lt(0).any():
            raise ValueError(f"{column} no puede ser negativo")
    for column in (name for name in selected if name not in NUMERIC):
        features[column] = (
            features[column].astype("Int64").astype("string").fillna("__FALTANTE__")
        )
    for column in (name for name in selected if name in NUMERIC):
        features[column] = pd.to_numeric(features[column], errors="raise")
    return features
