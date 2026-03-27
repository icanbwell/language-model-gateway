"""
HEDIS MY 2025 - Utilization of the PHQ-9 to Monitor Depression Symptoms
for Adolescents and Adults (DMS-E).

The percentage of members 12 years of age and older with a diagnosis of major
depression or dysthymia, who had an outpatient encounter with a PHQ-9 score
present in their record in the same assessment period as the encounter.

Three assessment periods:
  Period 1: January 1 - April 30
  Period 2: May 1 - August 31
  Period 3: September 1 - December 31
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_observation_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("DMS-E")

# PHQ-9 LOINC codes
PHQ9_LOINC = "44261-6"  # PHQ-9 for all members 12+
PHQ9M_LOINC = "89204-2"  # PHQ-9M for adolescents 12-17


def _assessment_periods(measurement_year: int) -> list[tuple[date, date]]:
    """Return the three assessment period date ranges."""
    return [
        (date(measurement_year, 1, 1), date(measurement_year, 4, 30)),
        (date(measurement_year, 5, 1), date(measurement_year, 8, 31)),
        (date(measurement_year, 9, 1), date(measurement_year, 12, 31)),
    ]


def _has_interactive_encounter_with_depression(
    bundle: dict, period_start: date, period_end: date
) -> tuple[bool, list[str]]:
    """
    Check for an interactive outpatient encounter with a diagnosis of major
    depression or dysthymia during the given period.
    """
    evaluated: list[str] = []
    enc_codes = all_codes(VALUE_SETS, "Interactive Outpatient Encounter")
    dep_codes = all_codes(VALUE_SETS, "Major Depression or Dysthymia")
    if not enc_codes or not dep_codes:
        return False, evaluated

    encounters = find_encounters_with_codes(bundle, enc_codes, period_start, period_end)
    for enc, enc_date in encounters:
        # Check encounter reason codes for depression diagnosis
        for reason in enc.get("reasonCode", []):
            if codeable_concept_has_any_code(reason, dep_codes):
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated

        # Check conditions linked to this encounter or active during period
        for cond in get_resources_by_type(bundle, "Condition"):
            if resource_has_any_code(cond, dep_codes):
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated

    return False, evaluated


def _has_phq9_score(
    bundle: dict, period_start: date, period_end: date, age: int
) -> tuple[bool, list[str]]:
    """Check for a PHQ-9 score in the member's record during the assessment period."""
    evaluated: list[str] = []
    valid_loincs = {PHQ9_LOINC}
    if age <= 17:
        valid_loincs.add(PHQ9M_LOINC)

    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, period_start, period_end):
            continue
        for coding in obs.get("code", {}).get("coding", []):
            if coding.get("system") == LOINC and coding.get("code") in valid_loincs:
                score = obs.get("valueQuantity", {}).get("value")
                if score is None:
                    score = obs.get("valueInteger")
                if score is not None:
                    evaluated.append(f"Observation/{obs.get('id')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Initial population: members 12 years and older at the start of the
    measurement period with at least one interactive outpatient encounter
    with a diagnosis of major depression or dysthymia in any assessment period.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 12:
        return False, evaluated

    # Check if there is at least one qualifying encounter in any period
    for period_start, period_end in _assessment_periods(measurement_year):
        has_enc, refs = _has_interactive_encounter_with_depression(
            bundle, period_start, period_end
        )
        if has_enc:
            evaluated.extend(refs)
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Exclusions:
    - Bipolar disorder any time through end of measurement period.
    - Personality disorder any time through end of measurement period.
    - Psychotic disorder any time through end of measurement period.
    - Pervasive developmental disorder any time through end of measurement period.
    - Hospice during measurement period.
    - Death during measurement period.
    """
    evaluated: list[str] = []

    exclusion_vs_names = [
        "Bipolar Disorder",
        "Other Bipolar Disorder",
        "Personality Disorder",
        "Psychotic Disorders",
        "Pervasive Developmental Disorder",
    ]

    for vs_name in exclusion_vs_names:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        conditions = find_conditions_with_codes(bundle, vs_codes, None, None)
        for cond, _ in conditions:
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    # Hospice and death
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
    """
    Numerator: PHQ-9 score present during each assessment period where the
    member has a qualifying encounter. This is checked per-period.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)

    # Check any period
    for period_start, period_end in _assessment_periods(measurement_year):
        has_enc, _ = _has_interactive_encounter_with_depression(
            bundle, period_start, period_end
        )
        if has_enc:
            has_score, refs = _has_phq9_score(bundle, period_start, period_end, age)
            if has_score:
                evaluated.extend(refs)
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_dms_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate DMS-E measure for a patient bundle.

    Returns a FHIR MeasureReport with three rate groups (one per assessment period).
    """
    all_evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    age = 0
    if birth_date:
        my_start, _ = measurement_year_dates(measurement_year)
        age = calculate_age(birth_date, my_start)

    # Check exclusions once (same for all periods)
    is_excluded = False
    exclusion_refs: list[str] = []

    groups: list[dict] = []
    period_labels = ["Period 1 (Jan-Apr)", "Period 2 (May-Aug)", "Period 3 (Sep-Dec)"]
    periods = _assessment_periods(measurement_year)

    for i, (period_start, period_end) in enumerate(periods):
        has_enc, enc_refs = _has_interactive_encounter_with_depression(
            bundle, period_start, period_end
        )
        all_evaluated.extend(enc_refs)

        if has_enc and not is_excluded:
            # Check exclusions only once
            if not exclusion_refs:
                is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
                all_evaluated.extend(exclusion_refs)

        has_score = False
        if has_enc and not is_excluded and birth_date:
            has_score, score_refs = _has_phq9_score(
                bundle, period_start, period_end, age
            )
            all_evaluated.extend(score_refs)

        groups.append(
            {
                "code": f"phq9-period-{i + 1}",
                "display": f"PHQ-9 Utilization {period_labels[i]}",
                "initial_population": has_enc,
                "denominator_exclusion": is_excluded,
                "numerator": has_score,
            }
        )

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="DMS-E",
        measure_name="Utilization of the PHQ-9 to Monitor Depression Symptoms for Adolescents and Adults",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
