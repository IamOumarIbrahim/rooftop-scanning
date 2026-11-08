"""
Configuration for SolarScan: model defaults and per-emirate profiles.

Every value here is a screening ASSUMPTION, not a measured fact. Change them in
solarscan.yaml or on the command line. Sources for the defaults:
  * tilt 15 deg, south-facing rows, packing factor 0.70, DC/AC 1.2:
    NREL flat-roof assumptions (Gagnon et al., NREL/TP-6A20-65298, 2016)
  * yield: PVGIS v5.3 grids with 14 % system loss (solarscan/data/pvgis/)
  * cost 3,000 AED/kWp: mid-point of 2.8-4.0 AED/Wp quoted for 50 kWp-1 MWp
    commercial rooftop systems in the UAE (installer surveys, 2025)
  * tariff 0.38 AED/kWh: top commercial slab of DEWA/SEWA, fuel surcharge excluded
"""

import os
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONFIG: Dict[str, Any] = {
    "default_tilt_deg": 15.0,
    "array_layout": "south",        # "south" (rows face true south) or "aligned" (rows follow the building)
    "setback_m": 1.5,
    "module_efficiency": 0.20,
    "packing_factor": 0.70,
    "dc_ac_ratio": 1.2,
    "pvgis_site": "sharjah",
    "cost_per_kw": 3000.0,          # AED per kWp installed
    "rate_aed": 0.38,               # AED per kWh
    "grid_co2_kg_per_kwh": 0.42,
    "discount_rate": 0.05,
    "lifetime_years": 25,
    "annual_degradation": 0.005,
    "om_cost_fraction": 0.015,
}

REGIONAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "sharjah": {"emirate": "Sharjah", "utility": "SEWA", "rate_aed": 0.38, "pvgis_site": "sharjah"},
    "dubai": {"emirate": "Dubai", "utility": "DEWA", "rate_aed": 0.38, "pvgis_site": "dubai"},
    "abu_dhabi": {"emirate": "Abu Dhabi", "utility": "ADDC", "rate_aed": 0.30, "pvgis_site": "abu_dhabi"},
    "ajman": {"emirate": "Ajman", "utility": "Etihad WE", "rate_aed": 0.38, "pvgis_site": "ajman"},
    "ras_al_khaimah": {"emirate": "Ras Al Khaimah", "utility": "Etihad WE", "rate_aed": 0.38,
                       "pvgis_site": "ras_al_khaimah"},
    "fujairah": {"emirate": "Fujairah", "utility": "Etihad WE", "rate_aed": 0.38, "pvgis_site": "ras_al_khaimah"},
    "umm_al_quwain": {"emirate": "Umm Al Quwain", "utility": "Etihad WE", "rate_aed": 0.38,
                      "pvgis_site": "ajman"},
}

_ALIASES = {"rak": "ras_al_khaimah", "ad": "abu_dhabi", "shj": "sharjah", "dxb": "dubai",
            "ajm": "ajman", "fuj": "fujairah", "uaq": "umm_al_quwain"}


def normalize_emirate_key(name: str) -> str:
    """Normalizes an emirate name or short code to its profile key."""
    cleaned = name.lower().strip().replace(" ", "_").replace("-", "_")
    return _ALIASES.get(cleaned, cleaned)


def get_emirate_profile(emirate_name: str) -> Dict[str, Any]:
    """Returns the profile for one emirate. Raises ValueError if unknown."""
    key = normalize_emirate_key(emirate_name)
    if key not in REGIONAL_PROFILES:
        raise ValueError(f"Unknown Emirate '{emirate_name}'. Supported: {', '.join(REGIONAL_PROFILES)}")
    return dict(REGIONAL_PROFILES[key])


def load_config(config_path: str = "solarscan.yaml", emirate: Optional[str] = None) -> Dict[str, Any]:
    """Defaults, then YAML overrides, then the emirate profile (if given)."""
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f)
            if isinstance(user_cfg, dict):
                cfg.update({k: v for k, v in user_cfg.items() if k != "regional_profiles"})
        except Exception as e:  # a broken YAML file should not stop a scan
            print(f"Warning: Failed to parse configuration file {config_path}: {e}")
    if emirate:
        profile = get_emirate_profile(emirate)
        cfg.update({k: profile[k] for k in ("rate_aed", "pvgis_site", "emirate", "utility")})
    return cfg
