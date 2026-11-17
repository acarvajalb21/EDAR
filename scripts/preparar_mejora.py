"""Resume el experimento de mejora de noviembre de 2026 en cuadros para el libro, Dash y Shiny.

No usa microdatos: lee ml_salud/experimento_mejora/salidas/. Ejecutar desde bookdown_salud/:
    python scripts/preparar_mejora.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

LIBRO = Path(__file__).resolve().parents[1]
SALIDAS = LIBRO / "ml_salud" / "experimento_mejora" / "salidas"

# Etiqueta legible de cada familia de variables y algoritmo.
FAMILIAS = {
    "F0_v2": "Mismas 28 variables del modelo actual",
    "F1_v2+TE_seccion": "+ respuestas de los vecinos de la sección",
    "F2_v2+TE_seccion+TE_manzana": "+ respuestas de los vecinos de la sección y la manzana",
    "F3_F2+agregados": "+ respuestas de los vecinos y perfil de la sección",
    "F4_v2+agregados_sin_etiqueta": "+ perfil de la sección (sin respuestas de vecinos)",
}
USA_VECINOS = {"F1_v2+TE_seccion", "F2_v2+TE_seccion+TE_manzana", "F3_F2+agregados"}


def leer(nombre: str) -> dict:
    return json.loads((SALIDAS / nombre).read_text(encoding="utf-8"))


def escribir(nombre: str, filas: list[dict]) -> None:
    with (LIBRO / "data" / nombre).open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def main() -> None:
    val = leer("validacion.json")
    seccion = leer("cv_seccion.json")["cv_por_seccion"]
    seccion.update(leer("cv_seccion_complemento.json")["cv_por_seccion"])
    filas = []
    for clave, r in val["tabla"].items():
        if clave == "prevalencia":
            continue
        familia, modelo = clave.split("|")
        filas.append({
            "clave": clave, "variables": FAMILIAS[familia],
            "algoritmo": "LightGBM" if modelo.startswith("lgb") else "Boosting de histogramas",
            "usa_respuestas_vecinos": familia in USA_VECINOS,
            "es_referencia": clave == val["referencia"], "es_candidato": clave == val["candidato"],
            "ap_cv": r["ap_cv_media"], "ap_validacion": r["ap_val"], "roc_auc_validacion": r["roc_auc_val"],
            "brier_validacion": r["brier_val"],
            "ap_secciones_no_vistas": seccion.get(clave, {}).get("ap_media", ""),
        })
    escribir("experimento_mejora.csv", filas)

    b = val["bootstrap_pareado"]
    ref, cand = val["umbrales"][val["referencia"]], val["umbrales"][val["candidato"]]
    resumen = {
        "prevalencia_ap": val["tabla"]["prevalencia"]["ap_val"],
        "delta_ap": b["delta_ap"], "delta_ap_inf": b["ic95_delta_ap"][0], "delta_ap_sup": b["ic95_delta_ap"][1],
        "replicas": b["replicas_validas"], "viviendas": b["unidades_remuestreadas"],
        "ap_seccion_v2": seccion[val["referencia"]]["ap_media"], "ap_seccion_candidato": seccion[val["candidato"]]["ap_media"],
        "exactitud_bal_v2": ref["umbral_f1_validacion"]["balanced_accuracy"],
        "exactitud_bal_candidato": cand["umbral_f1_validacion"]["balanced_accuracy"],
        "ap_lightgbm_mismas": next(f["ap_validacion"] for f in filas if f["variables"] == FAMILIAS["F0_v2"] and f["algoritmo"] == "LightGBM"),
        "ap_v2": next(f["ap_validacion"] for f in filas if f["es_referencia"]),
        "ap_candidato": next(f["ap_validacion"] for f in filas if f["es_candidato"]),
    }
    escribir("experimento_mejora_resumen.csv", [resumen])
    print(f"experimento_mejora.csv: {len(filas)} filas; resumen escrito")


if __name__ == "__main__":
    main()
