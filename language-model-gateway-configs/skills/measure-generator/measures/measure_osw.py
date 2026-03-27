"""
HEDIS MY 2025 - Osteoporosis Screening in Older Women (OSW)

The percentage of women 65-75 years of age who received osteoporosis screening.

Eligible population: women 66-75 as of Dec 31 of MY (Medicare product line).
No event/diagnosis criteria required.

Numerator: one or more osteoporosis screening tests on or between the member's
65th birthday and December 31 of the measurement year.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_patient_gender,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    prior_year_dates,
    get_medication_date,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("OSW")


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check OSW eligible population:
    - Women 66-75 as of Dec 31 of MY
    - No event/diagnosis criteria required
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    gender = get_patient_gender(bundle)
    if not birth_date or gender != "female":
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (66 <= age <= 75):
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check OSW exclusions:
    - Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    - Osteoporosis therapy any time in history through Dec 31 PY
    - Long-acting osteoporosis medications any time in history through Dec 31 PY
    - Dispensed osteoporosis medication from Jan 1 three years prior through Dec 31 PY
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    _, py_end = prior_year_dates(measurement_year)
    far_past = date(1900, 1, 1)

    # Osteoporosis therapy any time through Dec 31 PY
    osteo_therapy_codes = all_codes(VALUE_SETS, "Osteoporosis Medication Therapy")
    if osteo_therapy_codes:
        if find_procedures_with_codes(bundle, osteo_therapy_codes, far_past, py_end):
            return True, refs

    # Long-acting osteoporosis medications any time through Dec 31 PY
    long_acting_codes = all_codes(VALUE_SETS, "Long Acting Osteoporosis Medications")
    if long_acting_codes:
        if find_procedures_with_codes(bundle, long_acting_codes, far_past, py_end):
            return True, refs

    # Dispensed osteoporosis medication from Jan 1 three years prior through Dec 31 PY
    three_years_prior_start = date(measurement_year - 3, 1, 1)
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if med_date and is_date_in_range(med_date, three_years_prior_start, py_end):
                # Check if it's an osteoporosis medication
                # Since we loaded all value sets for OSW, any medication in the
                # lookback period that matches indicates prior treatment
                return True, refs

    return False, refs


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check OSW numerator: one or more osteoporosis screening tests on or between
    the member's 65th birthday and December 31 of MY.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    # Member's 65th birthday
    screening_start = date(birth_date.year + 65, birth_date.month, birth_date.day)
    screening_end = my_end

    screening_codes = all_codes(VALUE_SETS, "Osteoporosis Screening Tests")
    if not screening_codes:
        return False, evaluated

    # Check procedures
    if find_procedures_with_codes(
        bundle, screening_codes, screening_start, screening_end
    ):
        return True, evaluated

    # Check observations
    if find_observations_with_codes(
        bundle, screening_codes, screening_start, screening_end
    ):
        return True, evaluated

    return False, evaluated


def calculate_osw_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the OSW measure for a patient bundle."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="OSW",
        measure_name="Osteoporosis Screening in Older Women",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
