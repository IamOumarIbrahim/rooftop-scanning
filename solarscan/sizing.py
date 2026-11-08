"""
Sizing module for rooftop solar pre-feasibility analysis.
Computes DC array capacity, recommended AC inverter rating, and module counts.
"""

import math


FLAT_ROOF_PACKING_FACTOR = 0.70  # module area / roof area for tilted rows on flat roofs (NREL, Gagnon et al. 2016)


def calculate_dc_capacity(
    usable_area: float,
    module_efficiency: float = 0.20,
    packing_factor: float = FLAT_ROOF_PACKING_FACTOR,
) -> float:
    """
    DC nameplate capacity (kWp) at Standard Test Conditions (1000 W/m^2, 25 deg C):

        P_dc = A_usable * k_pack * eta * 1 kW/m^2

    k_pack is the share of usable roof covered by modules. Tilted rows on a flat
    roof need gaps so that one row does not shade the next, so k_pack < 1.
    Returns kW DC.
    """
    if usable_area <= 0.0 or module_efficiency <= 0.0 or packing_factor <= 0.0:
        return 0.0
    return round(usable_area * min(1.0, packing_factor) * module_efficiency, 3)


def recommend_inverter_capacity(dc_capacity_kw: float, dc_ac_ratio: float = 1.2) -> float:
    """
    Recommends alternating current (AC) inverter capacity based on target
    Inverter Loading Ratio (ILR = DC/AC).
    
    Formula:
        P_AC = P_DC / ILR
        
    Returns capacity in kW AC.
    """
    if dc_capacity_kw <= 0.0:
        return 0.0
    if dc_ac_ratio <= 0:
        return round(dc_capacity_kw, 2)
    ac_capacity_kw = dc_capacity_kw / dc_ac_ratio
    return round(ac_capacity_kw, 2)


def calculate_module_count(dc_capacity_kw: float, module_rating_watts: float = 400.0) -> int:
    """
    Calculates the integer count of photovoltaic modules required to meet DC capacity.
    """
    if dc_capacity_kw <= 0.0 or module_rating_watts <= 0.0:
        return 0
    total_watts = dc_capacity_kw * 1000.0
    return int(math.floor(total_watts / module_rating_watts))


def is_viable_system(dc_capacity_kw: float, min_kw: float = 3.0) -> bool:
    """
    Determines whether a sized rooftop PV system satisfies minimum technical
    and economic viability thresholds for commercial/residential grid interconnect.
    Systems below min_kw (default 3.0 kW) typically do not justify balance-of-system,
    permitting, and interconnection fixed costs.
    """
    return dc_capacity_kw >= min_kw
