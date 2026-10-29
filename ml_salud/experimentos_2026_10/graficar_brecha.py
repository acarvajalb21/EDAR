"""Figura descriptiva de sensibilidad por edad y dificultad funcional."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    out = Path(__file__).parent / "salidas"
    data = json.loads((out / "brecha_dificultad.json").read_text(encoding="utf-8"))
    bands = ["0-14", "15-59", "60+"]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    colors = {1: "#0c6478", 2: "#b56a32"}
    for code, offset, label in ((1, -0.14, "Con dificultad"), (2, 0.14, "Sin dificultad")):
        rows = [next(row for row in data["rows"] if row["age_band"] == band and
                     row["difficulty_code"] == code) for band in bands]
        values = np.array([row["recall"] for row in rows])
        lower = values - np.array([row["recall_wilson_95"][0] for row in rows])
        upper = np.array([row["recall_wilson_95"][1] for row in rows]) - values
        ax.errorbar(np.arange(3) + offset, values, yerr=[lower, upper], fmt="o-",
                    capsize=4, color=colors[code], label=label)
        for i, row in enumerate(rows):
            ax.annotate(f"{row['true_positives']}/{row['positives']}",
                        (i + offset, values[i]), xytext=(0, 10 if code == 1 else -19),
                        textcoords="offset points", ha="center", fontsize=8)
    ax.set_xticks(range(3), bands)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Edad en años")
    ax.set_ylabel("Sensibilidad en positivos de SIN_ACCESO")
    ax.set_title("Sensibilidad por edad y dificultad funcional declarada")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "brecha_dificultad.png", dpi=170)
    plt.close(fig)
    print(out / "brecha_dificultad.png")


if __name__ == "__main__":
    main()
