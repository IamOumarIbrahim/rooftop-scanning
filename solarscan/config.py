"""
Regional configuration and utility profiles for SolarScan.
Provides verified utility tariffs, solar irradiance baselines, and financial
assumptions across the United Arab Emirates.
"""

import os
from typing import Dict, Any, Optional
import yaml

DEFAULT_CONFIG: Dict[str, Any] = {
    "default_tilt_deg": 15.0,
    "setback_m": 1.5,
    "module_efficiency": 0.20,
    "dc_ac_ratio": 1.2,
    "peak_sun_hours_per_day": 5.5,
    "system_loss_factor": 0.85,
    "cost_per_kw": 1000.0,
    "rate_aed": 0.38,
    "grid_co2_kg_per_kwh": 0.42,
    "discount_rate": 0.05,
    "lifetime_years": 25,
    "annual_degradation": 0.005,
}

REGIONAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "sharjah": {
        "emirate": "Sharjah",
        "utility": "SEWA",
        "rate_aed": 0.38,
        "peak_sun_hours_per_day": 5.50,
        "default_tilt_deg": 15.0,
        "notes": "Sharjah Electricity, Water and Gas Authority commercial non-slab rate."
    },
    "dubai": {
        "emirate": "Dubai",
        "utility": "DEWA",
        "rate_aed": 0.38,
        "peak_sun_hours_per_day": 5.55,
        "default_tilt_deg": 15.0,
        "notes": "Dubai Electricity and Water Authority commercial tariff baseline."
    },
    "abu_dhabi": {
        "emirate": "Abu Dhabi",
        "utility": "TAQA / ADDC",
        "rate_aed": 0.30,
        "peak_sun_hours_per_day": 5.60,
        "default_tilt_deg": 15.0,
        "notes": "Abu Dhabi Distribution Company standard commercial tariff."
    },
    "ajman": {
        "emirate": "Ajman",
        "utility": "Etihad WE",
        "rate_aed": 0.38,
        "peak_sun_hours_per_day": 5.50,
        "default_tilt_deg": 15.0,
        "notes": "Etihad Water and Electricity Northern Emirates commercial tariff."
    },
    "ras_al_khaimah": {
        "emirate": "Ras Al Khaimah",
        "utility": "Etihad WE",
        "rate_aed": 0.38,
        "peak_sun_hours_per_day": 5.45,
        "default_tilt_deg": 15.0,
        "notes": "Etihad Water and Electricity RAK industrial/commercial profile."
    }
}


def normalize_emirate_key(name: str) -> str:
    """Normalizes emirate string to canonical key."""
    cleaned = name.lower().strip().replace(" ", "_").replace("-", "_")
    alias_map = {
        "rak": "ras_al_khaimah",
        "ad": "abu_dhabi",
        "shj": "sharjah",
        "dxb": "dubai",
        "ajm": "ajman"
    }
    return alias_map.get(cleaned, cleaned)


def get_emirate_profile(emirate_name: str) -> Dict[str, Any]:
    """
    Returns the verified utility tariff and solar resource profile for a UAE Emirate.
    
    Raises ValueError if emirate is unknown.
    """
    key = normalize_emirate_key(emirate_name)
    if key not in REGIONAL_PROFILES:
        valid_keys = ", ".join(REGIONAL_PROFILES.keys())
        raise ValueError(f"Unknown Emirate '{emirate_name}'. Supported: {valid_keys}")
    return dict(REGIONAL_PROFILES[key])


def load_config(
    config_path: str = "solarscan.yaml",
    emirate: Optional[str] = None
) -> Dict[str, Any]:
    """
    Loads configuration from YAML file with fallback to defaults and optional
    emirate-specific parameter overrides.
    """
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f)
                if isinstance(user_cfg, dict):
                    # Extract top-level overrides
                    for k, v in user_cfg.items():
                        if k != "regional_profiles":
                            cfg[k] = v
        except Exception as e:
            print(f"Warning: Failed to parse configuration file {config_path}: {e}")

    if emirate:
        profile = get_emirate_profile(emirate)
        if "rate_aed" in profile:
            cfg["rate_aed"] = profile["rate_aed"]
        if "peak_sun_hours_per_day" in profile:
            cfg["peak_sun_hours_per_day"] = profile["peak_sun_hours_per_day"]
        if "default_tilt_deg" in profile:
            cfg["default_tilt_deg"] = profile["default_tilt_deg"]
        cfg["emirate"] = profile["emirate"]
        cfg["utility"] = profile["utility"]

    return cfg
