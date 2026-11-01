"""Contexto de salud del hogar y de la sección censal (modelo versión 2).

Las dos variables se calculan con ``P_ENFERMO`` de todas las personas del
archivo censal; nunca con la acción declarada ni con la respuesta del modelo.
Este módulo amplía el contrato de ``esquema.py`` sin modificarlo, porque el
artefacto de la versión 1 guarda la huella de ese archivo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml_salud.esquema import FEATURES, NUMERIC, prepare_features

PERSON_FILE = "CNPV2018_5PER_A2_08.CSV"
MGN_FILE = "CNPV2018_MGN_A2_08.CSV"
DWELL_KEY = ["U_DPTO", "U_MPIO", "UA_CLASE", "COD_ENCUESTAS", "U_VIVIENDA"]
HOUSE_KEY = DWELL_KEY + ["P_NROHOG"]
SECTION_COLUMNS = ["U_MPIO", "UA_CLASE", "U_SECT_RUR", "U_SECC_RUR", "UA2_CPOB", "U_SECT_URB", "U_SECC_URB"]

CONTEXT_FEATURES = ["HOGAR_OTROS_ENFERMOS", "SECCION_PCT_ENFERMOS"]
FEATURES_V2 = FEATURES + CONTEXT_FEATURES
NUMERIC_V2 = NUMERIC + CONTEXT_FEATURES


def add_context(cohort: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """Añade las variables de contexto sin cambiar las filas ni su orden."""
    people = pd.read_csv(data_dir / PERSON_FILE, usecols=HOUSE_KEY + ["P_ENFERMO"], low_memory=False)
    mgn = pd.read_csv(data_dir / MGN_FILE, usecols=list(dict.fromkeys(DWELL_KEY + SECTION_COLUMNS)),
                      dtype={name: "string" for name in SECTION_COLUMNS[2:]}, low_memory=False)
    if mgn.duplicated(DWELL_KEY).any():
        raise AssertionError("El MGN tiene viviendas duplicadas")
    mgn["SECCION_ID"] = mgn[SECTION_COLUMNS].astype("string").agg("|".join, axis=1)
    people = people.merge(mgn[DWELL_KEY + ["SECCION_ID"]], on=DWELL_KEY, how="left", validate="many_to_one")
    if people["SECCION_ID"].isna().any():
        raise AssertionError("Hay personas sin sección censal")
    # 9 y los blancos no cuentan en el denominador: no informan sobre el problema de salud.
    people["valido"] = people["P_ENFERMO"].isin([1, 2]).astype("int32")
    people["enfermo"] = people["P_ENFERMO"].eq(1).astype("int32")
    household = people.groupby(HOUSE_KEY, sort=False)[["valido", "enfermo"]].sum().reset_index().rename(
        columns={"valido": "hogar_validos", "enfermo": "hogar_enfermos"})
    section = people.groupby("SECCION_ID", sort=False)[["valido", "enfermo"]].sum().reset_index().rename(
        columns={"valido": "seccion_validos", "enfermo": "seccion_enfermos"})
    n = len(cohort)
    enriched = (cohort.merge(household, on=HOUSE_KEY, how="left", validate="many_to_one")
                .merge(mgn[DWELL_KEY + ["SECCION_ID"]], on=DWELL_KEY, how="left", validate="many_to_one")
                .merge(section, on="SECCION_ID", how="left", validate="many_to_one"))
    if len(enriched) != n or enriched["hogar_enfermos"].isna().any() or enriched["seccion_enfermos"].isna().any():
        raise AssertionError("El contexto no enlazó con toda la cohorte")
    # Toda persona de la cohorte tiene P_ENFERMO=1: se descuenta a sí misma.
    enriched["HOGAR_OTROS_ENFERMOS"] = enriched["hogar_enfermos"] - 1
    # La sección excluye al hogar completo para no contar dos veces lo mismo.
    outside = enriched["seccion_validos"] - enriched["hogar_validos"]
    enriched["SECCION_PCT_ENFERMOS"] = (
        (enriched["seccion_enfermos"] - enriched["hogar_enfermos"]) / outside.where(outside > 0)
    )
    return enriched.drop(columns=["hogar_validos", "hogar_enfermos", "seccion_validos", "seccion_enfermos"])


def prepare_features_v2(raw: pd.DataFrame) -> pd.DataFrame:
    """Valida los 26 códigos censales y las dos variables de contexto."""
    missing = sorted(set(CONTEXT_FEATURES) - set(raw.columns))
    if missing:
        raise ValueError(f"Faltan variables requeridas: {missing}")
    prepared = prepare_features(raw, FEATURES)
    others = pd.to_numeric(raw["HOGAR_OTROS_ENFERMOS"], errors="raise").astype(float)
    if others.isna().any() or others.lt(0).any() or others.mod(1).ne(0).any():
        raise ValueError("HOGAR_OTROS_ENFERMOS debe ser un entero no negativo")
    share = pd.to_numeric(raw["SECCION_PCT_ENFERMOS"], errors="raise").astype(float)
    if np.isinf(share.to_numpy()).any() or (share.notna() & ~share.between(0, 1)).any():
        raise ValueError("SECCION_PCT_ENFERMOS debe estar entre 0 y 1")
    return prepared.assign(HOGAR_OTROS_ENFERMOS=others, SECCION_PCT_ENFERMOS=share)
