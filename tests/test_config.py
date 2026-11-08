"""
Unit tests for solarscan.config module.
Verifies regional UAE utility profiles, tariff resolution, and configuration loading.
"""

import os
import pytest
from solarscan.config import (
    get_emirate_profile, normalize_emirate_key, load_config,
    DEFAULT_CONFIG, REGIONAL_PROFILES
)


def test_normalize_emirate_key():
    assert normalize_emirate_key("Sharjah") == "sharjah"
    assert normalize_emirate_key("SHJ") == "sharjah"
    assert normalize_emirate_key("Abu Dhabi") == "abu_dhabi"
    assert normalize_emirate_key("AD") == "abu_dhabi"
    assert normalize_emirate_key("RAK") == "ras_al_khaimah"
    assert normalize_emirate_key("Ras-Al-Khaimah") == "ras_al_khaimah"
    assert normalize_emirate_key("Dubai") == "dubai"
    assert normalize_emirate_key("Ajman") == "ajman"
    assert normalize_emirate_key("Fujairah") == "fujairah"
    assert normalize_emirate_key("FUJ") == "fujairah"
    assert normalize_emirate_key("Umm Al Quwain") == "umm_al_quwain"
    assert normalize_emirate_key("UAQ") == "umm_al_quwain"


def test_get_emirate_profile_valid():
    p_shj = get_emirate_profile("sharjah")
    assert p_shj["utility"] == "SEWA"
    assert p_shj["rate_aed"] == 0.38
    assert p_shj["pvgis_site"] == "sharjah"

    p_ad = get_emirate_profile("abu_dhabi")
    assert p_ad["utility"] == "ADDC"
    assert p_ad["rate_aed"] == 0.30
    assert p_ad["pvgis_site"] == "abu_dhabi"

    p_dxb = get_emirate_profile("dubai")
    assert p_dxb["utility"] == "DEWA"
    assert p_dxb["rate_aed"] == 0.38

    p_fuj = get_emirate_profile("fujairah")
    assert p_fuj["utility"] == "Etihad WE"
    assert p_fuj["rate_aed"] == 0.38

    p_uaq = get_emirate_profile("umm_al_quwain")
    assert p_uaq["utility"] == "Etihad WE"
    assert p_uaq["rate_aed"] == 0.38


def test_get_emirate_profile_invalid():
    with pytest.raises(ValueError, match="Unknown Emirate"):
        get_emirate_profile("Atlantis")


def test_load_config_defaults():
    cfg = load_config(config_path="non_existent_file.yaml")
    assert cfg["rate_aed"] == DEFAULT_CONFIG["rate_aed"]
    assert cfg["module_efficiency"] == 0.20
    assert cfg["cost_per_kw"] == 3000.0
    assert cfg["packing_factor"] == 0.70
    assert cfg["array_layout"] == "south"


def test_load_config_with_emirate_override():
    cfg_ad = load_config(emirate="abu_dhabi")
    assert cfg_ad["rate_aed"] == 0.30
    assert cfg_ad["pvgis_site"] == "abu_dhabi"
    assert cfg_ad["utility"] == "ADDC"

    cfg_shj = load_config(emirate="sharjah")
    assert cfg_shj["rate_aed"] == 0.38
    assert cfg_shj["utility"] == "SEWA"


def test_load_config_corrupt_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("::: this is not valid yaml :::", encoding="utf-8")
    cfg = load_config(config_path=str(bad_yaml))
    assert cfg["rate_aed"] == 0.38
