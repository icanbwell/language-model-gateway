"""
HEDIS MY 2025 - Deprescribing of Benzodiazepines in Older Adults (DBO).

Members 67+ dispensed benzodiazepines who achieved >= 20% decrease in
diazepam milligram equivalent (DME) dose during the measurement year.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    find_conditions_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("DBO")

# All oral benzodiazepine medication value set name patterns
_BENZO_VS_PREFIXES = [
    "Alprazolam",
    "Chlordiazepoxide",
    "Clonazepam",
    "Clorazepate",
    "Diazepam",
    "Estazolam",
    "Flurazepam",
    "Lorazepam",
    "Midazolam",
    "Oxazepam",
    "Quazepam",
    "Temazepam",
    "Triazolam",
]


def _get_all_benzo_codes() -> dict[str, set[str]]:
    """Aggregate all oral benzodiazepine medication codes."""
    combined: dict[str, set[str]] = {}
    for vs_name, vs_data in VALUE_SETS.items():
        for prefix in _BENZO_VS_PREFIXES:
            if vs_name.startswith(prefix):
                for system, codes in vs_data.items():
                    combined.setdefault(system, set()).update(codes)
                break
    return combined


def _get_benzo_dispensing_events(
    bundle: dict, start: date, end: date
) -> list[tuple[dict, date]]:
    """Get all benzo dispensing events in a date range."""
    benzo_codes = _get_all_benzo_codes()
    if not benzo_codes:
        return []
    return find_medications_with_codes(bundle, benzo_codes, start, end)


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check eligible population for DBO.

    Age 67+, 2+ benzo dispensing events on different dates during MY,
    qualifying ITE (30 consecutive covered days starting Jan 1 - Sep 1),
    PDC >= 50% during treatment period.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 67:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)

    # 2+ dispensing events on different dates
    events = _get_benzo_dispensing_events(bundle, my_start, my_end)
    unique_dates = set(d for _, d in events if d)
    if len(unique_dates) < 2:
        return False, evaluated

    evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in events)

    # Simplified ITE check: at least one dispensing event between Jan 1 - Sep 1
    ite_end = date(measurement_year, 9, 1)
    ite_events = [
        (m, d) for m, d in events if d and is_date_in_range(d, my_start, ite_end)
    ]
    if not ite_events:
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions for DBO.

    - Seizure disorders, REM sleep behavior disorder, benzo withdrawal,
      ethanol withdrawal (Jan 1 prior year through ITE start date)
    - Hospice, death, palliative care
    """
    all_evaluated: list[str] = []

    # Common exclusions
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    py_start = date(measurement_year - 1, 1, 1)
    my_start, _ = measurement_year_dates(measurement_year)
    # Use MY start as proxy for ITE start date
    for vs_name in (
        "Seizure Disorders",
        "REM Sleep Behavior Disorder",
        "Benzodiazepine Withdrawal",
        "Alcohol Withdrawal",
    ):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes:
            matches = find_conditions_with_codes(bundle, codes, py_start, my_start)
            if matches:
                all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
                return True, all_evaluated

    return False, all_evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: >= 20% decrease in DME daily dose or discontinuation.

    Simplified: checks if the ending dispensing event has lower quantity/days
    supply ratio compared to earliest, or if no dispensing in last 60 days of MY.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    events = _get_benzo_dispensing_events(bundle, my_start, my_end)
    if not events:
        return False, evaluated

    # Sort by date
    dated_events = [(m, d) for m, d in events if d]
    dated_events.sort(key=lambda x: x[1])

    if not dated_events:
        return False, evaluated

    # Check for discontinuation: no dispensing in last 60 days of MY
    last_dispense_date = dated_events[-1][1]
    if (my_end - last_dispense_date).days >= 60:
        evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in dated_events)
        return True, evaluated

    # Simplified dose comparison using quantity / days supply
    first_med = dated_events[0][0]
    last_med = dated_events[-1][0]

    first_qty = first_med.get("quantity", {}).get("value", 0)
    first_supply = (first_med.get("daysSupply", {}).get("value", 1)) or 1
    last_qty = last_med.get("quantity", {}).get("value", 0)
    last_supply = (last_med.get("daysSupply", {}).get("value", 1)) or 1

    if first_qty and first_supply:
        starting_rate = first_qty / first_supply
        ending_rate = last_qty / last_supply if last_qty else 0
        if starting_rate > 0:
            pct_reduction = (starting_rate - ending_rate) / starting_rate * 100
            if pct_reduction >= 20:
                evaluated.extend(
                    f"MedicationDispense/{m.get('id')}" for m, _ in dated_events
                )
                return True, evaluated

    return False, evaluated


def calculate_dbo_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate DBO measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="DBO",
        measure_name="Deprescribing of Benzodiazepines in Older Adults",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
