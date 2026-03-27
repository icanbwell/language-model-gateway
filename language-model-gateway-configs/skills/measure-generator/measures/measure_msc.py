"""
HEDIS MY 2025 - Medical Assistance With Smoking and Tobacco Use Cessation (MSC).

Three indicators are reported:
  1. Advising Smokers and Tobacco Users to Quit
  2. Discussing Cessation Medications
  3. Discussing Cessation Strategies

This is primarily a survey-based (CAHPS) measure. For the administrative
specification path, we identify tobacco cessation counseling encounters
and tobacco cessation medication dispensing from claims data. This
implementation uses claims/encounter data to approximate the measure:

- Denominator: members 18+ identified as current smokers/tobacco users
  (via tobacco use diagnosis or screening observation).
- Indicator 1 (Advising): tobacco cessation counseling encounter.
- Indicator 2 (Medications): tobacco cessation medication dispensing or
  discussion of cessation medications in an encounter.
- Indicator 3 (Strategies): tobacco cessation counseling encounter that
  indicates discussion of strategies (same counseling codes used for
  indicator 1 serve as proxy).
"""

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    prior_year_dates,
    resource_has_any_code,
    get_observation_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    ICD10CM,
    CPT,
    HCPCS,
    LOINC,
    RXNORM,
)

VALUE_SETS = load_value_sets_from_csv("SMC")

# Common tobacco-related ICD-10-CM and SNOMED codes for identifying smokers
# when value sets are not available from the CSV
_TOBACCO_USE_ICD10 = {
    ICD10CM: {
        "F17.200",
        "F17.201",
        "F17.208",
        "F17.209",
        "F17.210",
        "F17.211",
        "F17.218",
        "F17.219",
        "F17.220",
        "F17.221",
        "F17.228",
        "F17.229",
        "F17.290",
        "F17.291",
        "F17.298",
        "F17.299",
        "Z72.0",  # Tobacco use
    },
}

_TOBACCO_CESSATION_COUNSELING_CPT = {
    CPT: {
        "99406",  # Smoking cessation counseling 3-10 min
        "99407",  # Smoking cessation counseling >10 min
        "1036F",  # Tobacco use counseling (CAT II)
        "4004F",  # Tobacco screening and cessation (CAT II)
    },
}

_TOBACCO_CESSATION_COUNSELING_HCPCS = {
    HCPCS: {
        "G0436",  # Smoking cessation counseling 3-10 min
        "G0437",  # Smoking cessation counseling >10 min
        "S9453",  # Smoking cessation counseling
    },
}

_TOBACCO_CESSATION_MED_CODES = {
    RXNORM: {
        # Varenicline
        "636671",
        "636676",
        "749289",
        "749762",
        "749766",
        "749768",
        # Bupropion (smoking cessation formulations)
        "42347",
        "42568",
        "993503",
        "993518",
        "993536",
        "993541",
        # Nicotine replacement
        "198029",
        "198030",
        "198031",
        "198045",
        "198046",
        "199888",
        "199889",
        "250983",
        "311975",
    },
}

# LOINC codes for tobacco screening observations
_TOBACCO_SCREENING_LOINC = {
    LOINC: {
        "72166-2",  # Tobacco smoking status NHIS
        "11367-0",  # History of tobacco use
        "81229-7",  # Tobacco use screening
        "39240-7",  # Tobacco use status
    },
}


