"""
HEDIS MY 2025 - Adults' Access to Preventive/Ambulatory Health Services (AAP).

Members 20+ who had an ambulatory or preventive care visit during the
measurement year (Medicaid/Medicare) or during the measurement year and
2 years prior (Commercial).
"""

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    find_encounters_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("AAP")


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check eligible population: age 20+ as of Dec 31 of MY."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 20:
        return False, []

    return True, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice, death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: ambulatory or preventive care visit during MY.

    For simplicity, uses Medicaid/Medicare criteria (MY only).
    Commercial would extend to MY-2 through MY.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    # Ambulatory Visits
    amb_codes = all_codes(VALUE_SETS, "Ambulatory Visits")
    if amb_codes:
        matches = find_encounters_with_codes(bundle, amb_codes, my_start, my_end)
        if matches:
            evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
            return True, evaluated

    # Reason for Ambulatory Visit
    reason_codes = all_codes(VALUE_SETS, "Reason for Ambulatory Visit")
    if reason_codes:
        matches = find_encounters_with_codes(bundle, reason_codes, my_start, my_end)
        if matches:
            evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
            return True, evaluated

    return False, evaluated


def calculate_aap_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate AAP measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="AAP",
        measure_name="Adults' Access to Preventive/Ambulatory Health Services",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
