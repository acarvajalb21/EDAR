"""Transformación determinista de entradas brutas para candidatos auditados."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.base import BaseEstimator, TransformerMixin

from ml_salud.esquema import CATEGORICAL, NUMERIC, SENTINELS, prepare_features


def feature_frame(df: pd.DataFrame, *, distinct_missing=False, density=False,
                  age_category=False):
    x = prepare_features(df)
    if distinct_missing:
        for col in CATEGORICAL:
            if col in SENTINELS:
                explicit = df[col].isin(SENTINELS[col]).to_numpy()
                x.loc[explicit, col] = "__NO_INFORMA_EXPLICITO__"
    cats = CATEGORICAL.copy()
    nums = NUMERIC.copy()
    if age_category:
        x["P_EDADR"] = x["P_EDADR"].astype("Int64").astype("string").fillna("__FALTANTE__")
        cats.append("P_EDADR")
        nums.remove("P_EDADR")
    if density:
        denominator = pd.to_numeric(x["H_NRO_DORMIT"], errors="coerce")
        numerator = pd.to_numeric(x["HA_TOT_PER"], errors="coerce")
        x["PERSONAS_POR_DORMITORIO"] = (numerator / denominator.where(denominator.gt(0))).replace(
            [np.inf, -np.inf], np.nan
        )
        nums.append("PERSONAS_POR_DORMITORIO")
    return x, cats, nums


class FeatureBuilder(BaseEstimator, TransformerMixin):
    """Prepara códigos censales brutos sin aprender parámetros de la muestra."""

    def __init__(self, distinct_missing=False, density=False, age_category=False):
        self.distinct_missing = distinct_missing
        self.density = density
        self.age_category = age_category

    def fit(self, x, y=None):
        return self

    def transform(self, x):
        return feature_frame(x, distinct_missing=self.distinct_missing,
                             density=self.density, age_category=self.age_category)[0]


class CandidatePredictor:
    """Un único predict_proba para entrada bruta y calibración opcional."""

    def __init__(self, pipeline, calibrator=None):
        self.pipeline = pipeline
        self.calibrator = calibrator

    def predict_proba(self, raw):
        p = self.pipeline.predict_proba(raw)[:, 1]
        if self.calibrator is not None:
            p = self.calibrator.predict_proba(
                logit(np.clip(p, 1e-6, 1 - 1e-6)).reshape(-1, 1)
            )[:, 1]
        return np.column_stack([1 - p, p])


class WeightedEnsemble:
    """Mezcla fija de dos pipelines ajustados sobre las mismas entradas preparadas."""

    def __init__(self, first, second, first_weight=0.75):
        self.first = first
        self.second = second
        self.first_weight = first_weight

    def predict_proba(self, x):
        p = (self.first_weight * self.first.predict_proba(x)[:, 1] +
             (1 - self.first_weight) * self.second.predict_proba(x)[:, 1])
        return np.column_stack([1 - p, p])
