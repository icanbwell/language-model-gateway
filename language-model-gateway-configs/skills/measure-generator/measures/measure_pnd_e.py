"""
HEDIS MY 2025 - Prenatal Depression Screening and Follow-Up (PND-E).

The percentage of deliveries in which members were screened for clinical depression
while pregnant and, if screened positive, received follow-up care.

Rate 1 - Depression Screening: screened during pregnancy using a standardized
         instrument.
Rate 2 - Follow-Up on Positive Screen: received follow-up care within 30 days
         of a positive depression screen.
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
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    get_condition_onset,
    get_procedure_date,
    get_observation_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    ICD10CM,
    SNOMED,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("PND-E")

# Depression screening instruments - same as DSF-E
ADOLESCENT_SCREENING_INSTRUMENTS: list[dict] = [
    {"loinc": "44261-6", "name": "PHQ-9", "threshold": 10, "brief": False},
    {"loinc": "89204-2", "name": "PHQ-9M", "threshold": 10, "brief": False},
    {"loinc": "55758-7", "name": "PHQ-2", "threshold": 3, "brief": True},
    {"loinc": "89208-3", "name": "BDI-FS", "threshold": 8, "brief": True},
    {"loinc": "89205-9", "name": "CESD-R", "threshold": 17, "brief": False},
    {"loinc": "99046-5", "name": "EPDS", "threshold": 10, "brief": False},
    {"loinc": "71965-8", "name": "PROMIS Depression", "threshold": 60, "brief": False},
]

ADULT_SCREENING_INSTRUMENTS: list[dict] = [
    {"loinc": "44261-6", "name": "PHQ-9", "threshold": 10, "brief": False},
    {"loinc": "55758-7", "name": "PHQ-2", "threshold": 3, "brief": True},
    {"loinc": "89208-3", "name": "BDI-FS", "threshold": 8, "brief": True},
    {"loinc": "89209-1", "name": "BDI-II", "threshold": 20, "brief": False},
    {"loinc": "89205-9", "name": "CESD-R", "threshold": 17, "brief": False},
    {"loinc": "90853-3", "name": "DUKE-AD", "threshold": 30, "brief": False},
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

GESTATION_VS_NAMES = [
    "37 Weeks Gestation",
    "38 Weeks Gestation",
    "39 Weeks Gestation",
    "40 Weeks Gestation",
    "41 Weeks Gestation",
    "42 Weeks Gestation",
]


def _get_instruments_for_age(age: int) -> list[dict]:
    if age <= 17:
        return ADOLESCENT_SCREENING_INSTRUMENTS
    return ADULT_SCREENING_INSTRUMENTS


def _get_observation_loinc(obs: dict) -> str | None:
    for coding in obs.get("code", {}).get("coding", []):
        if coding.get("system") == LOINC and coding.get("code") in ALL_SCREENING_LOINCS:
            return coding["code"]
    return None


def _get_observation_score(obs: dict) -> float | None:
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
    instruments = _get_instruments_for_age(age)
    for instr in instruments:
        if instr["loinc"] == loinc_code:
            return score >= instr["threshold"]
    return False


def _find_screening_observations(
    bundle: dict, start: date, end: date
) -> list[tuple[dict, date]]:
    results = []
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, start, end):
            continue
        loinc = _get_observation_loinc(obs)
        if loinc and _get_observation_score(obs) is not None:
            results.append((obs, obs_date))
    return results


def _get_delivery_date(bundle: dict, my_start: date, my_end: date) -> date | None:
    delivery_codes = all_codes(VALUE_SETS, "Deliveries")
    if not delivery_codes:
        return None
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_end = get_encounter_end_date(enc) or get_encounter_date(enc)
        if not is_date_in_range(enc_end, my_start, my_end):
            continue
        if resource_has_any_code(enc, delivery_codes):
            return enc_end
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, delivery_codes):
                return enc_end
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not is_date_in_range(proc_date, my_start, my_end):
            continue
        if resource_has_any_code(proc, delivery_codes):
            return proc_date
    return None


def _get_gestational_age_weeks(bundle: dict, delivery_date: date) -> int | None:
    window_start = delivery_date - timedelta(days=1)
    window_end = delivery_date + timedelta(days=1)

    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, window_start, window_end):
            continue
        for coding in obs.get("code", {}).get("coding", []):
            if coding.get("system") == SNOMED and coding.get("code") == "412726003":
                value = obs.get("valueQuantity", {}).get("value")
                if value is not None:
                    return int(value)

    for vs_name in GESTATION_VS_NAMES:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        for cond, _ in find_conditions_with_codes(bundle, vs_codes, None, None):
            try:
                return int(vs_name.split(" ")[0])
            except ValueError:
                continue

    lt37_codes = all_codes(VALUE_SETS, "Weeks of Gestation Less Than 37")
    if lt37_codes:
        for cond, _ in find_conditions_with_codes(bundle, lt37_codes, None, None):
            return 36

    for cond in get_resources_by_type(bundle, "Condition"):
        for coding in cond.get("code", {}).get("coding", []):
            if coding.get("system") == ICD10CM and coding.get("code") == "Z3A.49":
                return 43

    return None


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Initial population: deliveries during the measurement period with a
    gestational age assessment or diagnosis within 1 day of delivery.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    delivery_date = _get_delivery_date(bundle, my_start, my_end)
    if not delivery_date:
        return False, evaluated

    gest_weeks = _get_gestational_age_weeks(bundle, delivery_date)
    if gest_weeks is None:
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
    - Deliveries at less than 37 weeks gestation.
    - Hospice during measurement period.
    - Death during measurement period.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    delivery_date = _get_delivery_date(bundle, my_start, my_end)
    if delivery_date:
        gest_weeks = _get_gestational_age_weeks(bundle, delivery_date)
        if gest_weeks is not None and gest_weeks < 37:
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
    """Not used directly; see calculate function."""
    return False, []


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_pnd_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate PND-E measure for a patient bundle.

    Returns a FHIR MeasureReport with two rate groups:
    1. Depression Screening
    2. Follow-Up on Positive Screen
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    screened = False
    positive_screen = False
    has_followup = False

    if is_eligible and not is_excluded:
        my_start, my_end = measurement_year_dates(measurement_year)
        delivery_date = _get_delivery_date(bundle, my_start, my_end)

        if delivery_date:
            gest_weeks = _get_gestational_age_weeks(bundle, delivery_date)
            pregnancy_start = (
                delivery_date - timedelta(weeks=gest_weeks)
                if gest_weeks
                else delivery_date - timedelta(weeks=40)
            )

            birth_date = get_patient_birth_date(bundle)
            age = calculate_age(birth_date, my_start) if birth_date else 18

            # Screening window: pregnancy start through delivery date
            # For deliveries Dec 2-31: screening through Dec 1
            if delivery_date <= date(measurement_year, 12, 1):
                screening_end = delivery_date
            else:
                screening_end = date(measurement_year, 12, 1)

            screenings = _find_screening_observations(
                bundle, pregnancy_start, screening_end
            )
            if screenings:
                screened = True
                for obs, _ in screenings:
                    all_evaluated.append(f"Observation/{obs.get('id')}")

                # Check for positive screen
                screenings.sort(key=lambda x: x[1])
                first_positive_date: date | None = None
                first_positive_loinc: str | None = None
                for obs, obs_date in screenings:
                    loinc = _get_observation_loinc(obs)
                    score = _get_observation_score(obs)
                    if (
                        loinc
                        and score is not None
                        and _is_positive_screen(loinc, score, age)
                    ):
                        first_positive_date = obs_date
                        first_positive_loinc = loinc
                        positive_screen = True
                        break

                if positive_screen and first_positive_date:
                    followup_end = first_positive_date + timedelta(days=30)

                    # Same-day negative full-length screen after brief positive
                    if first_positive_loinc in BRIEF_LOINCS:
                        for obs, obs_date in screenings:
                            if obs_date != first_positive_date:
                                continue
                            loinc = _get_observation_loinc(obs)
                            if loinc and loinc in FULL_LENGTH_LOINCS:
                                score = _get_observation_score(obs)
                                if score is not None and not _is_positive_screen(
                                    loinc, score, age
                                ):
                                    all_evaluated.append(f"Observation/{obs.get('id')}")
                                    has_followup = True

                    if not has_followup:
                        # Follow-up visit with depression diagnosis
                        fv_codes = all_codes(VALUE_SETS, "Follow Up Visit")
                        dep_bh_codes = all_codes(
                            VALUE_SETS,
                            "Depression or Other Behavioral Health Condition",
                        )
                        if fv_codes and dep_bh_codes:
                            for enc, _ in find_encounters_with_codes(
                                bundle, fv_codes, first_positive_date, followup_end
                            ):
                                for reason in enc.get("reasonCode", []):
                                    if codeable_concept_has_any_code(
                                        reason, dep_bh_codes
                                    ):
                                        all_evaluated.append(
                                            f"Encounter/{enc.get('id')}"
                                        )
                                        has_followup = True
                                        break
                                if has_followup:
                                    break

                    if not has_followup:
                        # Depression case management encounter
                        dcm_codes = all_codes(
                            VALUE_SETS, "Depression Case Management Encounter"
                        )
                        if dcm_codes:
                            for enc, _ in find_encounters_with_codes(
                                bundle, dcm_codes, first_positive_date, followup_end
                            ):
                                all_evaluated.append(f"Encounter/{enc.get('id')}")
                                has_followup = True
                                break

                    if not has_followup:
                        # Behavioral health encounter
                        bh_codes = all_codes(VALUE_SETS, "Behavioral Health Encounter")
                        if bh_codes:
                            for enc, _ in find_encounters_with_codes(
                                bundle, bh_codes, first_positive_date, followup_end
                            ):
                                all_evaluated.append(f"Encounter/{enc.get('id')}")
                                has_followup = True
                                break

                    if not has_followup:
                        # Exercise counseling (Z71.82)
                        for cond in get_resources_by_type(bundle, "Condition"):
                            onset = get_condition_onset(cond)
                            if not is_date_in_range(
                                onset, first_positive_date, followup_end
                            ):
                                continue
                            for coding in cond.get("code", {}).get("coding", []):
                                if (
                                    coding.get("system") == ICD10CM
                                    and coding.get("code") == "Z71.82"
                                ):
                                    all_evaluated.append(f"Condition/{cond.get('id')}")
                                    has_followup = True
                                    break
                            if has_followup:
                                break

                    if not has_followup:
                        # Antidepressant medication
                        antidep_codes = all_codes(
                            VALUE_SETS, "Antidepressant Medications"
                        )
                        if antidep_codes:
                            for med, _ in find_medications_with_codes(
                                bundle, antidep_codes, first_positive_date, followup_end
                            ):
                                all_evaluated.append(
                                    f"MedicationDispense/{med.get('id')}"
                                    if med.get("resourceType") == "MedicationDispense"
                                    else f"MedicationRequest/{med.get('id')}"
                                )
                                has_followup = True
                                break

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
        measure_abbreviation="PND-E",
        measure_name="Prenatal Depression Screening and Follow-Up",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
