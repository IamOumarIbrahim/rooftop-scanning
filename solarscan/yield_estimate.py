"""
Yield estimation module for rooftop solar pre-feasibility analysis.
Provides orientation derating, annual AC energy generation estimation,
and financial payback modeling.
"""

import math


def calculate_orientation_derate(azimuth_deg: float, tilt_deg: float) -> float:
    """
    Computes an empirical orientation and tilt derating factor f_orient in [0.5, 1.0].
    
    The optimal orientation in the Northern Hemisphere is South (180 deg) at a tilt
    angle approximately matching local latitude (15 to 25 deg in the UAE/Gulf).
    
    Formulation:
        delta_azimuth = |((azimuth - 180 + 180) mod 360) - 180|
        f_azimuth = cos(radians(delta_azimuth / 2))
        f_tilt = cos(radians(|tilt - 20| / 2))
        f_orient = max(0.5, f_azimuth * f_tilt)
    """
    clamped_tilt = max(0.0, min(90.0, tilt_deg))
    dev_from_south = abs(((azimuth_deg - 180.0 + 180.0) % 360.0) - 180.0)
    
    azimuth_factor = math.cos(math.radians(dev_from_south / 2.0))
    tilt_factor = math.cos(math.radians(abs(clamped_tilt - 20.0) / 2.0))
    
    derate = max(0.5, azimuth_factor * tilt_factor)
    return round(derate, 4)


def calculate_temperature_derate(
    ambient_temp_c: float = 35.0,
    temp_coeff: float = -0.0035,
    noct: float = 45.0,
    irradiance: float = 800.0
) -> float:
    """
    Computes cell operating temperature derate factor based on ambient temperature
    and Normal Operating Cell Temperature (NOCT).
    
    Cell temperature:
        T_cell = T_amb + (NOCT - 20) * (G / 800)
    Temperature loss factor:
        f_temp = 1 + gamma * (T_cell - 25)
    """
    t_cell = ambient_temp_c + (noct - 20.0) * (irradiance / 800.0)
    f_temp = 1.0 + temp_coeff * (t_cell - 25.0)
    return round(max(0.5, min(1.0, f_temp)), 4)


def calculate_inverter_clipping_loss(dc_ac_ratio: float = 1.2) -> float:
    """
    Estimates annual percentage clipping loss due to Inverter Loading Ratio (ILR = DC/AC).
    Empirical polynomial approximation for sunny desert climates.
    For ILR <= 1.15, clipping loss is negligible (< 0.1%).
    For ILR = 1.20, clipping loss is approximately 0.4% to 0.8%.
    For ILR = 1.35, clipping loss approaches 2.5% to 3.5%.
    """
    if dc_ac_ratio <= 1.15:
        return 0.0
    excess = dc_ac_ratio - 1.15
    clipping_loss_pct = 75.0 * (excess ** 2)
    return round(min(15.0, clipping_loss_pct), 3)


def calculate_specific_yield(annual_kwh: float, dc_capacity_kw: float) -> float:
    """
    Computes specific energy yield in kWh per kWp installed per year (kWh/kWp/yr).
    Standard benchmarking metric for photovoltaic plant performance across regions.
    """
    if dc_capacity_kw <= 0.0:
        return 0.0
    return round(annual_kwh / dc_capacity_kw, 2)


def breakdown_performance_ratio(
    ambient_temp_c: float = 35.0,
    soiling_factor: float = 0.95,
    inverter_eff: float = 0.98,
    dc_wiring_loss: float = 0.015,
    ac_wiring_loss: float = 0.01
) -> float:
    """
    Calculates overall system Performance Ratio (PR) by multiplying individual
    subsystem efficiency factors.
    """
    f_temp = calculate_temperature_derate(ambient_temp_c=ambient_temp_c)
    f_wiring = (1.0 - dc_wiring_loss) * (1.0 - ac_wiring_loss)
    pr = f_temp * soiling_factor * inverter_eff * f_wiring
    return round(pr, 4)


def estimate_annual_yield(
    dc_capacity_kw: float,
    tilt_deg: float = 15.0,
    azimuth_deg: float = 180.0,
    peak_sun_hours_per_day: float = 5.5,
    system_loss_factor: float = 0.85
) -> float:
    """
    Estimates total annual AC energy generation in kilowatt-hours (kWh/year).
    
    Default parameters reflect Arabian Gulf solar resource:
        Peak Sun Hours (PSH): 5.5 kWh/m^2/day (GHI ~ 2000 kWh/m^2/year)
        System loss factor (PR): 0.85 (inverter, temperature derating, dust/soiling, wiring)
        
    Formula:
        E_annual = P_DC * PSH * 365 * f_orient * PR
    """
    derate = calculate_orientation_derate(azimuth_deg, tilt_deg)
    annual_kwh = dc_capacity_kw * peak_sun_hours_per_day * 365.0 * derate * system_loss_factor
    return round(annual_kwh, 2)


