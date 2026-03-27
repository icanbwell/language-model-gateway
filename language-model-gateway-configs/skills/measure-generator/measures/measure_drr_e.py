"""
HEDIS MY 2025 - Depression Remission or Response for Adolescents and Adults (DRR-E).

The percentage of members 12 years of age and older with a diagnosis of depression
and an elevated PHQ-9 score, who had evidence of response or remission within
120-240 days (4-8 months) of the elevated score.

Rate 1 - Follow-Up PHQ-9: follow-up PHQ-9 score within 120-240 days of IESD.
Rate 2 - Depression Remission: most recent PHQ-9 < 5 during follow-up period.
Rate 3 - Depression Response: most recent PHQ-9 decreased >= 50% from IESD score.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_observation_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("DRR-E")

# PHQ-9 LOINC codes
PHQ9_LOINC = "44261-6"
PHQ9M_LOINC = "89204-2"


def _get_phq9_loincs(age: int) -> set[str]:
    """Return valid PHQ-9 LOINC codes based on age."""
    loincs = {PHQ9_LOINC}
    if age <= 17:
        loincs.add(PHQ9M_LOINC)
    return loincs


def _find_phq9_observations(
    bundle: dict, start: date, end: date, valid_loincs: set[str]
) -> list[tuple[dict, date, float]]:
    """Find PHQ-9 observations with scores in the date range."""
    results = []
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, start, end):
            continue
        for coding in obs.get("code", {}).get("coding", []):
            if coding.get("system") == LOINC and coding.get("code") in valid_loincs:
                score = obs.get("valueQuantity", {}).get("value")
                if score is None:
                    score = obs.get("valueInteger")
                if score is not None:
                    results.append((obs, obs_date, float(score)))
                    break
    return results


def _find_iesd(
    bundle: dict, intake_start: date, intake_end: date, age: int
) -> tuple[date | None, float | None, list[str]]:
    """
    Find the Index Episode Start Date (IESD): the earliest date during the
    intake period when a member has a PHQ-9 total score >9 documented within
    a 31-day period around an interactive outpatient encounter with a diagnosis
    of major depression or dysthymia.
    """
    evaluated: list[str] = []
    valid_loincs = _get_phq9_loincs(age)

    enc_codes = all_codes(VALUE_SETS, "Interactive Outpatient Encounter")
    dep_codes = all_codes(VALUE_SETS, "Major Depression or Dysthymia")
    if not enc_codes or not dep_codes:
        return None, None, evaluated

    # Find qualifying encounters
    qualifying_encounters = find_encounters_with_codes(
        bundle, enc_codes, intake_start, intake_end
    )

    # Filter encounters with depression diagnosis
    dep_encounters: list[tuple[dict, date]] = []
    for enc, enc_date in qualifying_encounters:
        has_dep = False
        for reason in enc.get("reasonCode", []):
            if codeable_concept_has_any_code(reason, dep_codes):
                has_dep = True
                break
        if not has_dep:
            for cond in get_resources_by_type(bundle, "Condition"):
                if resource_has_any_code(cond, dep_codes):
                    has_dep = True
                    break
        if has_dep:
            dep_encounters.append((enc, enc_date))

    if not dep_encounters:
        return None, None, evaluated

    # Find PHQ-9 scores during intake period
    phq9_obs = _find_phq9_observations(bundle, intake_start, intake_end, valid_loincs)

    # Match PHQ-9 scores > 9 within 31-day window of encounter
    candidates: list[tuple[date, float, str, str]] = []
    for obs, obs_date, score in phq9_obs:
        if score <= 9:
            continue
        for enc, enc_date in dep_encounters:
            window_start = enc_date - timedelta(days=15)
            window_end = enc_date + timedelta(days=15)
            if is_date_in_range(obs_date, window_start, window_end):
                candidates.append(
                    (
                        obs_date,
                        score,
                        f"Observation/{obs.get('id')}",
                        f"Encounter/{enc.get('id')}",
                    )
                )

    if not candidates:
        return None, None, evaluated

    # Take the earliest
    candidates.sort(key=lambda x: x[0])
    iesd_date, iesd_score, obs_ref, enc_ref = candidates[0]
    evaluated.extend([obs_ref, enc_ref])
    return iesd_date, iesd_score, evaluated


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Initial population: members 12+ as of start of intake period with
    depression encounter and elevated PHQ-9 score (IESD).

    Intake period: May 1 of prior year through April 30 of measurement year.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    intake_start = date(measurement_year - 1, 5, 1)
    age = calculate_age(birth_date, intake_start)
    if age < 12:
        return False, evaluated

    intake_end = date(measurement_year, 4, 30)
    iesd_date, iesd_score, refs = _find_iesd(bundle, intake_start, intake_end, age)
    evaluated.extend(refs)

    if iesd_date is None:
        return False, evaluated

    return True, evaluated


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


def _check_followup_remission_response(
    bundle: dict, measurement_year: int
) -> tuple[bool, bool, bool, list[str]]:
    """
    Check all three numerators:
    1. Follow-up PHQ-9 score in 120-240 day window
    2. Remission: most recent PHQ-9 < 5
    3. Response: most recent PHQ-9 decreased >= 50%

    Returns (has_followup, has_remission, has_response, evaluated).
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, False, False, evaluated

    intake_start = date(measurement_year - 1, 5, 1)
    intake_end = date(measurement_year, 4, 30)
    age = calculate_age(birth_date, intake_start)
    valid_loincs = _get_phq9_loincs(age)

    iesd_date, iesd_score, iesd_refs = _find_iesd(bundle, intake_start, intake_end, age)
    evaluated.extend(iesd_refs)

    if iesd_date is None or iesd_score is None:
        return False, False, False, evaluated

    # Follow-up period: 120-240 days after IESD
    followup_start = iesd_date + timedelta(days=120)
    followup_end = iesd_date + timedelta(days=240)

    followup_obs = _find_phq9_observations(
        bundle, followup_start, followup_end, valid_loincs
    )

    if not followup_obs:
        return False, False, False, evaluated

    # Has follow-up PHQ-9
    has_followup = True
    for obs, _, _ in followup_obs:
        evaluated.append(f"Observation/{obs.get('id')}")

    # Most recent PHQ-9 in follow-up period
    followup_obs.sort(key=lambda x: x[1], reverse=True)
    _, _, most_recent_score = followup_obs[0]

    # Remission: PHQ-9 < 5
    has_remission = most_recent_score < 5

    # Response: PHQ-9 decreased >= 50% from IESD score
    has_response = most_recent_score <= (iesd_score * 0.5)

    return has_followup, has_remission, has_response, evaluated


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_drr_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate DRR-E measure for a patient bundle.

    Returns a FHIR MeasureReport with three rate groups:
    1. Follow-Up PHQ-9
    2. Depression Remission
    3. Depression Response
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    has_followup = False
    has_remission = False
    has_response = False
    if is_eligible and not is_excluded:
        has_followup, has_remission, has_response, num_refs = (
            _check_followup_remission_response(bundle, measurement_year)
        )
        all_evaluated.extend(num_refs)

    groups = [
        {
            "code": "followup",
            "display": "Follow-Up PHQ-9",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": has_followup,
        },
        {
            "code": "remission",
            "display": "Depression Remission",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": has_remission,
        },
        {
            "code": "response",
            "display": "Depression Response",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": has_response,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="DRR-E",
        measure_name="Depression Remission or Response for Adolescents and Adults",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