def _is_tobacco_user(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Identify if patient is a current smoker/tobacco user.

    Uses tobacco use diagnoses and screening observations.
    """
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)
    evaluated: list[str] = []

    # Check for tobacco use diagnosis (conditions)
    tobacco_dx = all_codes(VALUE_SETS, "Tobacco Use")
    if not tobacco_dx:
        tobacco_dx = _TOBACCO_USE_ICD10

    conditions = find_conditions_with_codes(bundle, tobacco_dx, py_start, my_end)
    if conditions:
        for cond, _ in conditions:
            evaluated.append(f"Condition/{cond.get('id')}")
        return True, evaluated

    # Check for tobacco use observations (screening)
    screening_codes = _TOBACCO_SCREENING_LOINC
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not obs_date or not is_date_in_range(obs_date, py_start, my_end):
            continue
        if not resource_has_any_code(obs, screening_codes):
            continue

        # Check if the value indicates current use
        value_cc = obs.get("valueCodeableConcept", {})
        value_str = obs.get("valueString", "")
        for coding in value_cc.get("coding", []):
            code = coding.get("code", "")
            display = coding.get("display", "").lower()
            # SNOMED codes for current smoker
            if code in ("449868002", "428041000124106", "77176002", "65568007"):
                evaluated.append(f"Observation/{obs.get('id')}")
                return True, evaluated
            if "current" in display and ("smok" in display or "tobacco" in display):
                evaluated.append(f"Observation/{obs.get('id')}")
                return True, evaluated
        if value_str.lower() in (
            "current every day smoker",
            "current some day smoker",
            "smoker",
            "yes",
            "every day",
            "some days",
        ):
            evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

    return False, evaluated


def _has_cessation_counseling(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check for tobacco cessation counseling encounter during MY."""
    my_start, my_end = measurement_year_dates(measurement_year)
    evaluated: list[str] = []

    counseling_codes = all_codes(VALUE_SETS, "Tobacco Cessation Counseling")
    if not counseling_codes:
        counseling_codes = {
            **_TOBACCO_CESSATION_COUNSELING_CPT,
            **_TOBACCO_CESSATION_COUNSELING_HCPCS,
        }

    # Check encounters
    encounters = find_encounters_with_codes(bundle, counseling_codes, my_start, my_end)
    if encounters:
        for enc, _ in encounters:
            evaluated.append(f"Encounter/{enc.get('id')}")
        return True, evaluated

    # Check procedures
    procedures = find_procedures_with_codes(bundle, counseling_codes, my_start, my_end)
    if procedures:
        for proc, _ in procedures:
            evaluated.append(f"Procedure/{proc.get('id')}")
        return True, evaluated

    return False, evaluated


def _has_cessation_medication(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check for tobacco cessation medication dispensing during MY."""
    my_start, my_end = measurement_year_dates(measurement_year)
    evaluated: list[str] = []

    med_codes = all_codes(VALUE_SETS, "Tobacco Use Cessation Pharmacotherapy")
    if not med_codes:
        med_codes = _TOBACCO_CESSATION_MED_CODES

    meds = find_medications_with_codes(bundle, med_codes, my_start, my_end)
    if meds:
        for med, _ in meds:
            evaluated.append(
                f"{med.get('resourceType', 'MedicationDispense')}/{med.get('id')}"
            )
        return True, evaluated

    return False, evaluated


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient is 18+ and a current smoker/tobacco user."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 18:
        return False, []

    is_smoker, refs = _is_tobacco_user(bundle, measurement_year)
    return is_smoker, refs


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusion: death during MY."""
    from .hedis_common import check_death

    return check_death(bundle, measurement_year)


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check indicator 1: advised to quit (has cessation counseling)."""
    return _has_cessation_counseling(bundle, measurement_year)


def calculate_msc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the MSC measure with three indicators."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    # Indicator 1: Advising smokers to quit (counseling encounter)
    ind1_met = False
    if is_eligible and not is_excluded:
        ind1_met, ind1_refs = _has_cessation_counseling(bundle, measurement_year)
        all_evaluated.extend(ind1_refs)

    # Indicator 2: Discussing cessation medications
    ind2_met = False
    if is_eligible and not is_excluded:
        ind2_met, ind2_refs = _has_cessation_medication(bundle, measurement_year)
        all_evaluated.extend(ind2_refs)
        # Also count counseling encounters as potential medication discussion
        if not ind2_met:
            ind2_met = ind1_met

    # Indicator 3: Discussing cessation strategies
    # In administrative specification, same counseling codes serve as proxy
    ind3_met = False
    if is_eligible and not is_excluded:
        ind3_met = ind1_met

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="MSC",
        measure_name="Medical Assistance With Smoking and Tobacco Use Cessation",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "MSC-Advising",
                "display": "Advising Smokers and Tobacco Users to Quit",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": ind1_met,
            },
            {
                "code": "MSC-Medications",
                "display": "Discussing Cessation Medications",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": ind2_met,
            },
            {
                "code": "MSC-Strategies",
                "display": "Discussing Cessation Strategies",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": ind3_met,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
