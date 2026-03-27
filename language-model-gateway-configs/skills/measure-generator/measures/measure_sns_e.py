"""
HEDIS MY 2025 - Social Need Screening and Intervention (SNS-E).

The percentage of members who were screened, using prespecified instruments, at
least once during the measurement period for unmet food, housing and
transportation needs, and received a corresponding intervention if they screened
positive.

Rate 1 - Food Screening
Rate 2 - Food Intervention (within 30 days of positive screen)
Rate 3 - Housing Screening
Rate 4 - Housing Intervention (within 30 days of positive screen)
Rate 5 - Transportation Screening
Rate 6 - Transportation Intervention (within 30 days of positive screen)
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient,
    get_patient_id,
    get_resources_by_type,
    is_date_in_range,
    measurement_year_dates,
    get_observation_date,
    find_encounters_with_codes,
    find_procedures_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("SNS-E")

# ---------------------------------------------------------------------------
# Screening instruments by domain (LOINC codes and positive finding codes)
# ---------------------------------------------------------------------------

# Food insecurity screening LOINC codes
FOOD_SCREENING_LOINCS = {
    "88122-7",
    "88123-5",
    "95251-5",
    "88124-3",
    "93031-3",
    "95400-8",
    "95399-2",
    "95264-8",
    "96434-6",
    "93668-2",
}

# Food insecurity positive finding LOINC answer codes
FOOD_POSITIVE_LOINCS = {
    "LA28397-0",
    "LA6729-3",
    "LA33-6",
    "LA19952-3",
    "LA30125-1",
    "LA30985-8",
    "LA30986-6",
    "LA32-8",
}

# Housing screening LOINC codes
HOUSING_SCREENING_LOINCS = {
    "71802-3",
    "99550-6",
    "98976-4",
    "98977-2",
    "98978-0",
    "93033-9",
    "96441-1",
    "93669-0",
    "96778-6",
    "99134-9",
    "99135-6",
}

# Housing positive finding LOINC answer codes
HOUSING_POSITIVE_LOINCS = {
    "LA31994-9",
    "LA31995-6",
    "LA33-6",
    "LA30190-5",
    "LA31996-4",
    "LA28580-1",
    "LA31997-2",
    "LA31998-0",
    "LA31999-8",
    "LA32000-4",
    "LA32001-2",
    "LA32691-0",
    "LA32693-6",
    "LA32694-4",
    "LA32695-1",
    "LA32696-9",
}

# Transportation screening LOINC codes
TRANSPORT_SCREENING_LOINCS = {
    "93030-5",
    "99594-4",
    "89569-8",
    "99553-0",
    "101351-5",
    "92358-1",
    "93671-6",
}

# Transportation positive finding LOINC answer codes
TRANSPORT_POSITIVE_LOINCS = {
    "LA33-6",
    "LA33093-8",
    "LA30134-3",
    "LA30133-5",
    "LA29232-8",
    "LA29233-6",
    "LA29234-4",
    "LA30024-6",
    "LA30026-1",
    "LA30027-9",
}


def _find_screenings(
    bundle: dict, screening_loincs: set[str], start: date, end: date
) -> list[tuple[dict, date]]:
    """Find screening observations for a social need domain."""
    results = []
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, start, end):
            continue
        for coding in obs.get("code", {}).get("coding", []):
            if coding.get("system") == LOINC and coding.get("code") in screening_loincs:
                results.append((obs, obs_date))
                break
    return results


def _is_positive_finding(obs: dict, positive_answer_loincs: set[str]) -> bool:
    """Check if a screening observation has a positive finding."""
    # Check valueCodeableConcept for answer codes
    value_cc = obs.get("valueCodeableConcept", {})
    for coding in value_cc.get("coding", []):
        if coding.get("code") in positive_answer_loincs:
            return True

    # Check valueString
    value_str = obs.get("valueString", "")
    if value_str and value_str in positive_answer_loincs:
        return True

    # Check components
    for comp in obs.get("component", []):
        comp_value_cc = comp.get("valueCodeableConcept", {})
        for coding in comp_value_cc.get("coding", []):
            if coding.get("code") in positive_answer_loincs:
                return True

    # Check for numeric threshold (e.g., score >= 2 for some instruments)
    value = obs.get("valueQuantity", {}).get("value")
    if value is None:
        value = obs.get("valueInteger")
    if value is not None and float(value) >= 1:
        return True

    return False


def _find_first_positive_screen(
    bundle: dict,
    screening_loincs: set[str],
    positive_loincs: set[str],
    start: date,
    end: date,
) -> date | None:
    """Find the date of the first positive screen for a social need domain."""
    screenings = _find_screenings(bundle, screening_loincs, start, end)
    screenings.sort(key=lambda x: x[1])
    for obs, obs_date in screenings:
        if _is_positive_finding(obs, positive_loincs):
            return obs_date
    return None


def _has_intervention(
    bundle: dict,
    intervention_vs_names: list[str],
    start: date,
    end: date,
) -> tuple[bool, list[str]]:
    """Check for a corresponding intervention within the date range."""
    evaluated: list[str] = []
    for vs_name in intervention_vs_names:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        for proc, _ in find_procedures_with_codes(bundle, vs_codes, start, end):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated
        for enc, _ in find_encounters_with_codes(bundle, vs_codes, start, end):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated
    return False, evaluated


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Initial population: members of any age enrolled at start of measurement period."""
    evaluated: list[str] = []
    patient = get_patient(bundle)
    if not patient:
        return False, evaluated
    evaluated.append(f"Patient/{patient.get('id')}")
    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Exclusions:
    - Hospice during measurement period.
    - Death during measurement period.
    - Medicare members 66+ enrolled in I-SNP or with LTI flag
      (not available in standard FHIR bundles).
    """
    evaluated: list[str] = []

    from .hedis_common import check_hospice, check_death

    excluded, refs = check_hospice(bundle, VALUE_SETS, measurement_year)
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    excluded, refs = check_death(bundle, measurement_year)
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Not used directly; see calculate function for multi-rate logic."""
    return False, []


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_sns_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate SNS-E measure for a patient bundle.

    Returns a FHIR MeasureReport with six rate groups:
    1. Food Screening
    2. Food Intervention
    3. Housing Screening
    4. Housing Intervention
    5. Transportation Screening
    6. Transportation Intervention
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    my_start, _ = measurement_year_dates(measurement_year)
    screening_end = date(measurement_year, 12, 1)

    # --- Food ---
    food_screened = False
    food_positive = False
    food_intervention = False
    if is_eligible and not is_excluded:
        food_screenings = _find_screenings(
            bundle, FOOD_SCREENING_LOINCS, my_start, screening_end
        )
        if food_screenings:
            food_screened = True
            for obs, _ in food_screenings:
                all_evaluated.append(f"Observation/{obs.get('id')}")

            first_pos = _find_first_positive_screen(
                bundle,
                FOOD_SCREENING_LOINCS,
                FOOD_POSITIVE_LOINCS,
                my_start,
                screening_end,
            )
            if first_pos:
                food_positive = True
                intervention_end = first_pos + timedelta(days=30)
                food_intervention, int_refs = _has_intervention(
                    bundle,
                    ["Food Insecurity Procedures"],
                    first_pos,
                    intervention_end,
                )
                all_evaluated.extend(int_refs)

    # --- Housing ---
    housing_screened = False
    housing_positive = False
    housing_intervention = False
    if is_eligible and not is_excluded:
        housing_screenings = _find_screenings(
            bundle, HOUSING_SCREENING_LOINCS, my_start, screening_end
        )
        if housing_screenings:
            housing_screened = True
            for obs, _ in housing_screenings:
                all_evaluated.append(f"Observation/{obs.get('id')}")

            first_pos = _find_first_positive_screen(
                bundle,
                HOUSING_SCREENING_LOINCS,
                HOUSING_POSITIVE_LOINCS,
                my_start,
                screening_end,
            )
            if first_pos:
                housing_positive = True
                intervention_end = first_pos + timedelta(days=30)
                housing_intervention, int_refs = _has_intervention(
                    bundle,
                    [
                        "Housing Instability Procedures",
                        "Homelessness Procedures",
                        "Inadequate Housing Procedures",
                    ],
                    first_pos,
                    intervention_end,
                )
                all_evaluated.extend(int_refs)

    # --- Transportation ---
    transport_screened = False
    transport_positive = False
    transport_intervention = False
    if is_eligible and not is_excluded:
        transport_screenings = _find_screenings(
            bundle, TRANSPORT_SCREENING_LOINCS, my_start, screening_end
        )
        if transport_screenings:
            transport_screened = True
            for obs, _ in transport_screenings:
                all_evaluated.append(f"Observation/{obs.get('id')}")

            first_pos = _find_first_positive_screen(
                bundle,
                TRANSPORT_SCREENING_LOINCS,
                TRANSPORT_POSITIVE_LOINCS,
                my_start,
                screening_end,
            )
            if first_pos:
                transport_positive = True
                intervention_end = first_pos + timedelta(days=30)
                transport_intervention, int_refs = _has_intervention(
                    bundle,
                    ["Transportation Insecurity Procedures"],
                    first_pos,
                    intervention_end,
                )
                all_evaluated.extend(int_refs)

    groups = [
        {
            "code": "food-screening",
            "display": "Food Screening",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": food_screened,
        },
        {
            "code": "food-intervention",
            "display": "Food Intervention",
            "initial_population": is_eligible and food_screened and food_positive,
            "denominator_exclusion": is_excluded,
            "numerator": food_intervention,
        },
        {
            "code": "housing-screening",
            "display": "Housing Screening",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": housing_screened,
        },
        {
            "code": "housing-intervention",
            "display": "Housing Intervention",
            "initial_population": is_eligible and housing_screened and housing_positive,
            "denominator_exclusion": is_excluded,
            "numerator": housing_intervention,
        },
        {
            "code": "transportation-screening",
            "display": "Transportation Screening",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": transport_screened,
        },
        {
            "code": "transportation-intervention",
            "display": "Transportation Intervention",
            "initial_population": is_eligible
            and transport_screened
            and transport_positive,
            "denominator_exclusion": is_excluded,
            "numerator": transport_intervention,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="SNS-E",
        measure_name="Social Need Screening and Intervention",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
