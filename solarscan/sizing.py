"""
Sizing module for rooftop solar pre-feasibility analysis.
Computes DC array capacity, recommended AC inverter rating, and module counts.
"""

import math


def calculate_dc_capacity(usable_area: float, module_efficiency: float = 0.20) -> float:
    """
    Computes nameplate direct current (DC) array capacity under Standard Test
    Conditions (STC, 1000 W/m^2 irradiance, 25 deg C cell temperature).
    
    Formula:
        P_DC = usable_area * module_efficiency * 1000 W/m^2 / 1000 W/kW
             = usable_area * module_efficiency
             
    Returns capacity in kW DC.
    """
    capacity_watts = usable_area * module_efficiency * 1000.0
    return round(capacity_watts / 1000.0, 3)


def recommend_inverter_capacity(dc_capacity_kw: float, dc_ac_ratio: float = 1.2) -> float:
    """
    Recommends alternating current (AC) inverter capacity based on target
    Inverter Loading Ratio (ILR = DC/AC).
    
    Formula:
        P_AC = P_DC / ILR
        
    Returns capacity in kW AC.
    """
    if dc_ac_ratio <= 0:
        return dc_capacity_kw
    ac_capacity_kw = dc_capacity_kw / dc_ac_ratio
    return round(ac_capacity_kw, 2)


def calculate_module_count(dc_capacity_kw: float, module_rating_watts: float = 400.0) -> int:
    """
    Calculates the integer count of photovoltaic modules required to meet DC capacity.
    """
    if module_rating_watts <= 0:
        return 0
    total_watts = dc_capacity_kw * 1000.0
    return int(math.floor(total_watts / module_rating_watts))
