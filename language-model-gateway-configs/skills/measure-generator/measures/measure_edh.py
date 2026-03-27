"""
HEDIS MY 2025 - Emergency Department Visits for Hypoglycemia in Older
Adults With Diabetes (EDH).

For members 67 years of age and older with diabetes (types 1 and 2), the
risk-adjusted ratio of observed to expected (O/E) ED visits for
hypoglycemia during the measurement year.

Two rates are reported:
  Rate 1: All members 67+ with diabetes.
  Rate 2: Members 67+ with diabetes receiving insulin (at least one
          dispensing in each of three 6-month treatment periods).

For individual patient calculation, we report the observed ED visit count
for hypoglycemia.
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
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("EDH")


def _has_diabetes_by_claims(bundle: dict, measurement_year: int) -> bool:
    """Check for 2+ diabetes diagnoses on different dates in MY or prior year."""
    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")
    if not diabetes_codes:
        return False

    py_start = date(measurement_year - 1, 1, 1)
    my_end = date(measurement_year, 12, 31)

    diab_dates: set[date] = set()
    conditions = find_conditions_with_codes(bundle, diabetes_codes, py_start, my_end)
    for _, onset in conditions:
        if onset:
            diab_dates.add(onset)

    encounters = find_encounters_with_codes(bundle, diabetes_codes, py_start, my_end)
    for _, enc_date in encounters:
        if enc_date:
            diab_dates.add(enc_date)

    return len(diab_dates) >= 2


def _has_diabetes_by_pharmacy(bundle: dict, measurement_year: int) -> bool:
    """Check for diabetes medication + at least one diabetes diagnosis."""
    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")
    if not diabetes_codes:
        return False

    py_start = date(measurement_year - 1, 1, 1)
    my_end = date(measurement_year, 12, 31)

    # Check for at least one diabetes diagnosis
    has_dx = (
        len(find_conditions_with_codes(bundle, diabetes_codes, py_start, my_end)) > 0
        or len(find_encounters_with_codes(bundle, diabetes_codes, py_start, my_end)) > 0
    )
    if not has_dx:
        return False

    # Check for diabetes medication dispensing
    # Look for any medication related to diabetes in the value sets
    for vs_name in VALUE_SETS:
        if "medication" in vs_name.lower() or "insulin" in vs_name.lower():
            med_codes = all_codes(VALUE_SETS, vs_name)
            if med_codes:
                meds = find_medications_with_codes(bundle, med_codes, py_start, my_end)
                if meds:
                    return True

    return False


def _has_insulin_in_all_treatment_periods(bundle: dict, measurement_year: int) -> bool:
    """Check if member received insulin in each of three 6-month periods.

    Treatment period 1: July 1 - Dec 31 of prior year
    Treatment period 2: Jan 1 - June 30 of MY
    Treatment period 3: July 1 - Dec 31 of MY
    """
    # Collect insulin medication codes
    insulin_codes: dict[str, set[str]] = {}
    for vs_name in VALUE_SETS:
        if "insulin" in vs_name.lower() and "basal" not in vs_name.lower():
            for sys, codes in VALUE_SETS[vs_name].items():
                insulin_codes.setdefault(sys, set()).update(codes)

    if not insulin_codes:
        return False

    periods = [
        (date(measurement_year - 1, 7, 1), date(measurement_year - 1, 12, 31)),
        (date(measurement_year, 1, 1), date(measurement_year, 6, 30)),
        (date(measurement_year, 7, 1), date(measurement_year, 12, 31)),
    ]

    for period_start, period_end in periods:
        meds = find_medications_with_codes(
            bundle, insulin_codes, period_start, period_end
        )
        if not meds:
            return False

    return True


def _count_ed_visits_for_hypoglycemia(
    bundle: dict, measurement_year: int
) -> tuple[int, list[str]]:
    """Count ED visits with a hypoglycemia diagnosis during MY.

    Multiple visits on the same date count as one. Max 5 visits.
    """
    my_start, my_end = measurement_year_dates(measurement_year)
    ed_codes = all_codes(VALUE_SETS, "ED")
    hypo_codes = all_codes(VALUE_SETS, "Hypoglycemia")

    if not ed_codes or not hypo_codes:
        return 0, []

    visited_dates: set[date] = set()
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue
        if enc_date in visited_dates:
            continue

        # Must be an ED visit
        is_ed = resource_has_any_code(enc, ed_codes) or any(
            codeable_concept_has_any_code(t, ed_codes) for t in enc.get("type", [])
        )
        if not is_ed:
            continue

        # Must have hypoglycemia diagnosis
        has_hypo = resource_has_any_code(enc, hypo_codes) or any(
            codeable_concept_has_any_code(t, hypo_codes) for t in enc.get("type", [])
        )
        if not has_hypo:
            # Check reasonCode
            for rc in enc.get("reasonCode", []):
                if codeable_concept_has_any_code(rc, hypo_codes):
                    has_hypo = True
                    break

        if has_hypo:
            visited_dates.add(enc_date)
            evaluated.append(f"Encounter/{enc.get('id')}")
            # Cap at 5 visits
            if len(visited_dates) >= 5:
                break

    return len(visited_dates), evaluated


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient is 67+ with diabetes."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 67:
        return False, []

    # Must have diabetes
    if _has_diabetes_by_claims(bundle, measurement_year):
        return True, []
    if _has_diabetes_by_pharmacy(bundle, measurement_year):
        return True, []

    return False, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusion: hospice."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient had any ED visits for hypoglycemia."""
    count, evaluated = _count_ed_visits_for_hypoglycemia(bundle, measurement_year)
    return count > 0, evaluated


def calculate_edh_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the EDH measure with Rate 1 (all diabetes) and Rate 2 (insulin)."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    visit_count = 0
    if is_eligible and not is_excluded:
        visit_count, num_refs = _count_ed_visits_for_hypoglycemia(
            bundle, measurement_year
        )
        all_evaluated.extend(num_refs)

    # Rate 2: subset receiving insulin in all treatment periods
    rate2_eligible = is_eligible and _has_insulin_in_all_treatment_periods(
        bundle, measurement_year
    )

    report = build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="EDH",
        measure_name="ED Visits for Hypoglycemia in Older Adults With Diabetes",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "EDH-Rate1",
                "display": "All Members With Diabetes",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": visit_count > 0,
            },
            {
                "code": "EDH-Rate2",
                "display": "Members Receiving Insulin",
                "initial_population": rate2_eligible,
                "denominator_exclusion": is_excluded if rate2_eligible else False,
                "numerator": visit_count > 0 if rate2_eligible else False,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )

    # Add observed count
    report["extension"] = [
        {
            "url": "http://ncqa.org/fhir/StructureDefinition/observed-event-count",
            "valueInteger": visit_count,
        }
    ]

    return report
