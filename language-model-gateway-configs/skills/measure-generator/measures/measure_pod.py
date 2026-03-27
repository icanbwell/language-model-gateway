"""
HEDIS MY 2025 - Pharmacotherapy for Opioid Use Disorder (POD)

The percentage of opioid use disorder (OUD) pharmacotherapy events that lasted
at least 180 days among members 16 years of age and older with a diagnosis of
OUD and a new OUD pharmacotherapy event.
"""

from datetime import date, timedelta
from typing import Any

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_medication_date,
    medication_has_code,
    find_conditions_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("POD")

# OUD medication value set names used in the measure
OUD_MED_VS_NAMES = [
    "Naltrexone Injection",
    "Buprenorphine Oral",
    "Buprenorphine Oral Weekly",
    "Buprenorphine Injection",
    "Buprenorphine Implant",
    "Buprenorphine Naloxone",
    "Methadone Oral",
    "Methadone Oral Weekly",
]

# Days supply per value set
DAYS_SUPPLY_MAP = {
    "Naltrexone Injection": 31,
    "Buprenorphine Oral": 1,
    "Buprenorphine Oral Weekly": 7,
    "Buprenorphine Injection": 31,
    "Buprenorphine Implant": 180,
    "Buprenorphine Naloxone": 1,
    "Methadone Oral": 1,
    "Methadone Oral Weekly": 7,
}


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def _get_all_oud_med_codes() -> dict[str, set[str]]:
    """Combine all OUD medication value set codes."""
    combined: dict[str, set[str]] = {}
    for vs_name in OUD_MED_VS_NAMES:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _find_oud_med_events(bundle: dict, start: date, end: date) -> list[dict[str, Any]]:
    """Find all OUD medication dispensing/administration events in date range."""
    events: list[dict[str, Any]] = []
    combined_codes = _get_all_oud_med_codes()

    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date or not is_date_in_range(med_date, start, end):
                continue
            if medication_has_code(med, combined_codes):
                # Determine days supply
                days_supply = None
                if rtype == "MedicationDispense":
                    ds = med.get("daysSupply", {}).get("value")
                    if ds:
                        days_supply = int(ds)
                if not days_supply:
                    # Use default from value set
                    for vs_name in OUD_MED_VS_NAMES:
                        vs_codes = all_codes(VALUE_SETS, vs_name)
                        if medication_has_code(med, vs_codes):
                            days_supply = DAYS_SUPPLY_MAP.get(vs_name, 1)
                            break
                if not days_supply:
                    days_supply = 7  # Default for buprenorphine oral

                events.append(
                    {
                        "date": med_date,
                        "days_supply": days_supply,
                        "ref": f"{rtype}/{med.get('id', 'unknown')}",
                    }
                )

    # Also check encounters/procedures for OUD administration
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, start, end):
            continue
        for vs_name in OUD_MED_VS_NAMES:
            vs_codes = all_codes(VALUE_SETS, vs_name)
            if resource_has_any_code(enc, vs_codes) or any(
                codeable_concept_has_any_code(t, vs_codes) for t in enc.get("type", [])
            ):
                events.append(
                    {
                        "date": enc_date,
                        "days_supply": DAYS_SUPPLY_MAP.get(vs_name, 1),
                        "ref": f"Encounter/{enc.get('id', 'unknown')}",
                    }
                )
                break

    return sorted(events, key=lambda e: e["date"])


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check for OUD diagnosis + new pharmacotherapy event during intake period.
    Intake: July 1 prior year to June 30 of measurement year.
    Age >= 16 at treatment period start date.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    intake_start = date(measurement_year - 1, 7, 1)
    intake_end = date(measurement_year, 6, 30)

    # Step 1: OUD diagnosis during intake period
    oud_codes = all_codes(VALUE_SETS, "Opioid Abuse and Dependence")
    oud_conditions = find_conditions_with_codes(
        bundle, oud_codes, intake_start, intake_end
    )
    # Also check encounter diagnoses
    has_oud_dx = len(oud_conditions) > 0
    if not has_oud_dx:
        for enc in get_resources_by_type(bundle, "Encounter"):
            enc_date = get_encounter_date(enc)
            if not enc_date or not is_date_in_range(enc_date, intake_start, intake_end):
                continue
            if resource_has_any_code(enc, oud_codes) or any(
                codeable_concept_has_any_code(t, oud_codes) for t in enc.get("type", [])
            ):
                has_oud_dx = True
                break
            for dx in enc.get("diagnosis", []):
                cc = dx.get("condition", {}).get("concept", {})
                if cc and codeable_concept_has_any_code(cc, oud_codes):
                    has_oud_dx = True
                    break
            if has_oud_dx:
                break

    if not has_oud_dx:
        return False, evaluated

    # Step 2: Find OUD med events during intake period
    med_events = _find_oud_med_events(bundle, intake_start, intake_end)
    if not med_events:
        return False, evaluated

    # Step 3: Test for negative medication history (31 days prior with no OUD meds)
    for event in med_events:
        lookback_start = event["date"] - timedelta(days=31)
        lookback_end = event["date"] - timedelta(days=1)
        prior_events = _find_oud_med_events(bundle, lookback_start, lookback_end)
        if not prior_events:
            # Has negative medication history - this is a treatment period start date
            age = calculate_age(birth_date, event["date"])
            if age >= 16:
                evaluated.append(event["ref"])
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check hospice and death exclusions."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check if OUD pharmacotherapy lasted 180+ days without a gap of 8+ consecutive
    days during the treatment period.
    """
    evaluated: list[str] = []

    intake_start = date(measurement_year - 1, 7, 1)
    intake_end = date(measurement_year, 6, 30)

    # Find the treatment period start date
    med_events = _find_oud_med_events(bundle, intake_start, intake_end)
    treatment_start = None

    for event in med_events:
        lookback_start = event["date"] - timedelta(days=31)
        lookback_end = event["date"] - timedelta(days=1)
        prior_events = _find_oud_med_events(bundle, lookback_start, lookback_end)
        if not prior_events:
            treatment_start = event["date"]
            evaluated.append(event["ref"])
            break

    if not treatment_start:
        return False, evaluated

    treatment_end = treatment_start + timedelta(days=179)

    # Find all OUD med events during the treatment period
    treatment_events = _find_oud_med_events(bundle, treatment_start, treatment_end)
    for ev in treatment_events:
        evaluated.append(ev["ref"])

    # Build set of covered days
    covered_days: set[int] = set()
    for event in treatment_events:
        event_start_offset = (event["date"] - treatment_start).days
        for d in range(event["days_supply"]):
            day_offset = event_start_offset + d
            if 0 <= day_offset < 180:
                covered_days.add(day_offset)

    # Check for gaps of 8+ consecutive days
    has_large_gap = False
    consecutive_gap = 0
    for day in range(180):
        if day not in covered_days:
            consecutive_gap += 1
            if consecutive_gap >= 8:
                has_large_gap = True
                break
        else:
            consecutive_gap = 0

    return not has_large_gap, list(dict.fromkeys(evaluated))


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_pod_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the POD measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="POD",
        measure_name="Pharmacotherapy for Opioid Use Disorder",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
