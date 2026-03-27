"""
HEDIS MY 2025 - Well-Child Visits in the First 30 Months of Life (W30).

Two rates are reported:
  Rate 1: Children who turned 15 months old during the measurement year -
          six or more well-child visits on different dates of service on or
          before the 15-month birthday.
  Rate 2: Children who turned 30 months old during the measurement year -
          two or more well-child visits on different dates of service between
          the child's 15-month birthday plus 1 day and the 30-month birthday.

Telehealth visits are excluded from the numerator (MY 2025 change).
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("W30")


def _is_telehealth_encounter(encounter: dict) -> bool:
    """Check if an encounter is a telehealth visit that should be excluded."""
    telehealth_pos_codes = all_codes(VALUE_SETS, "Telehealth POS")
    online_codes = all_codes(VALUE_SETS, "Online Assessments")
    telephone_codes = all_codes(VALUE_SETS, "Telephone Visits")

    for code_set in (telehealth_pos_codes, online_codes, telephone_codes):
        if code_set and resource_has_any_code(encounter, code_set):
            return True
        if code_set:
            for t in encounter.get("type", []):
                if codeable_concept_has_any_code(t, code_set):
                    return True
    return False


def _is_lab_claim(encounter: dict) -> bool:
    """Check if the encounter is a laboratory claim (POS code 81)."""
    for t in encounter.get("type", []):
        for coding in t.get("coding", []):
            if coding.get("code") == "81":
                return True
    return False


def _count_well_child_visits(
    bundle: dict,
    start: date,
    end: date,
) -> tuple[int, list[str]]:
    """Count well-child visits on distinct dates within a period.

    Uses Well Care Visit and Encounter for Well Care value sets.
    Excludes telehealth and lab claims.
    """
    well_care_codes = all_codes(VALUE_SETS, "Well Care Visit")
    encounter_well_care_codes = all_codes(VALUE_SETS, "Encounter for Well Care")

    visit_dates: set[date] = set()
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, start, end):
            continue
        if _is_telehealth_encounter(enc):
            continue

        matched = False
        if well_care_codes and resource_has_any_code(enc, well_care_codes):
            matched = True
        if not matched and well_care_codes:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, well_care_codes):
                    matched = True
                    break

        if not matched and encounter_well_care_codes:
            if _is_lab_claim(enc):
                continue
            if resource_has_any_code(enc, encounter_well_care_codes):
                matched = True
            if not matched:
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, encounter_well_care_codes):
                        matched = True
                        break

        if matched and enc_date not in visit_dates:
            visit_dates.add(enc_date)
            evaluated.append(f"Encounter/{enc.get('id')}")

    return len(visit_dates), evaluated


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Determine if patient is in the eligible population for either rate.

    Rate 1: children who turn 15 months during MY (born ~Oct prior year - Sep MY-1)
    Rate 2: children who turn 30 months during MY (born ~Jul MY-3 - Jun MY-2)
    """
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    my_start, my_end = measurement_year_dates(measurement_year)

    # 15-month birthday = 1st birthday + 90 days
    birthday_15m = date(
        birth_date.year + 1, birth_date.month, birth_date.day
    ) + timedelta(days=90)

    # 30-month birthday = 2nd birthday + 180 days
    birthday_30m = date(
        birth_date.year + 2, birth_date.month, birth_date.day
    ) + timedelta(days=180)

    rate1_eligible = my_start <= birthday_15m <= my_end
    rate2_eligible = my_start <= birthday_30m <= my_end

    if rate1_eligible or rate2_eligible:
        return True, []
    return False, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice and death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Not used directly; see calculate_w30_measure for multi-rate logic."""
    return False, []


def calculate_w30_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the W30 measure with two rates."""
    birth_date = get_patient_birth_date(bundle)
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    if not birth_date:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="W30",
            measure_name="Well-Child Visits in the First 30 Months of Life",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "W30-Rate1",
                    "display": "Well-Child Visits in the First 15 Months",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "W30-Rate2",
                    "display": "Well-Child Visits for Age 15 Months-30 Months",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    my_start, my_end = measurement_year_dates(measurement_year)

    # Calculate key dates
    birthday_15m = date(
        birth_date.year + 1, birth_date.month, birth_date.day
    ) + timedelta(days=90)
    birthday_30m = date(
        birth_date.year + 2, birth_date.month, birth_date.day
    ) + timedelta(days=180)

    rate1_eligible = my_start <= birthday_15m <= my_end
    rate2_eligible = my_start <= birthday_30m <= my_end

    # Check exclusions
    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    # Rate 1: 6+ visits on or before 15-month birthday
    rate1_numerator = False
    if rate1_eligible and not is_excluded:
        count, refs = _count_well_child_visits(bundle, birth_date, birthday_15m)
        all_evaluated.extend(refs)
        rate1_numerator = count >= 6

    # Rate 2: 2+ visits between 15-month birthday + 1 day and 30-month birthday
    rate2_numerator = False
    if rate2_eligible and not is_excluded:
        period_start = birthday_15m + timedelta(days=1)
        count, refs = _count_well_child_visits(bundle, period_start, birthday_30m)
        all_evaluated.extend(refs)
        rate2_numerator = count >= 2

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="W30",
        measure_name="Well-Child Visits in the First 30 Months of Life",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "W30-Rate1",
                "display": "Well-Child Visits in the First 15 Months",
                "initial_population": rate1_eligible,
                "denominator_exclusion": is_excluded if rate1_eligible else False,
                "numerator": rate1_numerator,
            },
            {
                "code": "W30-Rate2",
                "display": "Well-Child Visits for Age 15 Months-30 Months",
                "initial_population": rate2_eligible,
                "denominator_exclusion": is_excluded if rate2_eligible else False,
                "numerator": rate2_numerator,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
