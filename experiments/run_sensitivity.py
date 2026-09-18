"""
Sensitivity analysis for UAE rooftop solar pre-feasibility modeling.
Investigates:
1. Impact of setback distance (0.0 to 3.0 m) on usable area fraction across building scales.
2. Impact of tilt angle (0 to 45 deg) and azimuth (0 to 360 deg) on annual yield.
3. Impact of electricity tariff (0.25 to 0.50 AED/kWh) and installed cost ($800 to $1400/kW) on simple payback.
"""

import numpy as np
from typing import Dict, Any
from solarscan.geometry import calculate_usable_area
from solarscan.yield_estimate import calculate_orientation_derate, estimate_annual_yield, estimate_simple_payback


def run_setback_sensitivity() -> Dict[str, Any]:
    """
    Evaluates usable area ratio A_usable / A_raw as a function of setback distance s
    for three representative building typologies:
    - Small Residential Villa (A = 150 m2, P = 52 m)
    - Medium Institutional Building (UoS W5: A = 1,610 m2, P = 165.4 m)
    - Large Commercial Facility (A = 36,000 m2, P = 837 m)
    """
    setbacks = np.linspace(0.0, 3.0, 13)  # 0.0 to 3.0 m in 0.25 m steps
    
    cases = {
        "residential": {"name": "Residential Villa (150 m²)", "area": 150.0, "p": 52.0},
        "institutional": {"name": "Institutional Complex (1,610 m²)", "area": 1610.02, "p": 165.4},
        "commercial": {"name": "Commercial Center (36,000 m²)", "area": 36155.41, "p": 837.33}
    }
    
    results = {"setbacks": setbacks.tolist()}
    for key, c in cases.items():
        usable_fractions = []
        pa_ratio = round(c["p"] / c["area"], 4)
        for s in setbacks:
            u = calculate_usable_area(c["area"], c["p"], s, obstruction_area=0.0)
            usable_fractions.append(round(u / c["area"], 4))
        results[key] = {
            "name": c["name"],
            "area": c["area"],
            "perimeter": c["p"],
            "pa_ratio": pa_ratio,
            "usable_fractions": usable_fractions
        }
    return results


def run_orientation_sensitivity() -> Dict[str, Any]:
    """
    Evaluates annual generation (kWh/kWp) across azimuths [0, 360) and tilts [0, 40].
    """
    azimuths = np.arange(0, 361, 15)  # 0 to 360 deg in 15 deg steps
    tilts = [0, 10, 15, 20, 25, 30]    # standard racking tilts
    
    matrix = {}
    for t in tilts:
        yields = []
        for az in azimuths:
            derate = calculate_orientation_derate(float(az), float(t))
            kwh_per_kw = estimate_annual_yield(
                1.0, tilt_deg=float(t), azimuth_deg=float(az),
                peak_sun_hours_per_day=5.5, system_loss_factor=0.85
            )
            yields.append(round(kwh_per_kw, 2))
        matrix[t] = yields
        
    return {
        "azimuths": azimuths.tolist(),
        "tilts": tilts,
        "yields": matrix
    }


def run_economic_sensitivity() -> Dict[str, Any]:
    """
    Evaluates simple payback period as a function of electricity tariff and CAPEX.
    Assumes standard UAE system producing 1,706 kWh/kWp/year.
    """
    tariffs = [0.28, 0.33, 0.38, 0.43, 0.48]  # AED/kWh (commercial/industrial tiers)
    capex_costs = [800.0, 1000.0, 1200.0, 1400.0]  # USD/kW (or AED converted)
    
    payback_table = {}
    annual_kwh_per_kw = 1706.38  # 1 kW DC output
    for c in capex_costs:
        payback_table[c] = []
        for rate in tariffs:
            # simple payback: capex / (annual_kwh * rate)
            pb = estimate_simple_payback(annual_kwh_per_kw, rate, cost_per_kw=c, dc_capacity_kw=1.0)
            payback_table[c].append(round(pb, 2))
            
    return {
        "tariffs": tariffs,
        "capex_costs": capex_costs,
        "payback_table": payback_table
    }


