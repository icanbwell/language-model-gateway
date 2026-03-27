"""
HEDIS MY 2025 - Depression Screening and Follow-Up for Adolescents and Adults (DSF-E).

The percentage of members 12 years of age and older who were screened for clinical
depression using a standardized instrument and, if screened positive, received
follow-up care.

Rate 1 - Depression Screening: screened using a standardized instrument.
Rate 2 - Follow-Up on Positive Screen: received follow-up care within 30 days of
         a positive depression screen.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    prior_year_dates,
    codeable_concept_has_any_code,
    get_condition_onset,
    get_observation_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    ICD10CM,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("DSF-E")

# ---------------------------------------------------------------------------
# Depression screening instrument LOINC codes and positive thresholds
# ---------------------------------------------------------------------------

# Adolescent instruments (<=17)
ADOLESCENT_SCREENING_INSTRUMENTS: list[dict] = [
    {"loinc": "44261-6", "name": "PHQ-9", "threshold": 10, "brief": False},
    {"loinc": "89204-2", "name": "PHQ-9M", "threshold": 10, "brief": False},
    {"loinc": "55758-7", "name": "PHQ-2", "threshold": 3, "brief": True},
    {"loinc": "89208-3", "name": "BDI-FS", "threshold": 8, "brief": True},
    {"loinc": "89205-9", "name": "CESD-R", "threshold": 17, "brief": False},
    {"loinc": "99046-5", "name": "EPDS", "threshold": 10, "brief": False},
    {"loinc": "71965-8", "name": "PROMIS Depression", "threshold": 60, "brief": False},
]

# Adult instruments (18+)
ADULT_SCREENING_INSTRUMENTS: list[dict] = [
    {"loinc": "44261-6", "name": "PHQ-9", "threshold": 10, "brief": False},
    {"loinc": "55758-7", "name": "PHQ-2", "threshold": 3, "brief": True},
    {"loinc": "89208-3", "name": "BDI-FS", "threshold": 8, "brief": True},
    {"loinc": "89209-1", "name": "BDI-II", "threshold": 20, "brief": False},
    {"loinc": "89205-9", "name": "CESD-R", "threshold": 17, "brief": False},
    {"loinc": "90853-3", "name": "DUKE-AD", "threshold": 30, "brief": False},
    {"loinc": "48545-8", "name": "GDS Short", "threshold": 5, "brief": True},
    {"loinc": "48544-1", "name": "GDS Long", "threshold": 10, "brief": False},
    {"loinc": "99046-5", "name": "EPDS", "threshold": 10, "brief": False},
    {"loinc": "71777-7", "name": "M3", "threshold": 5, "brief": False},
    {"loinc": "71965-8", "name": "PROMIS Depression", "threshold": 60, "brief": False},
    {"loinc": "90221-3", "name": "CUDOS", "threshold": 31, "brief": False},
]

ALL_SCREENING_LOINCS = {i["loinc"] for i in ADOLESCENT_SCREENING_INSTRUMENTS} | {
    i["loinc"] for i in ADULT_SCREENING_INSTRUMENTS
}
BRIEF_LOINCS = {i["loinc"] for i in ADOLESCENT_SCREENING_INSTRUMENTS if i["brief"]} | {
    i["loinc"] for i in ADULT_SCREENING_INSTRUMENTS if i["brief"]
}
FULL_LENGTH_LOINCS = ALL_SCREENING_LOINCS - BRIEF_LOINCS


def _get_instruments_for_age(age: int) -> list[dict]:
    """Return the appropriate screening instruments based on age."""
    if age <= 17:
        return ADOLESCENT_SCREENING_INSTRUMENTS
    return ADULT_SCREENING_INSTRUMENTS


def _get_observation_loinc(obs: dict) -> str | None:
    """Extract the LOINC code from an observation."""
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


def _is_positive_screen(loinc_code: str, score: float, age: int) -> bool:
    """Determine if a screening score is positive based on the instrument."""
    instruments = _get_instruments_for_age(age)
    for instr in instruments:
        if instr["loinc"] == loinc_code:
            return score >= instr["threshold"]
    return False


def _find_screening_observations(
    bundle: dict, start: date, end: date
) -> list[tuple[dict, date]]:
    """Find all depression screening observations in the date range."""
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
    """
    Initial population: members 12 years and older at the start of
    the measurement period.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 12:
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
    - Bipolar disorder any time through end of year prior to measurement period.
    - Depression starting during the year prior to the measurement period.
    - Hospice during measurement period.
    - Death during measurement period.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    # Bipolar disorder - any time through end of prior year
    for vs_name in ("Bipolar Disorder", "Other Bipolar Disorder"):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        conditions = find_conditions_with_codes(bundle, vs_codes, None, None)
        for cond, onset in conditions:
            if onset is None or onset <= py_end:
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    # Depression starting during prior year
    depression_codes = all_codes(VALUE_SETS, "Depression")
    if depression_codes:
        for cond, onset in find_conditions_with_codes(
            bundle, depression_codes, py_start, py_end
        ):
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
    Numerator 1 - Depression Screening: documented result for depression
    screening between January 1 and December 1 of the measurement period.
    """
    evaluated: list[str] = []
    my_start, _ = measurement_year_dates(measurement_year)
    screening_end = date(measurement_year, 12, 1)

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
    Numerator 2 - Follow-Up on Positive Screen: follow-up care on or up
    to 30 days after the date of the first positive screen.
    """
    evaluated: list[str] = []
    my_start, _ = measurement_year_dates(measurement_year)
    screening_end = date(measurement_year, 12, 1)
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    age = calculate_age(birth_date, my_start)

    # Find the first positive screen
    screenings = _find_screening_observations(bundle, my_start, screening_end)
    screenings.sort(key=lambda x: x[1])

    first_positive_date: date | None = None
    first_positive_loinc: str | None = None
    for obs, obs_date in screenings:
        loinc = _get_observation_loinc(obs)
        score = _get_observation_score(obs)
        if loinc and score is not None and _is_positive_screen(loinc, score, age):
            first_positive_date = obs_date
            first_positive_loinc = loinc
            evaluated.append(f"Observation/{obs.get('id')}")
            break

    if first_positive_date is None:
        return False, evaluated

    followup_end = first_positive_date + timedelta(days=30)

    # Check for same-day negative full-length screen after brief positive
    if first_positive_loinc in BRIEF_LOINCS:
        for obs, obs_date in screenings:
            if obs_date != first_positive_date:
                continue
            loinc = _get_observation_loinc(obs)
            if loinc and loinc in FULL_LENGTH_LOINCS:
                score = _get_observation_score(obs)
                if score is not None and not _is_positive_screen(loinc, score, age):
                    evaluated.append(f"Observation/{obs.get('id')}")
                    return True, evaluated

    # Follow-up visit with depression/behavioral health diagnosis
    followup_visit_codes = all_codes(VALUE_SETS, "Follow Up Visit")
    dep_bh_codes = all_codes(
        VALUE_SETS, "Depression or Other Behavioral Health Condition"
    )
    if followup_visit_codes and dep_bh_codes:
        for enc, enc_date in find_encounters_with_codes(
            bundle, followup_visit_codes, first_positive_date, followup_end
        ):
            # Check encounter diagnoses
            for reason in enc.get("reasonCode", []):
                if codeable_concept_has_any_code(reason, dep_bh_codes):
                    evaluated.append(f"Encounter/{enc.get('id')}")
                    return True, evaluated
            # Check conditions linked to encounter
            for cond, _ in find_conditions_with_codes(bundle, dep_bh_codes, None, None):
                cond_enc = cond.get("encounter", {}).get("reference", "")
                if enc.get("id") and enc["id"] in cond_enc:
                    evaluated.append(f"Encounter/{enc.get('id')}")
                    return True, evaluated

    # Depression case management encounter
    dcm_codes = all_codes(VALUE_SETS, "Depression Case Management Encounter")
    symptom_codes = all_codes(VALUE_SETS, "Symptoms of Depression")
    if dcm_codes:
        for enc, _ in find_encounters_with_codes(
            bundle, dcm_codes, first_positive_date, followup_end
        ):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

    # Behavioral health encounter
    bh_codes = all_codes(VALUE_SETS, "Behavioral Health Encounter")
    if bh_codes:
        for enc, _ in find_encounters_with_codes(
            bundle, bh_codes, first_positive_date, followup_end
        ):
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

    # Exercise counseling diagnosis (ICD-10 Z71.82)
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if not is_date_in_range(onset, first_positive_date, followup_end):
            continue
        for coding in cond.get("code", {}).get("coding", []):
            if coding.get("system") == ICD10CM and coding.get("code") == "Z71.82":
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    # Dispensed antidepressant medication
    antidep_codes = all_codes(VALUE_SETS, "Antidepressant Medications")
    if antidep_codes:
        for med, _ in find_medications_with_codes(
            bundle, antidep_codes, first_positive_date, followup_end
        ):
            evaluated.append(
                f"MedicationDispense/{med.get('id')}"
                if med.get("resourceType") == "MedicationDispense"
                else f"MedicationRequest/{med.get('id')}"
            )
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_dsf_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate DSF-E measure for a patient bundle.

    Returns a FHIR MeasureReport with two rate groups:
    1. Depression Screening
    2. Follow-Up on Positive Screen
    """
    all_evaluated: list[str] = []

    # Check eligible population
    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    # Check exclusions
    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    # Rate 1: Depression Screening
    screened = False
    if is_eligible and not is_excluded:
        screened, screen_refs = check_numerator(bundle, measurement_year)
        all_evaluated.extend(screen_refs)

    # Rate 2: Follow-Up on Positive Screen
    # Denominator 2 = members from numerator 1 with positive screen Jan 1 - Dec 1
    has_followup = False
    positive_screen = False
    if screened:
        my_start, _ = measurement_year_dates(measurement_year)
        screening_end = date(measurement_year, 12, 1)
        birth_date = get_patient_birth_date(bundle)
        if birth_date:
            age = calculate_age(birth_date, my_start)
            screenings = _find_screening_observations(bundle, my_start, screening_end)
            screenings.sort(key=lambda x: x[1])
            for obs, obs_date in screenings:
                loinc = _get_observation_loinc(obs)
                score = _get_observation_score(obs)
                if (
                    loinc
                    and score is not None
                    and _is_positive_screen(loinc, score, age)
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
            "display": "Depression Screening",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": screened,
        },
        {
            "code": "followup",
            "display": "Follow-Up on Positive Screen",
            "initial_population": is_eligible and screened and positive_screen,
            "denominator_exclusion": is_excluded,
            "numerator": has_followup,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="DSF-E",
        measure_name="Depression Screening and Follow-Up for Adolescents and Adults",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
