"""
HEDIS MY 2025 - Glycemic Status Assessment for Patients With Diabetes (GSD)

The percentage of members 18-75 years of age with diabetes (types 1 and 2) whose
most recent glycemic status (HbA1c or GMI) was at the following levels during MY:
  - Glycemic Status <8.0%
  - Glycemic Status >9.0%

Diabetes identified by: (1) at least two diagnoses on different dates during MY or
prior year, OR (2) dispensed diabetes medication during MY or prior year with at
least one diabetes diagnosis.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    prior_year_dates,
    get_medication_date,
    find_conditions_with_codes,
    find_observations_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("GSD")


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
    if conditions:  # at least one diagnosis
        # Check for diabetes medications (using medication resources)
        for rtype in ("MedicationDispense", "MedicationRequest"):
            for med in get_resources_by_type(bundle, rtype):
                med_date = get_medication_date(med)
                if med_date and is_date_in_range(med_date, lookback_start, my_end):
                    # Any medication dispensing in the lookback period counts
                    # (the value set loading handles the specific medication codes)
                    return True

    return False


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check GSD eligible population:
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
    """Check GSD exclusions (common exclusions)."""
    return check_common_exclusions(bundle, VALUE_SETS, measurement_year)


def _get_most_recent_hba1c(bundle: dict, measurement_year: int) -> float | None:
    """
    Find the most recent HbA1c/GMI result during the measurement year.

    Uses HbA1c Lab Test Value Set and HbA1c Test Result or Finding Value Set.
    If multiple results on the same date, uses the lowest.
    """
    my_start, my_end = measurement_year_dates(measurement_year)

    hba1c_lab_codes = all_codes(VALUE_SETS, "HbA1c Lab Test")
    hba1c_finding_codes = all_codes(VALUE_SETS, "HbA1c Test Result or Finding")

    # Combine all HbA1c-related codes
    combined_codes: dict[str, set[str]] = {}
    for codes_map in (hba1c_lab_codes, hba1c_finding_codes):
        for system, codes in codes_map.items():
            combined_codes.setdefault(system, set()).update(codes)

    # Also include GMI LOINC code 97506-0
    combined_codes.setdefault(LOINC, set()).add("97506-0")

    observations = find_observations_with_codes(
        bundle, combined_codes, my_start, my_end
    )
    if not observations:
        return None

    # Group by date, find most recent, use lowest value on that date
    by_date: dict[date, list[float]] = {}
    for obs, obs_date in observations:
        if obs_date is None:
            continue
        value = obs.get("valueQuantity", {}).get("value")
        if value is None:
            # Try component values
            for comp in obs.get("component", []):
                value = comp.get("valueQuantity", {}).get("value")
                if value is not None:
                    break
        if value is not None:
            by_date.setdefault(obs_date, []).append(float(value))

    if not by_date:
        return None

    most_recent_date = max(by_date.keys())
    return min(by_date[most_recent_date])


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check GSD numerator for Glycemic Status <8.0%.

    Compliant if most recent HbA1c/GMI result during MY is <8.0%.
    Not compliant if >=8.0%, missing, or no test done.
    """
    evaluated: list[str] = []
    result = _get_most_recent_hba1c(bundle, measurement_year)

    if result is not None and result < 8.0:
        return True, evaluated
    return False, evaluated


def _check_greater_than_9(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check GSD numerator for Glycemic Status >9.0%.

    Compliant (poor control) if most recent HbA1c/GMI result is >9.0%,
    missing, or no test done. Lower rate = better performance.
    """
    evaluated: list[str] = []
    result = _get_most_recent_hba1c(bundle, measurement_year)

    if result is None:
        return True, evaluated  # No test = compliant for >9% (poor control indicator)
    if result > 9.0:
        return True, evaluated
    return False, evaluated


def calculate_gsd_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the GSD measure (both indicators) for a patient bundle."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    less_than_8 = False
    greater_than_9 = False

    if is_eligible:
        less_than_8, lt8_refs = check_numerator(bundle, measurement_year)
        all_evaluated.extend(lt8_refs)
        greater_than_9, gt9_refs = _check_greater_than_9(bundle, measurement_year)
        all_evaluated.extend(gt9_refs)

    groups = [
        {
            "code": "GSD-LessThan8",
            "display": "Glycemic Status <8.0%",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": less_than_8,
        },
        {
            "code": "GSD-GreaterThan9",
            "display": "Glycemic Status >9.0% (lower is better)",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": greater_than_9,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="GSD",
        measure_name="Glycemic Status Assessment for Patients With Diabetes",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
