"""
HEDIS MY 2025 - Eye Exam for Patients With Diabetes (EED)

The percentage of members 18-75 years of age with diabetes (types 1 and 2)
who had a retinal eye exam. Screening or monitoring for diabetic retinal disease
includes:
  - Retinal/dilated eye exam by an eye care professional during MY
  - Negative retinal exam (no retinopathy) by eye care professional in PY
  - Eye exam with/without evidence of retinopathy during MY
  - Retinal imaging with interpretation during MY
  - Autonomous eye exam (CPT 92229) during MY
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
    CPT,
)

VALUE_SETS = load_value_sets_from_csv("EED")


def _has_diabetes(bundle: dict, measurement_year: int) -> bool:
    """
    Identify members with diabetes via claims/encounter data or pharmacy data.
    """
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
    Check EED eligible population:
    - Age 18-75 as of Dec 31 of MY
    - Has diabetes
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
    """
    Check EED exclusions:
    - Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    - Bilateral absence of eyes (SNOMED 15665641000119103) any time through Dec 31 MY
    - Bilateral eye enucleation any time through Dec 31 MY
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    _, my_end = measurement_year_dates(measurement_year)
    far_past = date(1900, 1, 1)

    # Bilateral eye enucleation
    enucleation_codes = all_codes(VALUE_SETS, "Unilateral Eye Enucleation")
    if enucleation_codes:
        procedures = find_procedures_with_codes(
            bundle, enucleation_codes, far_past, my_end
        )
        # Two unilateral enucleations with dates >= 14 days apart
        if len(procedures) >= 2:
            proc_dates = sorted([d for _, d in procedures if d is not None])
            if len(proc_dates) >= 2:
                if (proc_dates[-1] - proc_dates[0]).days >= 14:
                    return True, refs

    return False, refs


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check EED numerator: retinal eye exam screening or monitoring.

    Any of the following meet criteria:
    - Retinal Eye Exams during MY
    - Eye Exam With Evidence of Retinopathy during MY
    - Eye Exam Without Evidence of Retinopathy during MY or PY (negative = PY OK)
    - Retinal Imaging during MY
    - Autonomous eye exam (CPT 92229) during MY
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    # Retinal Eye Exams during MY
    retinal_codes = all_codes(VALUE_SETS, "Retinal Eye Exams")
    if retinal_codes:
        if find_procedures_with_codes(bundle, retinal_codes, my_start, my_end):
            return True, evaluated
        if find_observations_with_codes(bundle, retinal_codes, my_start, my_end):
            return True, evaluated

    # Eye Exam With Evidence of Retinopathy during MY
    with_retinopathy = all_codes(VALUE_SETS, "Eye Exam With Evidence of Retinopathy")
    if with_retinopathy:
        if find_procedures_with_codes(bundle, with_retinopathy, my_start, my_end):
            return True, evaluated
        if find_observations_with_codes(bundle, with_retinopathy, my_start, my_end):
            return True, evaluated

    # Eye Exam Without Evidence of Retinopathy during MY or PY
    without_retinopathy = all_codes(
        VALUE_SETS, "Eye Exam Without Evidence of Retinopathy"
    )
    if without_retinopathy:
        if find_procedures_with_codes(bundle, without_retinopathy, my_start, my_end):
            return True, evaluated
        if find_observations_with_codes(bundle, without_retinopathy, my_start, my_end):
            return True, evaluated
        # Negative exam in prior year also qualifies
        if find_procedures_with_codes(bundle, without_retinopathy, py_start, py_end):
            return True, evaluated
        if find_observations_with_codes(bundle, without_retinopathy, py_start, py_end):
            return True, evaluated

    # Retinal Imaging during MY
    retinal_imaging = all_codes(VALUE_SETS, "Retinal Imaging")
    if retinal_imaging:
        if find_procedures_with_codes(bundle, retinal_imaging, my_start, my_end):
            return True, evaluated

    # Autonomous eye exam CPT 92229 during MY
    autonomous_codes: dict[str, set[str]] = {CPT: {"92229"}}
    if find_procedures_with_codes(bundle, autonomous_codes, my_start, my_end):
        return True, evaluated

    return False, evaluated


def calculate_eed_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the EED measure for a patient bundle."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="EED",
        measure_name="Eye Exam for Patients With Diabetes",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
