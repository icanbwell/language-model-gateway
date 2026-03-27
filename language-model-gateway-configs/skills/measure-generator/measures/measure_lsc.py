"""
HEDIS MY 2025 - Lead Screening in Children (LSC).

The percentage of children 2 years of age who had one or more capillary or
venous lead blood test for lead poisoning by their second birthday.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    is_date_in_range,
    measurement_year_dates,
    find_observations_with_codes,
    find_procedures_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("LSC")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: children who turn 2 years old during the measurement year.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)

    # Child turns 2 during the measurement year means their 2nd birthday
    # falls between Jan 1 and Dec 31 of the measurement year.
    second_birthday = date(birth_date.year + 2, birth_date.month, birth_date.day)
    if not is_date_in_range(second_birthday, my_start, my_end):
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
    At least one lead capillary or venous blood test (Lead Tests Value Set)
    on or before the child's second birthday.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    second_birthday = date(birth_date.year + 2, birth_date.month, birth_date.day)
    # Search from birth through second birthday
    search_start = birth_date
    search_end = second_birthday

    lead_codes = all_codes(VALUE_SETS, "Lead Tests")
    if not lead_codes:
        return False, evaluated

    # Check observations (lab results)
    obs_hits = find_observations_with_codes(
        bundle, lead_codes, search_start, search_end
    )
    if obs_hits:
        for obs, _ in obs_hits:
            evaluated.append(f"Observation/{obs.get('id')}")
        return True, evaluated

    # Check procedures
    proc_hits = find_procedures_with_codes(bundle, lead_codes, search_start, search_end)
    if proc_hits:
        for proc, _ in proc_hits:
            evaluated.append(f"Procedure/{proc.get('id')}")
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_lsc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the LSC measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="LSC",
        measure_name="Lead Screening in Children",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
