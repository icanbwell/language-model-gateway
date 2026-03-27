"""
HEDIS MY 2025 - Weight Assessment and Counseling for Nutrition and Physical
Activity for Children/Adolescents (WCC).

The percentage of members 3-17 years of age who had an outpatient visit with a
PCP or OB/GYN and who had evidence of the following during the measurement year:
  - BMI Percentile
  - Counseling for Nutrition
  - Counseling for Physical Activity

This is a multi-indicator measure with three numerator rates.
"""

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    ICD10CM,
)

VALUE_SETS = load_value_sets_from_csv("WCC")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible population: members 3-17 as of Dec 31 of the measurement year
    with an outpatient visit (Outpatient Value Set) during the measurement year.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 3 or age > 17:
        return False, evaluated

    outpatient_codes = all_codes(VALUE_SETS, "Outpatient")
    outpatient_visits = find_encounters_with_codes(
        bundle, outpatient_codes, my_start, my_end
    )
    if not outpatient_visits:
        return False, evaluated

    for enc, _ in outpatient_visits:
        evaluated.append(f"Encounter/{enc.get('id')}")

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions:
    - Pregnancy diagnosis during the measurement year (exclude lab claims).
    - Hospice services during the measurement year.
    - Death during the measurement year.
    """
    evaluated: list[str] = []

    # Pregnancy exclusion
    my_start, my_end = measurement_year_dates(measurement_year)
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy")
    if pregnancy_codes:
        pregnancy_conditions = find_conditions_with_codes(
            bundle, pregnancy_codes, my_start, my_end
        )
        if pregnancy_conditions:
            for cond, _ in pregnancy_conditions:
                evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    # Common exclusions (hospice, death) - no frailty for pediatric measure
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerators (three indicators)
# ---------------------------------------------------------------------------


def _check_bmi_percentile(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """BMI percentile documented during the measurement year."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    bmi_codes = all_codes(VALUE_SETS, "BMI Percentile")
    if bmi_codes:
        # Check observations
        obs_hits = find_observations_with_codes(bundle, bmi_codes, my_start, my_end)
        if obs_hits:
            for obs, _ in obs_hits:
                evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

        # Check conditions (ICD-10 BMI percentile codes)
        cond_hits = find_conditions_with_codes(bundle, bmi_codes, my_start, my_end)
        if cond_hits:
            for cond, _ in cond_hits:
                evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

        # Check encounters/procedures with BMI percentile codes
        enc_hits = find_encounters_with_codes(bundle, bmi_codes, my_start, my_end)
        if enc_hits:
            for enc, _ in enc_hits:
                evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

        proc_hits = find_procedures_with_codes(bundle, bmi_codes, my_start, my_end)
        if proc_hits:
            for proc, _ in proc_hits:
                evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    return False, evaluated


def _check_nutrition_counseling(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Counseling for nutrition during the measurement year:
    - Nutrition Counseling Value Set, OR
    - ICD-10-CM code Z71.3
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    nutrition_codes = all_codes(VALUE_SETS, "Nutrition Counseling")
    if nutrition_codes:
        for proc, _ in find_procedures_with_codes(
            bundle, nutrition_codes, my_start, my_end
        ):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

        for enc, _ in find_encounters_with_codes(
            bundle, nutrition_codes, my_start, my_end
        ):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

        for obs, _ in find_observations_with_codes(
            bundle, nutrition_codes, my_start, my_end
        ):
            evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

    # Also check ICD-10-CM Z71.3
    z713_codes = {ICD10CM: {"Z71.3"}}
    for cond, _ in find_conditions_with_codes(bundle, z713_codes, my_start, my_end):
        evaluated.append(f"Condition/{cond.get('id')}")
        return True, evaluated

    for enc, _ in find_encounters_with_codes(bundle, z713_codes, my_start, my_end):
        evaluated.append(f"Encounter/{enc.get('id')}")
        return True, evaluated

    return False, evaluated


def _check_physical_activity_counseling(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Counseling for physical activity during the measurement year:
    - Physical Activity Counseling Value Set, OR
    - Encounter for Physical Activity Counseling Value Set
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    for vs_name in (
        "Physical Activity Counseling",
        "Encounter for Physical Activity Counseling",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue

        for proc, _ in find_procedures_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

        for enc, _ in find_encounters_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

        for obs, _ in find_observations_with_codes(bundle, vs_codes, my_start, my_end):
            evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_wcc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate the WCC measure for an individual patient.

    Returns a FHIR MeasureReport with three rate groups:
    BMI Percentile, Counseling for Nutrition, Counseling for Physical Activity.
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        groups = [
            {
                "code": "WCC-BMI",
                "display": "BMI Percentile",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
            {
                "code": "WCC-Nutrition",
                "display": "Counseling for Nutrition",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
            {
                "code": "WCC-PhysicalActivity",
                "display": "Counseling for Physical Activity",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
        ]
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="WCC",
            measure_name="Weight Assessment and Counseling for Nutrition and Physical Activity for Children/Adolescents",
            measurement_year=measurement_year,
            groups=groups,
            evaluated_resources=all_evaluated,
        )

    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(exclusion_refs)

    bmi_met, bmi_refs = _check_bmi_percentile(bundle, measurement_year)
    all_evaluated.extend(bmi_refs)

    nutrition_met, nutrition_refs = _check_nutrition_counseling(
        bundle, measurement_year
    )
    all_evaluated.extend(nutrition_refs)

    activity_met, activity_refs = _check_physical_activity_counseling(
        bundle, measurement_year
    )
    all_evaluated.extend(activity_refs)

    groups = [
        {
            "code": "WCC-BMI",
            "display": "BMI Percentile",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": bmi_met,
        },
        {
            "code": "WCC-Nutrition",
            "display": "Counseling for Nutrition",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": nutrition_met,
        },
        {
            "code": "WCC-PhysicalActivity",
            "display": "Counseling for Physical Activity",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": activity_met,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="WCC",
        measure_name="Weight Assessment and Counseling for Nutrition and Physical Activity for Children/Adolescents",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
