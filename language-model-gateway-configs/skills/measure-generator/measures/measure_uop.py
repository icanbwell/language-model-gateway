"""
HEDIS MY 2025 - Use of Opioids From Multiple Providers (UOP).

INVERSE measure (lower = better). Three rates:
  1. Multiple Prescribers (>= 4 different prescribers)
  2. Multiple Pharmacies (>= 4 different pharmacies)
  3. Multiple Prescribers AND Multiple Pharmacies

Members 18+ receiving opioids for >= 15 days with 2+ dispensing events.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    find_medications_with_codes,
    build_multi_rate_measure_report,
)

VALUE_SETS = load_value_sets_from_csv("UOP")


def _get_all_opioid_codes() -> dict[str, set[str]]:
    """Aggregate all opioid medication codes from value sets."""
    combined: dict[str, set[str]] = {}
    for vs_name, vs_data in VALUE_SETS.items():
        if "Medications" in vs_name:
            for system, codes in vs_data.items():
                combined.setdefault(system, set()).update(codes)
    return combined


def _get_opioid_meds(bundle: dict, start: date, end: date) -> list[tuple[dict, date]]:
    """Get all opioid medication dispensing events."""
    opioid_codes = _get_all_opioid_codes()
    if not opioid_codes:
        return []
    return find_medications_with_codes(bundle, opioid_codes, start, end)


def _count_unique_prescribers(meds: list[tuple[dict, date]]) -> int:
    """Count unique prescribers by NPI from medication resources."""
    prescribers: set[str] = set()
    unknown_count = 0
    for med, _ in meds:
        # Check performer (MedicationDispense) or requester (MedicationRequest)
        prescriber_ref = None
        for performer in med.get("performer", []):
            actor = performer.get("actor", {})
            prescriber_ref = actor.get("reference", "")
            break
        if not prescriber_ref:
            requester = med.get("requester", {})
            prescriber_ref = requester.get("reference", "")
        if prescriber_ref:
            prescribers.add(prescriber_ref)
        else:
            # Missing NPI counts as new prescriber
            unknown_count += 1
    return len(prescribers) + unknown_count


def _count_unique_pharmacies(meds: list[tuple[dict, date]]) -> int:
    """Count unique pharmacies from medication dispense resources."""
    pharmacies: set[str] = set()
    unknown_count = 0
    for med, _ in meds:
        # Location or contained pharmacy reference
        location_ref = med.get("location", {}).get("reference", "")
        if not location_ref:
            # Check extensions for pharmacy NPI
            for ext in med.get("extension", []):
                if "pharmacy" in ext.get("url", "").lower():
                    location_ref = ext.get("valueReference", {}).get("reference", "")
                    break
        if location_ref:
            pharmacies.add(location_ref)
        else:
            unknown_count += 1
    return len(pharmacies) + unknown_count


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check eligible population: 18+, 2+ opioid dispensing on different dates,
    >= 15 days covered."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 18:
        return False, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)
    events = _get_opioid_meds(bundle, my_start, my_end)

    unique_dates = set(d for _, d in events if d)
    if len(unique_dates) < 2:
        return False, evaluated

    # Calculate days covered
    covered_days: set[date] = set()
    for med, med_date in events:
        if not med_date:
            continue
        supply = int(med.get("daysSupply", {}).get("value", 1) or 1)
        for i in range(supply):
            covered_days.add(med_date + timedelta(days=i))
    if len(covered_days) < 15:
        return False, evaluated

    evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in events)
    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice, death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """This is not used directly - see calculate_uop_measure for multi-rate."""
    return False, []


def calculate_uop_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate UOP measure (3 rates) and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="UOP",
            measure_name="Use of Opioids From Multiple Providers",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "UOP-1",
                    "display": "Multiple Prescribers",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "UOP-2",
                    "display": "Multiple Pharmacies",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "UOP-3",
                    "display": "Multiple Prescribers and Multiple Pharmacies",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    # Get all opioid meds for numerator assessment
    my_start, my_end = measurement_year_dates(measurement_year)
    meds = _get_opioid_meds(bundle, my_start, my_end)

    num_prescribers = _count_unique_prescribers(meds)
    num_pharmacies = _count_unique_pharmacies(meds)

    r1_num = num_prescribers >= 4
    r2_num = num_pharmacies >= 4
    r3_num = r1_num and r2_num

    groups = [
        {
            "code": "UOP-1",
            "display": "Multiple Prescribers",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r1_num,
        },
        {
            "code": "UOP-2",
            "display": "Multiple Pharmacies",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r2_num,
        },
        {
            "code": "UOP-3",
            "display": "Multiple Prescribers and Multiple Pharmacies",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r3_num,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="UOP",
        measure_name="Use of Opioids From Multiple Providers",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
