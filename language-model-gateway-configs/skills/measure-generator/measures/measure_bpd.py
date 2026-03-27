"""
HEDIS MY 2025 - Blood Pressure Control for Patients With Diabetes (BPD)

The percentage of members 18-75 years of age with diabetes (types 1 and 2)
whose blood pressure (BP) was adequately controlled (<140/90 mm Hg) during
the measurement year.

Uses the most recent BP reading during MY. Excludes readings taken during
acute inpatient stays or ED visits. If multiple BPs on the same date,
uses the lowest systolic and lowest diastolic.
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
    prior_year_dates,
    get_medication_date,
    find_conditions_with_codes,
    all_codes,
    get_bp_readings,
    get_most_recent_bp,
)

VALUE_SETS = load_value_sets_from_csv("BPD")


def _has_diabetes(bundle: dict, measurement_year: int) -> bool:
    """
    Identify members with diabetes via claims/encounter data or pharmacy data.

    Claims: at least two diabetes diagnoses on different dates during MY or PY.
    Pharmacy: dispensed diabetes medication during MY or PY with at least one
    diabetes diagnosis.
    """
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, _ = prior_year_dates(measurement_year)
    lookback_start = py_start

    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")
    if not diabetes_codes:
        return False

    # Claims-based: two diagnoses on different dates
    conditions = find_conditions_with_codes(
        bundle, diabetes_codes, lookback_start, my_end
    )
    onset_dates = sorted({d for _, d in conditions if d is not None})
    if len(onset_dates) >= 2:
        return True

    # Pharmacy-based: diabetes medication + at least one diabetes diagnosis
    if conditions:
        for rtype in ("MedicationDispense", "MedicationRequest"):
            for med in get_resources_by_type(bundle, rtype):
                med_date = get_medication_date(med)
                if med_date and is_date_in_range(med_date, lookback_start, my_end):
                    return True

    return False


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check BPD eligible population:
    - Age 18-75 as of Dec 31 of MY
    - Has diabetes (by claims or pharmacy data)
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (18 <= age <= 75):
        return False, evaluated

    if not _has_diabetes(bundle, measurement_year):
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check BPD exclusions (common exclusions)."""
    return check_common_exclusions(bundle, VALUE_SETS, measurement_year)


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check BPD numerator: most recent BP during MY is <140/90 mm Hg.

    Excludes BPs taken during acute inpatient stays or ED visits.
    If multiple BPs on the same date, uses the lowest systolic and lowest
    diastolic from that date.
    Not compliant if BP >= 140/90, missing, incomplete, or no reading during MY.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    bp_readings = get_bp_readings(bundle, my_start, my_end, exclude_inpatient_ed=True)
    systolic, diastolic, bp_refs = get_most_recent_bp(bp_readings)
    evaluated.extend(bp_refs)

    if systolic is None or diastolic is None:
        return False, evaluated

    if systolic < 140 and diastolic < 90:
        return True, evaluated

    return False, evaluated


def calculate_bpd_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the BPD measure for a patient bundle."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="BPD",
        measure_name="Blood Pressure Control for Patients With Diabetes",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
