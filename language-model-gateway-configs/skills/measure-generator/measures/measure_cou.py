"""
HEDIS MY 2025 - Risk of Continued Opioid Use (COU).

INVERSE measure (lower = better). Two rates:
  1. >= 15 days covered by opioids in a 30-day period (IPSD through 29 days after)
  2. >= 31 days covered by opioids in a 62-day period (IPSD through 61 days after)

Members 18+ with a new opioid episode.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    calculate_age,
    find_medications_with_codes,
    find_conditions_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("COU")


def _get_all_opioid_codes() -> dict[str, set[str]]:
    """Aggregate all opioid medication codes."""
    combined: dict[str, set[str]] = {}
    for vs_name, vs_data in VALUE_SETS.items():
        if "Medications" in vs_name:
            for system, codes in vs_data.items():
                combined.setdefault(system, set()).update(codes)
    return combined


def _find_ipsd(bundle: dict, measurement_year: int) -> date | None:
    """Find the Index Prescription Start Date (IPSD).

    Earliest opioid dispensing date during the intake period
    (Nov 1 prior year - Oct 31 measurement year) with 180-day negative
    medication history.
    """
    intake_start = date(measurement_year - 1, 11, 1)
    intake_end = date(measurement_year, 10, 31)

    opioid_codes = _get_all_opioid_codes()
    if not opioid_codes:
        return None

    events = find_medications_with_codes(bundle, opioid_codes, intake_start, intake_end)
    if not events:
        return None

    # Sort by date to find earliest
    dated = [(m, d) for m, d in events if d]
    dated.sort(key=lambda x: x[1])

    for med, med_date in dated:
        # Check 180-day negative medication history
        lookback_start = med_date - timedelta(days=180)
        lookback_end = med_date - timedelta(days=1)
        prior = find_medications_with_codes(
            bundle, opioid_codes, lookback_start, lookback_end
        )
        if not prior:
            return med_date

    return None


def _calculate_covered_days(
    bundle: dict, opioid_codes: dict[str, set[str]], start: date, end: date
) -> int:
    """Calculate covered days in a period."""
    events = find_medications_with_codes(bundle, opioid_codes, start, end)
    covered: set[date] = set()
    for med, med_date in events:
        if not med_date:
            continue
        supply = int(med.get("daysSupply", {}).get("value", 1) or 1)
        for i in range(supply):
            d = med_date + timedelta(days=i)
            if start <= d <= end:
                covered.add(d)
    return len(covered)


def calculate_cou_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate COU measure (2 rates) and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    # Check age: 18+ as of Nov 1 of prior year
    birth_date = get_patient_birth_date(bundle)
    age_ref = date(measurement_year - 1, 11, 1)
    is_eligible = False

    if birth_date:
        age = calculate_age(birth_date, age_ref)
        if age >= 18:
            ipsd = _find_ipsd(bundle, measurement_year)
            if ipsd:
                is_eligible = True

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="COU",
            measure_name="Risk of Continued Opioid Use",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "COU-1",
                    "display": ">=15 Days Covered",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "COU-2",
                    "display": ">=31 Days Covered",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    ipsd = _find_ipsd(bundle, measurement_year)
    assert ipsd is not None

    # Check exclusions
    is_excluded = False
    excl_refs: list[str] = []

    # Common exclusions (hospice, death)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(refs)
    if excluded:
        is_excluded = True

    # Cancer, sickle cell, palliative care (365 days prior to IPSD through 61 days after)
    if not is_excluded:
        excl_start = ipsd - timedelta(days=365)
        excl_end = ipsd + timedelta(days=61)
        for vs_name in ("Malignant Neoplasms", "Sickle Cell Anemia and HB S Disease"):
            codes = all_codes(VALUE_SETS, vs_name)
            if codes:
                matches = find_conditions_with_codes(
                    bundle, codes, excl_start, excl_end
                )
                if matches:
                    all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
                    is_excluded = True
                    break

    # Calculate numerators
    opioid_codes = _get_all_opioid_codes()

    # Rate 1: >= 15 days in 30-day period (IPSD through 29 days after)
    r1_end = ipsd + timedelta(days=29)
    r1_days = _calculate_covered_days(bundle, opioid_codes, ipsd, r1_end)
    r1_num = r1_days >= 15

    # Rate 2: >= 31 days in 62-day period (IPSD through 61 days after)
    r2_end = ipsd + timedelta(days=61)
    r2_days = _calculate_covered_days(bundle, opioid_codes, ipsd, r2_end)
    r2_num = r2_days >= 31

    groups = [
        {
            "code": "COU-1",
            "display": ">=15 Days Covered",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r1_num,
        },
        {
            "code": "COU-2",
            "display": ">=31 Days Covered",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r2_num,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="COU",
        measure_name="Risk of Continued Opioid Use",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
