"""
HEDIS MY 2025 - Kidney Health Evaluation for Patients With Diabetes (KED)

The percentage of members 18-85 years of age with diabetes (type 1 and type 2)
who received a kidney health evaluation, defined by an estimated glomerular
filtration rate (eGFR) AND a urine albumin-creatinine ratio (uACR), during the
measurement year.

Both tests must be performed during the measurement year (same or different dates).
uACR can be identified by either:
  - Both a quantitative urine albumin test AND a urine creatinine test with
    service dates 4 days or less apart, OR
  - A uACR lab test
"""

from datetime import date

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
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("KED")


def _has_diabetes(bundle: dict, measurement_year: int) -> bool:
    """Identify members with diabetes via claims/encounter data or pharmacy data."""
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, _ = prior_year_dates(measurement_year)
    lookback_start = py_start

    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")
    if not diabetes_codes:
        return False

    conditions = find_conditions_with_codes(
        bundle, diabetes_codes, lookback_start, my_end
    )
    onset_dates = sorted({d for _, d in conditions if d is not None})
    if len(onset_dates) >= 2:
        return True

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
    Check KED eligible population:
    - Age 18-85 as of Dec 31 of MY
    - Has diabetes
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (18 <= age <= 85):
        return False, evaluated

    if not _has_diabetes(bundle, measurement_year):
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check KED exclusions:
    - Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    - ESRD diagnosis any time through Dec 31 MY
    - Dialysis any time through Dec 31 MY
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    _, my_end = measurement_year_dates(measurement_year)
    far_past = date(1900, 1, 1)

    # ESRD diagnosis any time through end of MY
    esrd_codes = all_codes(VALUE_SETS, "ESRD Diagnosis")
    if esrd_codes and find_conditions_with_codes(bundle, esrd_codes, far_past, my_end):
        return True, refs

    # Dialysis any time through end of MY
    dialysis_codes = all_codes(VALUE_SETS, "Dialysis Procedure")
    if dialysis_codes and find_procedures_with_codes(
        bundle, dialysis_codes, far_past, my_end
    ):
        return True, refs

    return False, refs


def _has_egfr(bundle: dict, measurement_year: int) -> bool:
    """Check for at least one eGFR lab test during the measurement year."""
    my_start, my_end = measurement_year_dates(measurement_year)
    egfr_codes = all_codes(VALUE_SETS, "Estimated Glomerular Filtration Rate Lab Test")
    if not egfr_codes:
        return False
    return bool(find_observations_with_codes(bundle, egfr_codes, my_start, my_end))


def _has_uacr(bundle: dict, measurement_year: int) -> bool:
    """
    Check for uACR during the measurement year.

    Either:
    - A uACR lab test (Urine Albumin Creatinine Ratio Lab Test), OR
    - Both a quantitative urine albumin test AND a urine creatinine test
      with service dates 4 days or less apart
    """
    my_start, my_end = measurement_year_dates(measurement_year)

    # Direct uACR test
    uacr_codes = all_codes(VALUE_SETS, "Urine Albumin Creatinine Ratio Lab Test")
    if uacr_codes and find_observations_with_codes(
        bundle, uacr_codes, my_start, my_end
    ):
        return True

    # Component tests: urine albumin + urine creatinine within 4 days
    albumin_codes = all_codes(VALUE_SETS, "Quantitative Urine Albumin Lab Test")
    creatinine_codes = all_codes(VALUE_SETS, "Urine Creatinine Lab Test")

    if not albumin_codes or not creatinine_codes:
        return False

    albumin_obs = find_observations_with_codes(bundle, albumin_codes, my_start, my_end)
    creatinine_obs = find_observations_with_codes(
        bundle, creatinine_codes, my_start, my_end
    )

    albumin_dates = [d for _, d in albumin_obs if d is not None]
    creatinine_dates = [d for _, d in creatinine_obs if d is not None]

    for a_date in albumin_dates:
        for c_date in creatinine_dates:
            if abs((a_date - c_date).days) <= 4:
                return True

    return False


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check KED numerator: both eGFR AND uACR during the measurement year.
    """
    evaluated: list[str] = []

    has_egfr = _has_egfr(bundle, measurement_year)
    has_uacr = _has_uacr(bundle, measurement_year)

    if has_egfr and has_uacr:
        return True, evaluated

    return False, evaluated


def calculate_ked_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the KED measure for a patient bundle."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="KED",
        measure_name="Kidney Health Evaluation for Patients With Diabetes",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
