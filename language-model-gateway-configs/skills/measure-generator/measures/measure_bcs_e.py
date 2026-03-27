"""
HEDIS MY 2025 - Breast Cancer Screening (BCS-E)

The percentage of members 52-74 years of age who were recommended for
routine breast cancer screening and had a mammogram to screen for breast
cancer.
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
    parse_date,
    is_date_in_range,
    measurement_year_dates,
    resource_has_code,
    resource_has_any_code,
    get_procedure_date,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
    CPT,
)

VALUE_SETS = load_value_sets_from_csv("BCS-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_female(bundle: dict) -> bool:
    """Check if member is recommended for routine breast cancer screening."""
    patient = get_patient(bundle)
    if not patient:
        return False
    gender = patient.get("gender", "")
    if gender == "female":
        return True
    # Check extensions for sex assigned at birth or sex parameter for clinical use
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


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Members 52-74 by end of MY, recommended for routine screening (female)."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (52 <= age <= 74):
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
    """Hospice, death, palliative care, frailty/advanced illness, bilateral mastectomy."""
    excluded, refs = check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=True,
    )
    if excluded:
        return True, refs

    far_past = date(1900, 1, 1)
    _, my_end = measurement_year_dates(measurement_year)

    # Bilateral mastectomy
    bilateral_codes = all_codes(VALUE_SETS, "Bilateral Mastectomy")
    if bilateral_codes:
        found = find_procedures_with_codes(bundle, bilateral_codes, far_past, my_end)
        if found:
            return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found]
        found_cond = find_conditions_with_codes(
            bundle, bilateral_codes, far_past, my_end
        )
        if found_cond:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found_cond]

    # History of bilateral mastectomy
    hist_codes = all_codes(VALUE_SETS, "History of Bilateral Mastectomy")
    if hist_codes:
        found = find_conditions_with_codes(bundle, hist_codes, far_past, my_end)
        if found:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]

    # Unilateral mastectomy on both sides
    left_codes = all_codes(VALUE_SETS, "Unilateral Mastectomy Left")
    right_codes = all_codes(VALUE_SETS, "Unilateral Mastectomy Right")
    absence_left_codes = all_codes(VALUE_SETS, "Absence of Left Breast")
    absence_right_codes = all_codes(VALUE_SETS, "Absence of Right Breast")

    has_left = False
    has_right = False

    if left_codes and find_procedures_with_codes(bundle, left_codes, far_past, my_end):
        has_left = True
    if absence_left_codes and find_conditions_with_codes(
        bundle, absence_left_codes, far_past, my_end
    ):
        has_left = True

    if right_codes and find_procedures_with_codes(
        bundle, right_codes, far_past, my_end
    ):
        has_right = True
    if absence_right_codes and find_conditions_with_codes(
        bundle, absence_right_codes, far_past, my_end
    ):
        has_right = True

    if has_left and has_right:
        return True, refs

    # Gender-affirming chest surgery with gender dysphoria
    gender_dysphoria_codes = all_codes(VALUE_SETS, "Gender Dysphoria")
    if gender_dysphoria_codes:
        has_dysphoria = bool(
            find_conditions_with_codes(bundle, gender_dysphoria_codes, far_past, my_end)
        )
        if has_dysphoria:
            # Check for CPT 19318
            for proc in get_resources_by_type(bundle, "Procedure"):
                proc_date = get_procedure_date(proc)
                if proc_date and is_date_in_range(proc_date, far_past, my_end):
                    if resource_has_code(proc, {"19318"}, CPT):
                        return True, refs

    return False, refs


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """One or more mammograms Oct 1 two years prior through end of MY."""
    evaluated: list[str] = []
    mammo_codes = all_codes(VALUE_SETS, "Mammography")
    if not mammo_codes:
        return False, evaluated

    start = date(measurement_year - 2, 10, 1)
    _, end = measurement_year_dates(measurement_year)

    for obs, obs_date in find_observations_with_codes(bundle, mammo_codes, start, end):
        evaluated.append(f"Observation/{obs.get('id')}")
        return True, evaluated
    for proc, proc_date in find_procedures_with_codes(bundle, mammo_codes, start, end):
        evaluated.append(f"Procedure/{proc.get('id')}")
        return True, evaluated
    # Check DiagnosticReport
    for dr in get_resources_by_type(bundle, "DiagnosticReport"):
        dr_date = parse_date(
            dr.get("effectiveDateTime")
            or (dr.get("effectivePeriod") or {}).get("start")
        )
        if dr_date and is_date_in_range(dr_date, start, end):
            if resource_has_any_code(dr, mammo_codes):
                evaluated.append(f"DiagnosticReport/{dr.get('id')}")
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_bcs_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate BCS-E measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="BCS-E",
        measure_name="Breast Cancer Screening",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
