"""
Validation experiment runner for UAE rooftop solar pre-feasibility analysis.
Computes statistical error metrics (MAPE, MBE, RMSE, R^2), categorical breakdowns,
and writes tabular results.
"""

import os
import csv
import math
import numpy as np
from typing import Dict, Any, List

def compute_metrics(csv_path: str = "data/validation_buildings.csv") -> Dict[str, Any]:
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    osm_areas = np.array([float(r["osm_area_m2"]) for r in rows])
    ref_areas = np.array([float(r["reference_area_m2"]) for r in rows])
    rel_errors = np.array([float(r["rel_error_pct"]) for r in rows])
    abs_errors = np.array([float(r["abs_error_m2"]) for r in rows])

    n = len(rows)
    mape = np.mean(np.abs(rel_errors))
    mbe = np.mean(rel_errors)
    rmse = np.sqrt(np.mean((osm_areas - ref_areas) ** 2))
    r_matrix = np.corrcoef(ref_areas, osm_areas)
    r2 = r_matrix[0, 1] ** 2

    # Categorical breakdown
    categories = sorted(list(set(r["category"] for r in rows)))
    cat_summary = {}
    for cat in categories:
        cat_rows = [r for r in rows if r["category"] == cat]
        cat_rel = np.array([float(r["rel_error_pct"]) for r in cat_rows])
        cat_summary[cat] = {
            "count": len(cat_rows),
            "mape": float(np.mean(np.abs(cat_rel))),
            "mbe": float(np.mean(cat_rel)),
            "min_err": float(np.min(cat_rel)),
            "max_err": float(np.max(cat_rel))
        }

    # Emirate breakdown
    emirates = sorted(list(set(r["emirate"] for r in rows)))
    em_summary = {}
    for em in emirates:
        em_rows = [r for r in rows if r["emirate"] == em]
        em_rel = np.array([float(r["rel_error_pct"]) for r in em_rows])
        em_summary[em] = {
            "count": len(em_rows),
            "mape": float(np.mean(np.abs(em_rel))),
            "mbe": float(np.mean(em_rel))
        }

    return {
        "n_buildings": n,
        "mape": float(mape),
        "mbe": float(mbe),
        "rmse": float(rmse),
        "r2": float(r2),
        "categorical": cat_summary,
        "emirates": em_summary,
        "rows": rows
    }


def main():
    results = compute_metrics()
    print("=================================================================")
    print("               UAE ROOFTOP VALIDATION BENCHMARK                  ")
    print("=================================================================")
    print(f"Total Buildings Evaluated: {results['n_buildings']}")
    print(f"Mean Absolute Percentage Error (MAPE): {results['mape']:.2f}%")
    print(f"Mean Bias Error (MBE):                {results['mbe']:.2f}%")
    print(f"Root Mean Square Error (RMSE):         {results['rmse']:.2f} m²")
    print(f"Coefficient of Determination (R²):     {results['r2']:.4f}")
    print("\nCategorical Breakdown:")
    print("Category        | Count | MAPE (%) | MBE (%)  | Error Range (%)")
    print("----------------|-------|----------|----------|-------------------")
    for cat, stats in results["categorical"].items():
        print(f"{cat:15} | {stats['count']:5} | {stats['mape']:8.2f} | {stats['mbe']:8.2f} | [{stats['min_err']:+.2f}%, {stats['max_err']:+.2f}%]")
    print("\nEmirate Breakdown:")
    print("Emirate         | Count | MAPE (%) | MBE (%)")
    print("----------------|-------|----------|---------")
    for em, stats in results["emirates"].items():
        print(f"{em:15} | {stats['count']:5} | {stats['mape']:8.2f} | {stats['mbe']:8.2f}")
    print("=================================================================")


if __name__ == "__main__":
    main()
