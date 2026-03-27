"""
HEDIS MY 2025 - Unhealthy Alcohol Use Screening and Follow-Up (ASF-E).

The percentage of members 18 years of age and older who were screened for unhealthy
alcohol use using a standardized instrument and, if screened positive, received
appropriate follow-up care.

Rate 1 - Unhealthy Alcohol Use Screening: screened using a standardized instrument.
Rate 2 - Follow-Up Care on Positive Screen: brief counseling or other follow-up
         care within 60 days of a positive screen.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient,
    get_patient_id,
    get_patient_birth_date,
    get_patient_gender,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    prior_year_dates,
    get_encounter_date,
    get_condition_onset,
    get_observation_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    ICD10CM,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("ASF-E")

# ---------------------------------------------------------------------------
# Alcohol screening instruments and thresholds
# ---------------------------------------------------------------------------

SCREENING_INSTRUMENTS: list[dict] = [
    {"loinc": "75624-7", "name": "AUDIT", "threshold": 8, "gender_specific": False},
    {
        "loinc": "75626-2",
        "name": "AUDIT-C",
        "threshold_male": 4,
        "threshold_female": 3,
        "gender_specific": True,
    },
    {
        "loinc": "88037-7",
        "name": "Single-question (men)",
        "threshold": 1,
        "gender_specific": False,
    },
    {
        "loinc": "75889-6",
        "name": "Single-question (women/65+)",
        "threshold": 1,
        "gender_specific": False,
    },
]

ALL_SCREENING_LOINCS = {i["loinc"] for i in SCREENING_INSTRUMENTS}


def _get_observation_loinc(obs: dict) -> str | None:
    """Extract alcohol screening LOINC code from an observation."""
    for coding in obs.get("code", {}).get("coding", []):
        if coding.get("system") == LOINC and coding.get("code") in ALL_SCREENING_LOINCS:
            return coding["code"]
    return None


def _get_observation_score(obs: dict) -> float | None:
    """Extract the numeric score from an observation."""
    vq = obs.get("valueQuantity", {})
    if vq and vq.get("value") is not None:
        return float(vq["value"])
    if obs.get("valueInteger") is not None:
        return float(obs["valueInteger"])
    if obs.get("valueString") is not None:
        try:
            return float(obs["valueString"])
        except (ValueError, TypeError):
            return None
    return None


def _is_positive_screen(loinc_code: str, score: float, gender: str | None) -> bool:
    """Determine if a screening score is positive."""
    for instr in SCREENING_INSTRUMENTS:
        if instr["loinc"] == loinc_code:
            if instr.get("gender_specific"):
                if gender == "male":
                    return score >= instr.get("threshold_male", 4)
                else:
                    return score >= instr.get("threshold_female", 3)
            return score >= instr["threshold"]
    return False


def _find_screening_observations(
    bundle: dict, start: date, end: date
) -> list[tuple[dict, date]]:
    """Find all alcohol screening observations in the date range."""
    results = []
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, start, end):
            continue
        loinc = _get_observation_loinc(obs)
        if loinc and _get_observation_score(obs) is not None:
            results.append((obs, obs_date))
    return results


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Initial population: members 18 years and older at start of measurement period."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 18:
        return False, evaluated

    patient = get_patient(bundle)
    if patient:
        evaluated.append(f"Patient/{patient.get('id')}")
    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Exclusions:
    - Alcohol use disorder starting during the year prior to measurement period.
    - History of dementia any time through end of measurement period.
    - Hospice during measurement period.
    - Death during measurement period.
    """
    evaluated: list[str] = []
    py_start, py_end = prior_year_dates(measurement_year)

    # Alcohol use disorder starting during prior year
    aud_codes = all_codes(VALUE_SETS, "Alcohol Use Disorder")
    if aud_codes:
        for cond, onset in find_conditions_with_codes(
            bundle, aud_codes, py_start, py_end
        ):
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    # Dementia - any time through end of measurement period
    dementia_codes = all_codes(VALUE_SETS, "Dementia")
    if dementia_codes:
        conditions = find_conditions_with_codes(bundle, dementia_codes, None, None)
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
    """
    Numerator 1 - Unhealthy Alcohol Use Screening: documented result between
    January 1 and November 1 of the measurement period.
    """
    evaluated: list[str] = []
    my_start, _ = measurement_year_dates(measurement_year)
    screening_end = date(measurement_year, 11, 1)

    screenings = _find_screening_observations(bundle, my_start, screening_end)
    if screenings:
        for obs, _ in screenings:
            evaluated.append(f"Observation/{obs.get('id')}")
        return True, evaluated

    return False, evaluated


