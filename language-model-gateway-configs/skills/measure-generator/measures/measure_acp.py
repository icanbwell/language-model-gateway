"""
HEDIS MY 2025 - Advance Care Planning (ACP).

Members 66-80 with advanced illness/frailty/palliative care, and all 81+,
who had advance care planning during the measurement year.
"""

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    get_condition_onset,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_medications_with_codes,
    all_codes,
    ICD10CM,
)

VALUE_SETS = load_value_sets_from_csv("ACP")


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check eligible population for ACP.

    - Age 81+: all members
    - Age 66-80: must have advanced illness, frailty, or palliative care
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    if age < 66:
        return False, evaluated

    # Age 81+: automatically eligible
    if age >= 81:
        return True, evaluated

    # Age 66-80: need advanced illness, frailty, or palliative care
    my_start, _ = measurement_year_dates(measurement_year)

    # Advanced illness: 2+ dates of service during MY
    adv_illness_codes = all_codes(VALUE_SETS, "Advanced Illness")
    if adv_illness_codes:
        matches = find_conditions_with_codes(
            bundle, adv_illness_codes, my_start, my_end
        )
        if len(matches) >= 2:
            dates = set(d for _, d in matches if d)
            if len(dates) >= 2:
                evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
                return True, evaluated

    # Dementia medications during MY
    dem_med_codes = all_codes(VALUE_SETS, "Dementia Medications")
    if dem_med_codes:
        matches = find_medications_with_codes(bundle, dem_med_codes, my_start, my_end)
        if matches:
            evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in matches)
            return True, evaluated

    # Frailty during MY
    for vs_name in (
        "Frailty Device",
        "Frailty Diagnosis",
        "Frailty Encounter",
        "Frailty Symptom",
    ):
        frailty_codes = all_codes(VALUE_SETS, vs_name)
        if frailty_codes:
            enc_matches = find_encounters_with_codes(
                bundle, frailty_codes, my_start, my_end
            )
            if enc_matches:
                evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in enc_matches)
                return True, evaluated
            cond_matches = find_conditions_with_codes(
                bundle, frailty_codes, my_start, my_end
            )
            if cond_matches:
                evaluated.extend(f"Condition/{c.get('id')}" for c, _ in cond_matches)
                return True, evaluated

    # Palliative care during MY
    for vs_name in (
        "Palliative Care Assessment",
        "Palliative Care Encounter",
        "Palliative Care Intervention",
    ):
        pc_codes = all_codes(VALUE_SETS, vs_name)
        if pc_codes:
            matches = find_encounters_with_codes(bundle, pc_codes, my_start, my_end)
            if matches:
                evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
                return True, evaluated

    # Palliative care ICD-10-CM Z51.5
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if onset and is_date_in_range(onset, my_start, my_end):
            for coding in cond.get("code", {}).get("coding", []):
                if coding.get("system") == ICD10CM and coding.get("code") == "Z51.5":
                    evaluated.append(f"Condition/{cond.get('id')}")
                    return True, evaluated

    return False, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice, death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: advance care planning during the measurement year."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    acp_codes = all_codes(VALUE_SETS, "Advance Care Planning")
    if not acp_codes:
        return False, evaluated

    # Check encounters
    matches = find_encounters_with_codes(bundle, acp_codes, my_start, my_end)
    if matches:
        evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
        return True, evaluated

    # Check procedures
    proc_matches = find_procedures_with_codes(bundle, acp_codes, my_start, my_end)
    if proc_matches:
        evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
        return True, evaluated

    return False, evaluated


def calculate_acp_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate ACP measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="ACP",
        measure_name="Advance Care Planning",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
