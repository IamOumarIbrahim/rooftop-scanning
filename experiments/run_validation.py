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
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Validation dataset not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"Validation dataset '{csv_path}' is empty.")

    osm_areas = np.array([float(r["osm_area_m2"]) for r in rows])
    ref_areas = np.array([float(r["reference_area_m2"]) for r in rows])
    rel_errors = np.array([float(r["rel_error_pct"]) for r in rows])
    abs_errors = np.array([float(r["abs_error_m2"]) for r in rows])

    n = len(rows)
    mape = float(np.mean(np.abs(rel_errors)))
    mbe = float(np.mean(rel_errors))
    medape = float(np.median(np.abs(rel_errors)))
    std_err = float(np.std(rel_errors, ddof=1))
    q25, q75 = np.percentile(rel_errors, [25, 75])
    iqr = float(q75 - q25)
    
    # 95% Confidence interval on MBE: t_{0.025, df=n-1} ~ 2.069 for n=24
    t_crit = 2.069 if n >= 20 else 2.262
    ci95_margin = float(t_crit * (std_err / math.sqrt(n)))
    ci95_mbe = (round(mbe - ci95_margin, 2), round(mbe + ci95_margin, 2))

    rmse = float(np.sqrt(np.mean((osm_areas - ref_areas) ** 2)))
    if np.std(ref_areas) > 1e-9 and np.std(osm_areas) > 1e-9:
        r_matrix = np.corrcoef(ref_areas, osm_areas)
        r2 = float(r_matrix[0, 1] ** 2)
    else:
        r2 = 1.0

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
            "medape": float(np.median(np.abs(cat_rel))),
            "std": float(np.std(cat_rel, ddof=1)) if len(cat_rel) > 1 else 0.0,
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
            "mbe": float(np.mean(em_rel)),
            "min_err": float(np.min(em_rel)),
            "max_err": float(np.max(em_rel))
        }

    return {
        "n_buildings": n,
        "mape": round(mape, 4),
        "mbe": round(mbe, 4),
        "medape": round(medape, 4),
        "std_err": round(std_err, 4),
        "q25": round(float(q25), 4),
        "q75": round(float(q75), 4),
        "iqr": round(iqr, 4),
        "ci95_mbe": ci95_mbe,
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
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