def run_degradation_sensitivity(
    initial_kwh: float = 260330.0,
    lifetime_years: int = 25
) -> Dict[str, Any]:
    """
    Evaluates cumulative 25-year energy generation under varying annual PV degradation rates
    ranging from 0.3%/yr (premium heterojunction / TOPCon) to 1.0%/yr (standard multicrystalline).
    """
    degradation_rates = [0.003, 0.005, 0.007, 0.010]
    lifetime_totals = {}
    for deg in degradation_rates:
        cum_gen = sum(initial_kwh * ((1.0 - deg) ** t) for t in range(lifetime_years))
        lifetime_totals[deg] = round(cum_gen / 1000.0, 2)  # MWh
    return {
        "degradation_rates": degradation_rates,
        "lifetime_mwh": lifetime_totals
    }


def run_monte_carlo_uncertainty(
    dc_capacity_kw: float = 272.38,
    n_iterations: int = 1000,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Performs Monte Carlo uncertainty propagation over solar pre-feasibility modeling.
    Stochastically samples:
    - Peak Sun Hours: Normal(mu=5.5, sigma=0.25)
    - System Loss / Performance Ratio: Normal(mu=0.85, sigma=0.03)
    - Electricity Tariff: Uniform(0.35, 0.42)
    - Turnkey Cost: Normal(mu=1000, sigma=60)
    """
    np.random.seed(random_seed)
    psh_samples = np.random.normal(5.50, 0.25, n_iterations)
    pr_samples = np.clip(np.random.normal(0.85, 0.03, n_iterations), 0.70, 0.95)
    tariff_samples = np.random.uniform(0.35, 0.42, n_iterations)
    cost_samples = np.clip(np.random.normal(1000.0, 60.0, n_iterations), 800.0, 1300.0)

    # Fixed orientation factor for UoS W5 case study
    f_orient = 0.5601

    yields = dc_capacity_kw * psh_samples * 365.0 * f_orient * pr_samples
    paybacks = (dc_capacity_kw * cost_samples) / (yields * tariff_samples)

    return {
        "n_iterations": n_iterations,
        "yield_mwh_p5": round(float(np.percentile(yields, 5)) / 1000.0, 2),
        "yield_mwh_p50": round(float(np.percentile(yields, 50)) / 1000.0, 2),
        "yield_mwh_p95": round(float(np.percentile(yields, 95)) / 1000.0, 2),
        "payback_yrs_p5": round(float(np.percentile(paybacks, 5)), 2),
        "payback_yrs_p50": round(float(np.percentile(paybacks, 50)), 2),
        "payback_yrs_p95": round(float(np.percentile(paybacks, 95)), 2)
    }


def main():
    sb = run_setback_sensitivity()
    print("--- Setback Sensitivity (Usable Area Fraction) ---")
    for s_idx, s in enumerate(sb["setbacks"]):
        print(f"Setback {s:4.2f}m: Res={sb['residential']['usable_fractions'][s_idx]*100:5.1f}% | "
              f"Inst={sb['institutional']['usable_fractions'][s_idx]*100:5.1f}% | "
              f"Comm={sb['commercial']['usable_fractions'][s_idx]*100:5.1f}%")
        
    econ = run_economic_sensitivity()
    print("\n--- Economic Sensitivity (Payback Years) ---")
    print(f"Tariff (AED/kWh): {econ['tariffs']}")
    for c, pbs in econ['payback_table'].items():
        print(f"CAPEX ${c:4.0f}/kW: {pbs}")

    mc = run_monte_carlo_uncertainty()
    print("\n--- Monte Carlo Uncertainty (UoS W5, 1000 runs) ---")
    print(f"Annual Yield: P5={mc['yield_mwh_p5']} MWh | P50={mc['yield_mwh_p50']} MWh | P95={mc['yield_mwh_p95']} MWh")
    print(f"Payback:      P5={mc['payback_yrs_p5']} yrs | P50={mc['payback_yrs_p50']} yrs | P95={mc['payback_yrs_p95']} yrs")


if __name__ == "__main__":
    main()

