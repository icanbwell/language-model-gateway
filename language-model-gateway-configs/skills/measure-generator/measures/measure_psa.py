"""
HEDIS MY 2025 - Non-Recommended PSA-Based Screening in Older Men (PSA).

INVERSE measure: numerator = PSA screening occurred (lower rate = better).
Men 70+ who were screened unnecessarily using PSA-based screening.
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
    resource_has_any_code,
    get_observation_date,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("PSA")


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if the patient is in the eligible population for PSA.

    Eligible: Men 70+ as of Dec 31 of the measurement year.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 70:
        return False, evaluated

    gender = get_patient_gender(bundle)
    if gender != "male":
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions for PSA.

    - Hospice / death
    - Prostate cancer diagnosis (any time through Dec 31 MY)
    - Prostate dysplasia (MY or year prior)
    - Elevated PSA lab result (>4.0 ng/mL) in year prior
    - Abnormal PSA test result/finding in year prior
    - Dispensed 5-ARI medication during MY
    """
    all_evaluated: list[str] = []

    # Common exclusions (hospice + death only, no frailty)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    # Prostate cancer - any time through Dec 31 MY
    prostate_cancer_codes = all_codes(VALUE_SETS, "Prostate Cancer")
    if prostate_cancer_codes:
        history_start = date(1900, 1, 1)
        matches = find_conditions_with_codes(
            bundle, prostate_cancer_codes, history_start, my_end
        )
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    # Prostate dysplasia - MY or year prior
    dysplasia_codes = all_codes(VALUE_SETS, "Prostate Dysplasia")
    if dysplasia_codes:
        matches = find_conditions_with_codes(bundle, dysplasia_codes, py_start, my_end)
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    # Elevated PSA lab result in year prior (>4.0 ng/mL)
    psa_lab_excl_codes = all_codes(VALUE_SETS, "PSA Lab Test Exclusion")
    if psa_lab_excl_codes:
        for obs in get_resources_by_type(bundle, "Observation"):
            obs_date = get_observation_date(obs)
            if not is_date_in_range(obs_date, py_start, py_end):
                continue
            if resource_has_any_code(obs, psa_lab_excl_codes):
                value = obs.get("valueQuantity", {}).get("value")
                if value is not None and value > 4.0:
                    all_evaluated.append(f"Observation/{obs.get('id')}")
                    return True, all_evaluated

    # Abnormal PSA test result or finding in year prior
    abnormal_psa_codes = all_codes(VALUE_SETS, "Abnormal PSA Test Result or Finding")
    if abnormal_psa_codes:
        matches = find_observations_with_codes(
            bundle, abnormal_psa_codes, py_start, py_end
        )
        if matches:
            all_evaluated.extend(f"Observation/{o.get('id')}" for o, _ in matches)
            return True, all_evaluated
        cond_matches = find_conditions_with_codes(
            bundle, abnormal_psa_codes, py_start, py_end
        )
        if cond_matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in cond_matches)
            return True, all_evaluated

    # 5-ARI medications during MY
    ari_codes = all_codes(VALUE_SETS, "5 Alpha Reductase Inhibitor Medications")
    if not ari_codes:
        ari_codes = all_codes(VALUE_SETS, "5-ARI Medications")
    if ari_codes:
        matches = find_medications_with_codes(bundle, ari_codes, my_start, my_end)
        if matches:
            all_evaluated.extend(
                f"MedicationDispense/{m.get('id')}" for m, _ in matches
            )
            return True, all_evaluated

    return False, all_evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: PSA-based screening test during the measurement year.

    Note: this is an INVERSE measure - numerator hit = bad outcome.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    # PSA Lab Test
    psa_lab_codes = all_codes(VALUE_SETS, "PSA Lab Test")
    if psa_lab_codes:
        matches = find_observations_with_codes(bundle, psa_lab_codes, my_start, my_end)
        if matches:
            evaluated.extend(f"Observation/{o.get('id')}" for o, _ in matches)
            return True, evaluated
        proc_matches = find_procedures_with_codes(
            bundle, psa_lab_codes, my_start, my_end
        )
        if proc_matches:
            evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
            return True, evaluated

    # PSA Test Result or Finding
    psa_result_codes = all_codes(VALUE_SETS, "PSA Test Result or Finding")
    if psa_result_codes:
        matches = find_observations_with_codes(
            bundle, psa_result_codes, my_start, my_end
        )
        if matches:
            evaluated.extend(f"Observation/{o.get('id')}" for o, _ in matches)
            return True, evaluated
        cond_matches = find_conditions_with_codes(
            bundle, psa_result_codes, my_start, my_end
        )
        if cond_matches:
            evaluated.extend(f"Condition/{c.get('id')}" for c, _ in cond_matches)
            return True, evaluated

    return False, evaluated


def calculate_psa_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate PSA measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="PSA",
        measure_name="Non-Recommended PSA-Based Screening in Older Men",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
