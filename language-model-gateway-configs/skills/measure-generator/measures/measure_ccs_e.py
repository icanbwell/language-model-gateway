"""
HEDIS MY 2025 - Cervical Cancer Screening (CCS-E)

The percentage of members 21-64 years of age who were recommended for
routine cervical cancer screening who were screened for cervical cancer:

- Members 24-64: cervical cytology within the last 3 years.
- Members 30-64: hrHPV testing within the last 5 years.
- Members 30-64: cervical cytology/hrHPV cotesting within the last 5 years.
"""

from __future__ import annotations

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    get_observation_date,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
    SNOMED,
)

VALUE_SETS = load_value_sets_from_csv("CCS-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_female(bundle: dict) -> bool:
    """Check if member is recommended for routine cervical cancer screening."""
    patient = get_patient(bundle)
    if not patient:
        return False
    if patient.get("gender") == "female":
        return True
    for ext in patient.get("extension", []):
        url = ext.get("url", "")
        vc = ext.get("valueCodeableConcept", {}) or ext.get("valueCode", "")
        if "us-core-birthsex" in url and vc in ("F", "female"):
            return True
        if isinstance(vc, dict):
            for coding in vc.get("coding", []):
                if coding.get("code") in ("LA3-6", "female", "female-typical"):
                    return True
    return False


def _is_male_at_birth(bundle: dict) -> bool:
    """Check if sex assigned at birth is male (exclusion)."""
    patient = get_patient(bundle)
    if not patient:
        return False
    for ext in patient.get("extension", []):
        url = ext.get("url", "")
        vc = ext.get("valueCodeableConcept", {}) or ext.get("valueCode", "")
        if "us-core-birthsex" in url and vc in ("M", "male"):
            return True
        if isinstance(vc, dict):
            for coding in vc.get("coding", []):
                if coding.get("code") == "LA2-8":
                    return True
    return False


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Members 24-64 by end of MY, recommended for routine screening (female)."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (24 <= age <= 64):
        return False, []
    if not _is_female(bundle):
        return False, []
    return True, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Hospice, death, palliative care, hysterectomy, absence of cervix, male at birth."""
    excluded, refs = check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=False,
    )
    if excluded:
        return True, refs

    far_past = date(1900, 1, 1)
    _, my_end = measurement_year_dates(measurement_year)

    # Hysterectomy with no residual cervix
    hyst_codes = all_codes(VALUE_SETS, "Hysterectomy With No Residual Cervix")
    if hyst_codes:
        found = find_procedures_with_codes(bundle, hyst_codes, far_past, my_end)
        if found:
            return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found]
        found_cond = find_conditions_with_codes(bundle, hyst_codes, far_past, my_end)
        if found_cond:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found_cond]

    # Absence of cervix diagnosis
    absence_codes = all_codes(VALUE_SETS, "Absence of Cervix Diagnosis")
    if absence_codes:
        found = find_conditions_with_codes(bundle, absence_codes, far_past, my_end)
        if found:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]

    # Male at birth
    if _is_male_at_birth(bundle):
        return True, refs

    return False, refs


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Cervical cytology within 3 years or hrHPV within 5 years."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    # Cervical cytology within 3 years (MY and 2 years prior) for ages 24-64
    cytology_start = date(measurement_year - 2, 1, 1)
    cytology_end = my_end

    for vs_name in (
        "Cervical Cytology Lab Test",
        "Cervical Cytology Result or Finding",
    ):
        cytology_codes = all_codes(VALUE_SETS, vs_name)
        if cytology_codes:
            found_obs = find_observations_with_codes(
                bundle, cytology_codes, cytology_start, cytology_end
            )
            if found_obs:
                evaluated.append(f"Observation/{found_obs[0][0].get('id')}")
                return True, evaluated
            found_proc = find_procedures_with_codes(
                bundle, cytology_codes, cytology_start, cytology_end
            )
            if found_proc:
                evaluated.append(f"Procedure/{found_proc[0][0].get('id')}")
                return True, evaluated

    # hrHPV testing within 5 years for ages 30-64
    if age >= 30:
        hpv_start = date(measurement_year - 4, 1, 1)
        hpv_end = my_end

        hpv_codes = all_codes(VALUE_SETS, "High Risk HPV Lab Test")
        if hpv_codes:
            for obs in get_resources_by_type(bundle, "Observation"):
                obs_date = get_observation_date(obs)
                if not obs_date or not is_date_in_range(obs_date, hpv_start, hpv_end):
                    continue
                # Must be 30+ on test date
                age_at_test = calculate_age(birth_date, obs_date)
                if age_at_test < 30:
                    continue
                if resource_has_any_code(obs, hpv_codes):
                    evaluated.append(f"Observation/{obs.get('id')}")
                    return True, evaluated

        # SNOMED direct reference code 718591004
        snomed_hpv = {SNOMED: {"718591004"}}
        for obs in get_resources_by_type(bundle, "Observation"):
            obs_date = get_observation_date(obs)
            if not obs_date or not is_date_in_range(obs_date, hpv_start, hpv_end):
                continue
            age_at_test = calculate_age(birth_date, obs_date)
            if age_at_test < 30:
                continue
            if resource_has_any_code(obs, snomed_hpv):
                evaluated.append(f"Observation/{obs.get('id')}")
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_ccs_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate CCS-E measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="CCS-E",
        measure_name="Cervical Cancer Screening",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
