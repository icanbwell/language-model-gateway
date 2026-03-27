"""
HEDIS MY 2025 - Prenatal Immunization Status (PRS-E).

The percentage of deliveries in the measurement period in which members had
received influenza and tetanus, diphtheria toxoids and acellular pertussis
(Tdap) vaccinations.

Rate 1 - Influenza: received influenza vaccine between July 1 of prior year
         and delivery date.
Rate 2 - Tdap: received Tdap vaccine during pregnancy.
Rate 3 - Combination: met criteria for both Rate 1 and Rate 2.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient,
    get_patient_id,
    get_resources_by_type,
    parse_date,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    get_condition_onset,
    get_procedure_date,
    get_observation_date,
    find_conditions_with_codes,
    find_procedures_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    ICD10CM,
    SNOMED,
    CVX,
)

VALUE_SETS = load_value_sets_from_csv("PRS-E")

# Gestational age value set names
GESTATION_VS_NAMES = [
    "37 Weeks Gestation",
    "38 Weeks Gestation",
    "39 Weeks Gestation",
    "40 Weeks Gestation",
    "41 Weeks Gestation",
    "42 Weeks Gestation",
]


def _find_immunizations(
    bundle: dict,
    code_sets: dict[str, set[str]],
    start: date | None = None,
    end: date | None = None,
) -> list[tuple[dict, date | None]]:
    """Find Immunization resources matching code sets within optional date range."""
    results = []
    for imm in get_resources_by_type(bundle, "Immunization"):
        imm_date = parse_date(imm.get("occurrenceDateTime"))
        if start and end and not is_date_in_range(imm_date, start, end):
            continue
        if start and not end and imm_date and imm_date < start:
            continue
        if end and not start and imm_date and imm_date > end:
            continue
        vaccine_code = imm.get("vaccineCode", {})
        if codeable_concept_has_any_code(vaccine_code, code_sets):
            results.append((imm, imm_date))
    return results


def _get_delivery_date(bundle: dict, measurement_year: int) -> date | None:
    """Find a delivery during the measurement period."""
    my_start, my_end = measurement_year_dates(measurement_year)
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

    # Check procedures
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not is_date_in_range(proc_date, my_start, my_end):
            continue
        if resource_has_any_code(proc, delivery_codes):
            return proc_date

    return None


def _get_gestational_age_weeks(bundle: dict, delivery_date: date) -> int | None:
    """Get gestational age in weeks from observations or diagnoses near delivery."""
    window_start = delivery_date - timedelta(days=1)
    window_end = delivery_date + timedelta(days=1)

    # Check SNOMED CT 412726003 observation
    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not is_date_in_range(obs_date, window_start, window_end):
            continue
        for coding in obs.get("code", {}).get("coding", []):
            if coding.get("system") == SNOMED and coding.get("code") == "412726003":
                value = obs.get("valueQuantity", {}).get("value")
                if value is not None:
                    return int(value)

    # Check gestational age diagnosis codes
    for vs_name in GESTATION_VS_NAMES:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        for cond, onset in find_conditions_with_codes(bundle, vs_codes, None, None):
            # Extract weeks from value set name
            weeks_str = vs_name.split(" ")[0]
            try:
                return int(weeks_str)
            except ValueError:
                continue

    # Check for < 37 weeks
    lt37_codes = all_codes(VALUE_SETS, "Weeks of Gestation Less Than 37")
    if lt37_codes:
        for cond, _ in find_conditions_with_codes(bundle, lt37_codes, None, None):
            return 36  # Less than 37

    # Check for 43 weeks (Z3A.49)
    for cond in get_resources_by_type(bundle, "Condition"):
        for coding in cond.get("code", {}).get("coding", []):
            if coding.get("system") == ICD10CM and coding.get("code") == "Z3A.49":
                return 43

    return None


def _calculate_pregnancy_start(delivery_date: date, gestational_weeks: int) -> date:
    """Calculate pregnancy start date from delivery date and gestational age."""
    return delivery_date - timedelta(weeks=gestational_weeks)


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

    delivery_date = _get_delivery_date(bundle, measurement_year)
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

    delivery_date = _get_delivery_date(bundle, measurement_year)
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
    """Not used directly; see calculate function for multi-rate logic."""
    return False, []


def _check_influenza(
    bundle: dict, measurement_year: int, delivery_date: date
) -> tuple[bool, list[str]]:
    """
    Numerator 1 - Influenza: received influenza vaccine between July 1 of
    prior year and delivery date, or anaphylaxis contraindication.
    """
    evaluated: list[str] = []
    flu_start = date(measurement_year - 1, 7, 1)

    for vs_name in (
        "Adult Influenza Immunization",
        "Influenza Virus LAIV Immunization",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if vs_codes:
            for imm, _ in _find_immunizations(
                bundle, vs_codes, flu_start, delivery_date
            ):
                evaluated.append(f"Immunization/{imm.get('id')}")
                return True, evaluated

    for vs_name in (
        "Adult Influenza Vaccine Procedure",
        "Influenza Virus LAIV Vaccine Procedure",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if vs_codes:
            for proc, _ in find_procedures_with_codes(
                bundle, vs_codes, flu_start, delivery_date
            ):
                evaluated.append(f"Procedure/{proc.get('id')}")
                return True, evaluated

    # Anaphylaxis contraindication
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if onset and onset > delivery_date:
            continue
        for coding in cond.get("code", {}).get("coding", []):
            if (
                coding.get("system") == SNOMED
                and coding.get("code") == "471361000124100"
            ):
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    return False, evaluated


def _check_tdap(
    bundle: dict, pregnancy_start: date, delivery_date: date
) -> tuple[bool, list[str]]:
    """
    Numerator 2 - Tdap: received Tdap vaccine during pregnancy, or
    contraindications on or before delivery date.
    """
    evaluated: list[str] = []

    # Tdap (CVX 115) during pregnancy
    tdap_imms = _find_immunizations(
        bundle, {CVX: {"115"}}, pregnancy_start, delivery_date
    )
    if tdap_imms:
        evaluated.append(f"Immunization/{tdap_imms[0][0].get('id')}")
        return True, evaluated

    tdap_proc_codes = all_codes(VALUE_SETS, "Tdap Vaccine Procedure")
    if tdap_proc_codes:
        for proc, _ in find_procedures_with_codes(
            bundle, tdap_proc_codes, pregnancy_start, delivery_date
        ):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    # Contraindications
    anaph_codes = all_codes(
        VALUE_SETS, "Anaphylaxis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if anaph_codes:
        for cond, onset in find_conditions_with_codes(bundle, anaph_codes, None, None):
            if onset is None or onset <= delivery_date:
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    enceph_codes = all_codes(
        VALUE_SETS, "Encephalitis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if enceph_codes:
        for cond, onset in find_conditions_with_codes(bundle, enceph_codes, None, None):
            if onset is None or onset <= delivery_date:
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_prs_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate PRS-E measure for a patient bundle.

    Returns a FHIR MeasureReport with three rate groups:
    1. Immunization Status: Influenza
    2. Immunization Status: Tdap
    3. Immunization Status: Combination
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    flu_met = False
    tdap_met = False
    combination_met = False

    if is_eligible and not is_excluded:
        delivery_date = _get_delivery_date(bundle, measurement_year)
        if delivery_date:
            gest_weeks = _get_gestational_age_weeks(bundle, delivery_date)
            pregnancy_start = (
                _calculate_pregnancy_start(delivery_date, gest_weeks)
                if gest_weeks
                else delivery_date - timedelta(weeks=40)
            )

            flu_met, flu_refs = _check_influenza(
                bundle, measurement_year, delivery_date
            )
            all_evaluated.extend(flu_refs)

            tdap_met, tdap_refs = _check_tdap(bundle, pregnancy_start, delivery_date)
            all_evaluated.extend(tdap_refs)

            combination_met = flu_met and tdap_met

    groups = [
        {
            "code": "influenza",
            "display": "Immunization Status: Influenza",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": flu_met,
        },
        {
            "code": "tdap",
            "display": "Immunization Status: Tdap",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": tdap_met,
        },
        {
            "code": "combination",
            "display": "Immunization Status: Combination",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": combination_met,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="PRS-E",
        measure_name="Prenatal Immunization Status",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