def estimate_simple_payback(
    annual_kwh: float,
    rate_per_kwh: float,
    cost_per_kw: float = 1000.0,
    dc_capacity_kw: float = 10.0
) -> float:
    """
    Estimates simple financial payback period in years.
    
    Formula:
        CAPEX = P_DC * cost_per_kw
        Annual_Savings = E_annual * rate_per_kwh
        T_payback = CAPEX / Annual_Savings
    """
    annual_savings = annual_kwh * rate_per_kwh
    total_cost = dc_capacity_kw * cost_per_kw
    
    if annual_savings <= 0:
        return float('inf')
    
    payback_years = total_cost / annual_savings
    return round(payback_years, 2)


def calculate_lcoe(
    annual_kwh: float,
    dc_capacity_kw: float,
    cost_per_kw: float = 1000.0,
    discount_rate: float = 0.05,
    lifetime_years: int = 25,
    om_cost_fraction: float = 0.015,
    annual_degradation: float = 0.005
) -> float:
    """
    Computes Levelized Cost of Electricity (LCOE) in currency units per kWh.
    
    Formula:
        LCOE = [ CAPEX + sum_{t=1}^N (OPEX_t / (1+r)^t) ] / [ sum_{t=1}^N (E_t / (1+r)^t) ]
    """
    capex = dc_capacity_kw * cost_per_kw
    annual_om = capex * om_cost_fraction
    
    discounted_costs = capex
    discounted_energy = 0.0
    
    for year in range(1, lifetime_years + 1):
        df = (1.0 + discount_rate) ** year
        discounted_costs += annual_om / df
        gen_year = annual_kwh * ((1.0 - annual_degradation) ** (year - 1))
        discounted_energy += gen_year / df
        
    if discounted_energy <= 0:
        return float('inf')
        
    return round(discounted_costs / discounted_energy, 4)


def calculate_npv(
    annual_kwh: float,
    tariff_per_kwh: float,
    dc_capacity_kw: float,
    cost_per_kw: float = 1000.0,
    discount_rate: float = 0.05,
    lifetime_years: int = 25,
    om_cost_fraction: float = 0.015,
    annual_degradation: float = 0.005,
    tariff_escalation: float = 0.02
) -> float:
    """
    Computes Net Present Value (NPV) over system lifetime in currency units.
    
    Accounts for annual module degradation, operational maintenance costs (OPEX),
    and electricity tariff escalation under discounted cash flow (DCF).
    """
    capex = dc_capacity_kw * cost_per_kw
    annual_om_base = capex * om_cost_fraction
    npv = -capex
    
    for year in range(1, lifetime_years + 1):
        df = (1.0 + discount_rate) ** year
        gen_year = annual_kwh * ((1.0 - annual_degradation) ** (year - 1))
        tariff_year = tariff_per_kwh * ((1.0 + tariff_escalation) ** (year - 1))
        revenue_year = gen_year * tariff_year
        om_year = annual_om_base * ((1.0 + 0.02) ** (year - 1))
        net_cf = revenue_year - om_year
        npv += net_cf / df
        
    return round(npv, 2)


def calculate_discounted_payback(
    annual_kwh: float,
    tariff_per_kwh: float,
    dc_capacity_kw: float,
    cost_per_kw: float = 1000.0,
    discount_rate: float = 0.05,
    lifetime_years: int = 25,
    om_cost_fraction: float = 0.015,
    annual_degradation: float = 0.005
) -> float:
    """
    Calculates the discounted payback period in years where cumulative discounted
    savings exceed initial capital expenditure.
    """
    capex = dc_capacity_kw * cost_per_kw
    annual_om = capex * om_cost_fraction
    cum_dcf = -capex
    
    for year in range(1, lifetime_years + 1):
        df = (1.0 + discount_rate) ** year
        gen_year = annual_kwh * ((1.0 - annual_degradation) ** (year - 1))
        net_cf = (gen_year * tariff_per_kwh) - annual_om
        prev_cum = cum_dcf
        cum_dcf += net_cf / df
        if cum_dcf >= 0:
            # Linear interpolation for fractional year
            fraction = abs(prev_cum) / (net_cf / df)
            return round((year - 1) + fraction, 2)
            
    return float('inf')


def calculate_carbon_offset(
    annual_kwh: float,
    grid_emission_factor_kg_per_kwh: float = 0.42
) -> float:
    """
    Estimates avoided greenhouse gas emissions in metric tonnes of CO2 equivalent per year.
    Default baseline reflects UAE national electrical grid emission intensity (0.42 kg CO2e/kWh).
    """
    if annual_kwh <= 0.0 or grid_emission_factor_kg_per_kwh <= 0.0:
        return 0.0
    tonnes_co2 = (annual_kwh * grid_emission_factor_kg_per_kwh) / 1000.0
    return round(tonnes_co2, 2)

