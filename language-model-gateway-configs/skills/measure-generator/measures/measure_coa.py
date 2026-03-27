"""
HEDIS MY 2025 - Care for Older Adults (COA).

The percentage of adults 66 years of age and older who had both of the
following during the measurement year:
  - Medication Review
  - Functional Status Assessment

This is a multi-indicator measure (MY 2025 removed Pain Assessment; now 2 indicators).
"""

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    find_encounters_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("COA")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: 66 years and older as of Dec 31 of the measurement year.
    No event/diagnosis required.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 66:
        return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions: hospice, death.
    """
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


# ---------------------------------------------------------------------------
# Helper: check if encounter is in acute inpatient setting
# ---------------------------------------------------------------------------


def _is_acute_inpatient_encounter(
    encounter: dict,
) -> bool:
    """Check if an encounter matches acute inpatient codes."""
    acute_codes = all_codes(VALUE_SETS, "Acute Inpatient")
    acute_pos_codes = all_codes(VALUE_SETS, "Acute Inpatient POS")
    if acute_codes and resource_has_any_code(encounter, acute_codes):
        return True
    for t in encounter.get("type", []):
        if acute_codes and codeable_concept_has_any_code(t, acute_codes):
            return True
        if acute_pos_codes and codeable_concept_has_any_code(t, acute_pos_codes):
            return True
    return False


# ---------------------------------------------------------------------------
# Numerator: Medication Review
# ---------------------------------------------------------------------------


def _check_medication_review(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Medication Review: Either
    1) Both medication review AND medication list during the same visit
       in the measurement year (not in acute inpatient setting), OR
    2) Transitional care management services during the measurement year.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    # Option 2: Transitional care management services
    tcm_codes = all_codes(VALUE_SETS, "Transitional Care Management Services")
    if tcm_codes:
        tcm_hits = find_encounters_with_codes(bundle, tcm_codes, my_start, my_end)
        if tcm_hits:
            for enc, _ in tcm_hits:
                evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

        tcm_proc_hits = find_procedures_with_codes(bundle, tcm_codes, my_start, my_end)
        if tcm_proc_hits:
            for proc, _ in tcm_proc_hits:
                evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    # Option 1: medication review + medication list during the measurement year
    med_review_codes = all_codes(VALUE_SETS, "Medication Review")
    med_list_codes = all_codes(VALUE_SETS, "Medication List")

    if med_review_codes and med_list_codes:
        # Find medication review procedures/observations
        review_hits = find_procedures_with_codes(
            bundle, med_review_codes, my_start, my_end
        )
        review_obs_hits = find_observations_with_codes(
            bundle, med_review_codes, my_start, my_end
        )

        list_hits = find_procedures_with_codes(bundle, med_list_codes, my_start, my_end)
        list_obs_hits = find_observations_with_codes(
            bundle, med_list_codes, my_start, my_end
        )

        has_review = bool(review_hits or review_obs_hits)
        has_list = bool(list_hits or list_obs_hits)

        if has_review and has_list:
            for proc, _ in review_hits:
                evaluated.append(f"Procedure/{proc.get('id')}")
            for obs, _ in review_obs_hits:
                evaluated.append(f"Observation/{obs.get('id')}")
            for proc, _ in list_hits:
                evaluated.append(f"Procedure/{proc.get('id')}")
            for obs, _ in list_obs_hits:
                evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator: Functional Status Assessment
# ---------------------------------------------------------------------------


def _check_functional_status(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    At least one functional status assessment (Functional Status Assessment
    Value Set) during the measurement year, not in acute inpatient setting.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    fs_codes = all_codes(VALUE_SETS, "Functional Status Assessment")
    if not fs_codes:
        return False, evaluated

    proc_hits = find_procedures_with_codes(bundle, fs_codes, my_start, my_end)
    if proc_hits:
        for proc, _ in proc_hits:
            evaluated.append(f"Procedure/{proc.get('id')}")
        return True, evaluated

    obs_hits = find_observations_with_codes(bundle, fs_codes, my_start, my_end)
    if obs_hits:
        for obs, _ in obs_hits:
            evaluated.append(f"Observation/{obs.get('id')}")
        return True, evaluated

    enc_hits = find_encounters_with_codes(bundle, fs_codes, my_start, my_end)
    if enc_hits:
        for enc, _ in enc_hits:
            evaluated.append(f"Encounter/{enc.get('id')}")
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_coa_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate the COA measure for an individual patient.

    Returns a FHIR MeasureReport with two rate groups:
    Medication Review and Functional Status Assessment.
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        groups = [
            {
                "code": "COA-MedReview",
                "display": "Medication Review",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
            {
                "code": "COA-FunctionalStatus",
                "display": "Functional Status Assessment",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
        ]
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="COA",
            measure_name="Care for Older Adults",
            measurement_year=measurement_year,
            groups=groups,
            evaluated_resources=all_evaluated,
        )

    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(exclusion_refs)

    med_review_met, med_review_refs = _check_medication_review(bundle, measurement_year)
    all_evaluated.extend(med_review_refs)

    func_status_met, func_status_refs = _check_functional_status(
        bundle, measurement_year
    )
    all_evaluated.extend(func_status_refs)

    groups = [
        {
            "code": "COA-MedReview",
            "display": "Medication Review",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": med_review_met,
        },
        {
            "code": "COA-FunctionalStatus",
            "display": "Functional Status Assessment",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": func_status_met,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="COA",
        measure_name="Care for Older Adults",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
