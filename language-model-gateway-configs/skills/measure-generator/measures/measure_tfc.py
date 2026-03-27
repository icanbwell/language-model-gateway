"""
HEDIS MY 2025 - Topical Fluoride for Children (TFC).

The percentage of members 1-4 years of age who received at least two fluoride
varnish applications during the measurement year.
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

VALUE_SETS = load_value_sets_from_csv("TFC")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: 1-4 years as of Dec 31 of the measurement year.
    No event/diagnosis required.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 1 or age > 4:
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
    Two or more fluoride varnish applications (Application of Fluoride Varnish
    Value Set) during the measurement year, on different dates of service.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    fluoride_codes = all_codes(VALUE_SETS, "Application of Fluoride Varnish")
    if not fluoride_codes:
        return False, evaluated

    # Collect all fluoride application dates
    application_dates: set = set()

    proc_hits = find_procedures_with_codes(bundle, fluoride_codes, my_start, my_end)
    for proc, proc_date in proc_hits:
        if proc_date:
            application_dates.add(proc_date)
            evaluated.append(f"Procedure/{proc.get('id')}")

    enc_hits = find_encounters_with_codes(bundle, fluoride_codes, my_start, my_end)
    for enc, enc_date in enc_hits:
        if enc_date:
            application_dates.add(enc_date)
            evaluated.append(f"Encounter/{enc.get('id')}")

    if len(application_dates) >= 2:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_tfc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the TFC measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="TFC",
        measure_name="Topical Fluoride for Children",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
