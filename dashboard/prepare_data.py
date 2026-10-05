"""Genera únicamente tablas agregadas para el dashboard público.

Uso:
    python dashboard/prepare_data.py --input ruta/base_analitica_acceso_salud.csv

El CSV de entrada contiene una fila por persona y nunca debe subirse a GitHub.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent / "data"
GEO_PATH = ROOT / "datos" / "mgn2018_municipios_atlantico.geojson"
MIN_GROUP = 30

DIMENSIONS = {
    "sexo": "SEXO",
    "dificultad": "DIFICULTAD",
    "zona": "ZONA",
    "edad": "EDAD_TRAMO",
    "estrato": "ESTRATO",
    "educacion": "NIVEL_EDUCATIVO",
}


def aggregate(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return (
        frame.groupby(columns, dropna=False, observed=True)
        .agg(n=("ACCESO_FORMAL_SALUD", "size"), accedieron=("ACCESO_FORMAL_SALUD", "sum"))
        .reset_index()
    )


def build(input_path: Path, output_dir: Path = OUTPUT) -> None:
    if not input_path.is_file():
        raise FileNotFoundError(f"Falta la base analítica: {input_path}")

    columns = [
        "U_MPIO", "MUNICIPIO", "ACCESO_FORMAL_SALUD", "SEXO", "DIFICULTAD",
        "ZONA", "P_EDADR", "ESTRATO", "NIVEL_EDUCATIVO",
    ]
    df = pd.read_csv(input_path, usecols=columns, dtype={"U_MPIO": "string"})
    df["U_MPIO"] = df["U_MPIO"].str.zfill(3)
    df["ACCESO_FORMAL_SALUD"] = pd.to_numeric(
        df["ACCESO_FORMAL_SALUD"], errors="raise"
    ).astype("int8")
    if not df["ACCESO_FORMAL_SALUD"].isin([0, 1]).all():
        raise ValueError("La respuesta debe estar codificada como 0 o 1.")

    df["EDAD_TRAMO"] = pd.cut(
        pd.to_numeric(df["P_EDADR"], errors="raise"),
        bins=[0, 4, 8, 12, 16, 21],
        labels=["0–19", "20–39", "40–59", "60–79", "80 o más"],
    ).astype("string")
    if df["EDAD_TRAMO"].isna().any():
        raise ValueError("Hay códigos de edad fuera de los grupos quinquenales esperados.")

    for column in DIMENSIONS.values():
        df[column] = df[column].astype("string").fillna("Sin dato")

    with GEO_PATH.open(encoding="utf-8") as file:
        geo = json.load(file)
    geo_codes = {f["properties"]["MPIO_CCDGO"] for f in geo["features"]}
    data_codes = set(df["U_MPIO"].unique())
    if len(geo_codes) != 23 or data_codes != geo_codes:
        raise ValueError("Los municipios de la base no coinciden con los 23 del mapa.")

    municipal = aggregate(df, ["U_MPIO", "MUNICIPIO"]).rename(
        columns={"U_MPIO": "codigo", "MUNICIPIO": "municipio"}
    )
    municipal = municipal.sort_values("municipio")

    breakdown_parts = []
    for variable, column in DIMENSIONS.items():
        department = aggregate(df, [column]).rename(columns={column: "categoria"})
        department.insert(0, "codigo", "DEP")
        department.insert(1, "variable", variable)

        by_municipality = aggregate(df, ["U_MPIO", column]).rename(
            columns={"U_MPIO": "codigo", column: "categoria"}
        )
        by_municipality = by_municipality.loc[by_municipality["n"] >= MIN_GROUP].copy()
        by_municipality.insert(1, "variable", variable)
        breakdown_parts.extend([department, by_municipality])

    breakdowns = pd.concat(breakdown_parts, ignore_index=True)
    breakdowns = breakdowns[["codigo", "variable", "categoria", "n", "accedieron"]]

    age_difficulty = aggregate(df, ["U_MPIO", "EDAD_TRAMO", "DIFICULTAD"]).rename(
        columns={
            "U_MPIO": "codigo", "EDAD_TRAMO": "edad", "DIFICULTAD": "dificultad"
        }
    )
    age_difficulty = age_difficulty.loc[age_difficulty["n"] >= MIN_GROUP].copy()
    department_age = aggregate(df, ["EDAD_TRAMO", "DIFICULTAD"]).rename(
        columns={"EDAD_TRAMO": "edad", "DIFICULTAD": "dificultad"}
    )
    department_age.insert(0, "codigo", "DEP")
    age_difficulty = pd.concat([department_age, age_difficulty], ignore_index=True)

    total = int(df.shape[0])
    accessed = int(df["ACCESO_FORMAL_SALUD"].sum())
    if total != 136_034 or accessed != 107_384:
        raise ValueError(
            f"Cifras distintas al EDA validado: n={total}, accedieron={accessed}."
        )
    if int(municipal["n"].sum()) != total:
        raise ValueError("El resumen municipal no reconcilia con la base.")

    output_dir.mkdir(parents=True, exist_ok=True)
    municipal.to_csv(output_dir / "municipios.csv", index=False, encoding="utf-8")
    breakdowns.to_csv(output_dir / "desgloses.csv", index=False, encoding="utf-8")
    age_difficulty.to_csv(output_dir / "edad_dificultad.csv", index=False, encoding="utf-8")
    (output_dir / "metadata.json").write_text(
        json.dumps(
            {
                "year": 2018,
                "department": "Atlántico",
                "population": total,
                "accessed": accessed,
                "municipalities": len(municipal),
                "minimum_published_group": MIN_GROUP,
                "source": "DANE, CNPV 2018; base analítica del EDA en R",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Agregados generados: {total:,} personas, {len(municipal)} municipios.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="CSV analítico local, no público")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.input, args.output)
