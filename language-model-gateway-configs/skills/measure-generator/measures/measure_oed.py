"""
HEDIS MY 2025 - Oral Evaluation, Dental Services (OED).

The percentage of members under 21 years of age who received a comprehensive
or periodic oral evaluation with a dental provider during the measurement year.
"""

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    find_encounters_with_codes,
    find_procedures_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("OED")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: under 21 years as of Dec 31 of the measurement year.
    No event/diagnosis required.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age >= 21:
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
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    A comprehensive or periodic oral evaluation (Oral Evaluation Value Set)
    with a dental provider (Dental Provider Value Set) during the measurement
    year.

    Note: In administrative data, the dental provider is typically identified
    by the rendering provider taxonomy on the claim. For FHIR bundle
    evaluation, we check for the presence of an oral evaluation code during
    the measurement year as a proxy.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    oral_eval_codes = all_codes(VALUE_SETS, "Oral Evaluation")
    if not oral_eval_codes:
        return False, evaluated

    # Check encounters with oral evaluation codes
    enc_hits = find_encounters_with_codes(bundle, oral_eval_codes, my_start, my_end)
    if enc_hits:
        for enc, _ in enc_hits:
            evaluated.append(f"Encounter/{enc.get('id')}")
        return True, evaluated

    # Check procedures with oral evaluation codes
    proc_hits = find_procedures_with_codes(bundle, oral_eval_codes, my_start, my_end)
    if proc_hits:
        for proc, _ in proc_hits:
            evaluated.append(f"Procedure/{proc.get('id')}")
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_oed_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the OED measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="OED",
        measure_name="Oral Evaluation, Dental Services",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
