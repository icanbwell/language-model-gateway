"""
HEDIS MY 2025 - Emergency Department Utilization (EDU).

For members 18 years of age and older, the risk-adjusted ratio of
observed-to-expected emergency department (ED) visits during the
measurement year.

This is a member-based, risk-adjusted utilization measure (rate per 1000).
For individual patient calculation, we report the observed count of
qualifying ED visits as the numerator.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_class,
    build_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("EDU")


def _is_ed_visit(encounter: dict) -> bool:
    """Check if an encounter is an ED visit.

    An ED visit is identified by:
    - ED Value Set, OR
    - ED Procedure Code Value Set with POS code 23
    """
    ed_codes = all_codes(VALUE_SETS, "ED")
    ed_proc_codes = all_codes(VALUE_SETS, "ED Procedure Code")

    if ed_codes and (
        resource_has_any_code(encounter, ed_codes)
        or any(
            codeable_concept_has_any_code(t, ed_codes)
            for t in encounter.get("type", [])
        )
    ):
        return True

    if ed_proc_codes and (
        resource_has_any_code(encounter, ed_proc_codes)
        or any(
            codeable_concept_has_any_code(t, ed_proc_codes)
            for t in encounter.get("type", [])
        )
    ):
        # Must also have ED POS code 23
        enc_class = get_encounter_class(encounter)
        if enc_class == "EMER":
            return True
        # Check for POS code 23 in encounter type or location
        for t in encounter.get("type", []):
            for coding in t.get("coding", []):
                if coding.get("code") == "23":
                    return True

    return False


def _results_in_inpatient_or_observation(encounter: dict, bundle: dict) -> bool:
    """Check if ED visit resulted in an inpatient or observation stay."""
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    observation_codes = all_codes(VALUE_SETS, "Observation Stay")
    enc_date = get_encounter_date(encounter)
    if not enc_date:
        return False

    for enc in get_resources_by_type(bundle, "Encounter"):
        if enc.get("id") == encounter.get("id"):
            continue
        for code_set in (inpatient_codes, observation_codes):
            if not code_set:
                continue
            if resource_has_any_code(enc, code_set) or any(
                codeable_concept_has_any_code(t, code_set) for t in enc.get("type", [])
            ):
                ip_date = get_encounter_date(enc)
                if ip_date and abs((ip_date - enc_date).days) <= 1:
                    return True
    return False


def _should_exclude_ed_visit(encounter: dict) -> bool:
    """Check if an ED visit should be excluded.

    Excludes: mental health/chemical dependency, psychiatry, ECT.
    """
    mental_codes = all_codes(VALUE_SETS, "Mental and Behavioral Disorders")
    psychiatry_codes = all_codes(VALUE_SETS, "Psychiatry")
    ect_codes = all_codes(VALUE_SETS, "Electroconvulsive Therapy")

    for code_set in (mental_codes, psychiatry_codes, ect_codes):
        if code_set and (
            resource_has_any_code(encounter, code_set)
            or any(
                codeable_concept_has_any_code(t, code_set)
                for t in encounter.get("type", [])
            )
        ):
            return True
    return False


def _count_ed_visits(bundle: dict, measurement_year: int) -> tuple[int, list[str]]:
    """Count qualifying ED visits during the measurement year.

    Multiple visits on the same date count as one visit.
    Excludes visits resulting in inpatient/observation stays.
    """
    my_start, my_end = measurement_year_dates(measurement_year)
    visited_dates: set[date] = set()
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        if not _is_ed_visit(enc):
            continue
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue
        if enc_date in visited_dates:
            continue
        if _results_in_inpatient_or_observation(enc, bundle):
            continue
        if _should_exclude_ed_visit(enc):
            continue

        visited_dates.add(enc_date)
        evaluated.append(f"Encounter/{enc.get('id')}")

    return len(visited_dates), evaluated


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient is 18+ as of Dec 31 of MY."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    if age >= 18:
        return True, []
    return False, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusion: hospice."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient had any qualifying ED visits.

    For individual reporting, numerator = True if count > 0.
    """
    count, evaluated = _count_ed_visits(bundle, measurement_year)
    return count > 0, evaluated


def calculate_edu_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the EDU measure.

    For individual patient, reports the observed ED visit count.
    """
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    if not is_eligible:
        return build_measure_report(
            patient_id=patient_id,
            measure_abbreviation="EDU",
            measure_name="Emergency Department Utilization",
            measurement_year=measurement_year,
            initial_population=False,
            denominator_exclusion=False,
            numerator=False,
            evaluated_resources=all_evaluated,
        )

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    visit_count, num_refs = _count_ed_visits(bundle, measurement_year)
    all_evaluated.extend(num_refs)

    report = build_measure_report(
        patient_id=patient_id,
        measure_abbreviation="EDU",
        measure_name="Emergency Department Utilization",
        measurement_year=measurement_year,
        initial_population=True,
        denominator_exclusion=is_excluded,
        numerator=visit_count > 0,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )

    # Add observed count as extension for utilization reporting
    report["extension"] = [
        {
            "url": "http://ncqa.org/fhir/StructureDefinition/observed-event-count",
            "valueInteger": visit_count,
        }
    ]

    return report