def check_numerator_followup(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Numerator 2 - Follow-Up Care on Positive Screen: alcohol counseling or
    other follow-up on or up to 60 days after the first positive screen.
    """
    evaluated: list[str] = []
    my_start, _ = measurement_year_dates(measurement_year)
    screening_end = date(measurement_year, 11, 1)
    gender = get_patient_gender(bundle)

    screenings = _find_screening_observations(bundle, my_start, screening_end)
    screenings.sort(key=lambda x: x[1])

    # Find first positive screen
    first_positive_date: date | None = None
    for obs, obs_date in screenings:
        loinc = _get_observation_loinc(obs)
        score = _get_observation_score(obs)
        if loinc and score is not None and _is_positive_screen(loinc, score, gender):
            first_positive_date = obs_date
            evaluated.append(f"Observation/{obs.get('id')}")
            break

    if first_positive_date is None:
        return False, evaluated

    followup_end = first_positive_date + timedelta(days=60)

    # Alcohol Counseling or Other Follow Up Care value set
    counseling_codes = all_codes(
        VALUE_SETS, "Alcohol Counseling or Other Follow Up Care"
    )
    if counseling_codes:
        for enc, _ in find_encounters_with_codes(
            bundle, counseling_codes, first_positive_date, followup_end
        ):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated
        for proc, _ in find_procedures_with_codes(
            bundle, counseling_codes, first_positive_date, followup_end
        ):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    # ICD-10 Z71.41 - encounter for alcohol counseling and surveillance
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if not is_date_in_range(onset, first_positive_date, followup_end):
            continue
        for coding in cond.get("code", {}).get("coding", []):
            if coding.get("system") == ICD10CM and coding.get("code") == "Z71.41":
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    # Also check encounters with Z71.41 diagnosis
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, first_positive_date, followup_end):
            continue
        for reason in enc.get("reasonCode", []):
            for coding in reason.get("coding", []):
                if coding.get("system") == ICD10CM and coding.get("code") == "Z71.41":
                    evaluated.append(f"Encounter/{enc.get('id')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_asf_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate ASF-E measure for a patient bundle.

    Returns a FHIR MeasureReport with two rate groups:
    1. Unhealthy Alcohol Use Screening
    2. Follow-Up Care on Positive Screen
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    screened = False
    if is_eligible and not is_excluded:
        screened, screen_refs = check_numerator(bundle, measurement_year)
        all_evaluated.extend(screen_refs)

    # Rate 2: denominator is members from numerator 1 with positive screen
    has_followup = False
    positive_screen = False
    if screened:
        my_start, _ = measurement_year_dates(measurement_year)
        screening_end = date(measurement_year, 11, 1)
        gender = get_patient_gender(bundle)
        screenings = _find_screening_observations(bundle, my_start, screening_end)
        screenings.sort(key=lambda x: x[1])
        for obs, obs_date in screenings:
            loinc = _get_observation_loinc(obs)
            score = _get_observation_score(obs)
            if (
                loinc
                and score is not None
                and _is_positive_screen(loinc, score, gender)
            ):
                positive_screen = True
                break

        if positive_screen:
            has_followup, followup_refs = check_numerator_followup(
                bundle, measurement_year
            )
            all_evaluated.extend(followup_refs)

    groups = [
        {
            "code": "screening",
            "display": "Unhealthy Alcohol Use Screening",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": screened,
        },
        {
            "code": "followup",
            "display": "Follow-Up Care on Positive Screen",
            "initial_population": is_eligible and screened and positive_screen,
            "denominator_exclusion": is_excluded,
            "numerator": has_followup,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="ASF-E",
        measure_name="Unhealthy Alcohol Use Screening and Follow-Up",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
