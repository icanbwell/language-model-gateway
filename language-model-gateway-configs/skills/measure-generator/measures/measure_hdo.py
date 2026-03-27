"""
HEDIS MY 2025 - Use of Opioids at High Dosage (HDO).

INVERSE measure (lower = better).
Members 18+ who received prescription opioids at high dosage (avg MME >= 90)
for >= 15 days during the measurement year.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    find_conditions_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("HDO")


def _get_all_opioid_codes() -> dict[str, set[str]]:
    """Aggregate all opioid medication codes from value sets."""
    combined: dict[str, set[str]] = {}
    for vs_name, vs_data in VALUE_SETS.items():
        if "Medications" in vs_name or "Medications List" in vs_name:
            # Skip non-medication value sets
            for system, codes in vs_data.items():
                combined.setdefault(system, set()).update(codes)
    return combined


def _get_opioid_dispensing_events(
    bundle: dict, start: date, end: date
) -> list[tuple[dict, date]]:
    """Get all opioid dispensing events in a date range."""
    opioid_codes = _get_all_opioid_codes()
    if not opioid_codes:
        return []
    return find_medications_with_codes(bundle, opioid_codes, start, end)


def _calculate_total_days_covered(events: list[tuple[dict, date]]) -> int:
    """Calculate total days covered by opioid medications."""
    if not events:
        return 0

    covered_days: set[date] = set()
    for med, med_date in events:
        if not med_date:
            continue
        days_supply = med.get("daysSupply", {}).get("value", 1) or 1
        for i in range(int(days_supply)):
            covered_days.add(med_date + __import__("datetime").timedelta(days=i))

    return len(covered_days)


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check eligible population: 18+ with 2+ opioid dispensing events
    on different dates and >= 15 total days covered."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 18:
        return False, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)
    events = _get_opioid_dispensing_events(bundle, my_start, my_end)

    # 2+ events on different dates
    unique_dates = set(d for _, d in events if d)
    if len(unique_dates) < 2:
        return False, evaluated

    # >= 15 days covered
    total_days = _calculate_total_days_covered(events)
    if total_days < 15:
        return False, evaluated

    evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in events)
    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: cancer, sickle cell, palliative, hospice, death."""
    all_evaluated: list[str] = []

    # Common exclusions (hospice, death, palliative)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    my_start, my_end = measurement_year_dates(measurement_year)

    # Cancer
    cancer_codes = all_codes(VALUE_SETS, "Malignant Neoplasms")
    if cancer_codes:
        matches = find_conditions_with_codes(bundle, cancer_codes, my_start, my_end)
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    # Sickle cell disease
    sickle_codes = all_codes(VALUE_SETS, "Sickle Cell Anemia and HB S Disease")
    if sickle_codes:
        matches = find_conditions_with_codes(bundle, sickle_codes, my_start, my_end)
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    return False, all_evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: average MME >= 90 during treatment period.

    Simplified: estimates based on quantity and days supply.
    INVERSE - numerator hit = bad outcome (high dosage opioid use).
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    events = _get_opioid_dispensing_events(bundle, my_start, my_end)
    if not events:
        return False, evaluated

    # Simplified MME estimation
    # In a full implementation, each medication would be mapped to its
    # MME conversion factor from the HDO-A table. Here we use a proxy:
    # total quantity dispensed as a rough indicator.
    total_quantity = 0
    total_days = 0
    for med, med_date in events:
        qty = med.get("quantity", {}).get("value", 0) or 0
        supply = med.get("daysSupply", {}).get("value", 0) or 0
        total_quantity += qty
        total_days += supply

    if total_days > 0:
        # Average daily dose (proxy - actual implementation needs MME factors)
        avg_daily = total_quantity / total_days
        # Using a simplified threshold - actual needs per-drug MME conversion
        if avg_daily >= 90:
            evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in events)
            return True, evaluated

    return False, evaluated


def calculate_hdo_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate HDO measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="HDO",
        measure_name="Use of Opioids at High Dosage",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
