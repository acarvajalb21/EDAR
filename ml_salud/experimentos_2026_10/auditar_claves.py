"""Verifica claves completas en los tres CSV fuente sin modificar archivos."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ml_salud.entrenar import (
    DWELL_FILE, DWELL_KEY, HOUSE_FILE, PERSON_FILE, PERSON_KEY, group_ids,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True, type=Path)
    p.add_argument("--output", type=Path, default=Path(__file__).parent / "salidas" / "claves_fuente.json")
    args = p.parse_args()
    result = {}
    house_source_key = DWELL_KEY + ["H_NROHOG"]
    for file, keys in ((PERSON_FILE, PERSON_KEY), (HOUSE_FILE, house_source_key),
                       (DWELL_FILE, DWELL_KEY)):
        columns = keys + (["P_ENFERMO"] if file == PERSON_FILE else [])
        frame = pd.read_csv(args.data_dir / file, usecols=columns, low_memory=False)
        duplicates = int(frame.duplicated(keys).sum())
        missing = {name: int(frame[name].isna().sum()) for name in keys}
        item = {"rows": len(frame), "duplicate_keys": duplicates,
                "missing_key_values": missing}
        if file == PERSON_FILE:
            sick = frame.P_ENFERMO.eq(1)
            item["sick_rows"] = int(sick.sum())
            item["sick_duplicate_keys"] = int(frame.loc[sick].duplicated(keys).sum())
            item["sick_missing_key_rows"] = int(frame.loc[sick, keys].isna().any(axis=1).sum())
            item["sick_distinct_dwellings_tuple"] = int(len(frame.loc[sick, DWELL_KEY].drop_duplicates()))
            item["sick_distinct_dwellings_group_id"] = int(len(set(group_ids(frame.loc[sick]))))
        result[file] = item
        print(file, item, flush=True)
    assert all(v["duplicate_keys"] == 0 for v in result.values())
    # Hay claves de hogar vacías fuera de la población analítica. La garantía
    # necesaria para el modelo es que ningún caso enfermo las necesite.
    assert result[PERSON_FILE]["sick_missing_key_rows"] == 0
    assert (result[PERSON_FILE]["sick_distinct_dwellings_tuple"] ==
            result[PERSON_FILE]["sick_distinct_dwellings_group_id"])
    assert all(n == 0 for n in result[DWELL_FILE]["missing_key_values"].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
