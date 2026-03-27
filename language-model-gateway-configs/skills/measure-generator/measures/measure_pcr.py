"""
HEDIS MY 2025 - Plan All-Cause Readmissions (PCR).

For members 18 years of age and older, the number of acute inpatient and
observation stays during the measurement year that were followed by an
unplanned acute readmission for any diagnosis within 30 days.

This is a discharge-based, risk-adjusted measure. For individual patient
calculation we report the observed readmission (not expected), identifying
whether any Index Hospital Stay (IHS) had an unplanned readmission within
30 days.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    parse_date,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("PCR")


def _get_acute_stays(bundle: dict) -> list[dict]:
    """Identify acute inpatient and observation stays from the bundle.

    Returns encounters that are inpatient/observation but not nonacute.
    """
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    observation_codes = all_codes(VALUE_SETS, "Observation Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")

    acute_stays = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        is_inpatient = False
        is_nonacute = False

        if inpatient_codes and (
            resource_has_any_code(enc, inpatient_codes)
            or any(
                codeable_concept_has_any_code(t, inpatient_codes)
                for t in enc.get("type", [])
            )
        ):
            is_inpatient = True

        if observation_codes and (
            resource_has_any_code(enc, observation_codes)
            or any(
                codeable_concept_has_any_code(t, observation_codes)
                for t in enc.get("type", [])
            )
        ):
            is_inpatient = True

        if nonacute_codes and (
            resource_has_any_code(enc, nonacute_codes)
            or any(
                codeable_concept_has_any_code(t, nonacute_codes)
                for t in enc.get("type", [])
            )
        ):
            is_nonacute = True

        if is_inpatient and not is_nonacute:
            acute_stays.append(enc)

    return acute_stays


def _is_planned_stay(encounter: dict) -> bool:
    """Check if a hospital stay is planned (numerator exclusion)."""
    chemo_codes = all_codes(VALUE_SETS, "Chemotherapy Encounter")
    rehab_codes = all_codes(VALUE_SETS, "Rehabilitation")
    kidney_codes = all_codes(VALUE_SETS, "Kidney Transplant")
    bmt_codes = all_codes(VALUE_SETS, "Bone Marrow Transplant")
    organ_codes = all_codes(VALUE_SETS, "Organ Transplant Other Than Kidney")
    pancreatic_codes = all_codes(
        VALUE_SETS, "Introduction of Autologous Pancreatic Cells"
    )
    planned_proc_codes = all_codes(VALUE_SETS, "Potentially Planned Procedures")
    acute_dx_codes = all_codes(VALUE_SETS, "Acute Condition")

    # Principal diagnosis of maintenance chemotherapy
    if chemo_codes and resource_has_any_code(encounter, chemo_codes):
        return True

    # Principal diagnosis of rehabilitation
    if rehab_codes and resource_has_any_code(encounter, rehab_codes):
        return True

    # Organ transplant
    for transplant_codes in (kidney_codes, bmt_codes, organ_codes, pancreatic_codes):
        if transplant_codes and resource_has_any_code(encounter, transplant_codes):
            return True
        if transplant_codes:
            for t in encounter.get("type", []):
                if codeable_concept_has_any_code(t, transplant_codes):
                    return True

    # Potentially planned procedure without principal acute diagnosis
    if planned_proc_codes:
        has_planned = resource_has_any_code(encounter, planned_proc_codes) or any(
            codeable_concept_has_any_code(t, planned_proc_codes)
            for t in encounter.get("type", [])
        )
        if has_planned:
            has_acute = acute_dx_codes and (
                resource_has_any_code(encounter, acute_dx_codes)
                or any(
                    codeable_concept_has_any_code(t, acute_dx_codes)
                    for t in encounter.get("type", [])
                )
            )
            if not has_acute:
                return True

    return False


def _has_pregnancy_or_perinatal(encounter: dict) -> bool:
    """Check if encounter has pregnancy or perinatal principal diagnosis."""
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy")
    perinatal_codes = all_codes(VALUE_SETS, "Perinatal Conditions")

    if pregnancy_codes and resource_has_any_code(encounter, pregnancy_codes):
        return True
    if perinatal_codes and resource_has_any_code(encounter, perinatal_codes):
        return True
    return False


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Identify if patient has an IHS with discharge Jan 1 - Dec 1 of MY.

    Patient must be 18+ as of Index Discharge Date.
    """
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    ihs_start = date(measurement_year, 1, 1)
    ihs_end = date(measurement_year, 12, 1)
    evaluated: list[str] = []

    acute_stays = _get_acute_stays(bundle)
    for stay in acute_stays:
        discharge_date = get_encounter_end_date(stay)
        admission_date = get_encounter_date(stay)
        if not discharge_date or not is_date_in_range(
            discharge_date, ihs_start, ihs_end
        ):
            continue

        # Must be 18+ as of discharge date
        age = calculate_age(birth_date, discharge_date)
        if age < 18:
            continue

        # Exclude same-day stays
        if admission_date and admission_date == discharge_date:
            continue

        # Exclude death during stay
        patient = get_patient(bundle)
        if patient:
            deceased_dt = patient.get("deceasedDateTime")
            if deceased_dt:
                death = parse_date(deceased_dt)
                if (
                    death
                    and admission_date
                    and death >= admission_date
                    and death <= discharge_date
                ):
                    continue

        # Exclude pregnancy and perinatal
        if _has_pregnancy_or_perinatal(stay):
            continue

        evaluated.append(f"Encounter/{stay.get('id')}")
        return True, evaluated

    return False, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusion: hospice."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if any IHS had an unplanned acute readmission within 30 days.

    For individual reporting, we use observed (not expected) readmission.
    """
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    ihs_start = date(measurement_year, 1, 1)
    ihs_end = date(measurement_year, 12, 1)
    evaluated: list[str] = []

    acute_stays = _get_acute_stays(bundle)

    # Build list of IHS discharges
    ihs_discharges: list[tuple[dict, date]] = []
    for stay in acute_stays:
        discharge_date = get_encounter_end_date(stay)
        admission_date = get_encounter_date(stay)
        if not discharge_date or not is_date_in_range(
            discharge_date, ihs_start, ihs_end
        ):
            continue
        age = calculate_age(birth_date, discharge_date)
        if age < 18:
            continue
        if admission_date and admission_date == discharge_date:
            continue
        if _has_pregnancy_or_perinatal(stay):
            continue
        ihs_discharges.append((stay, discharge_date))

    # Build list of potential readmission stays
    readmission_candidates: list[tuple[dict, date]] = []
    for stay in acute_stays:
        admission_date = get_encounter_date(stay)
        if not admission_date:
            continue
        if _has_pregnancy_or_perinatal(stay):
            continue
        if _is_planned_stay(stay):
            continue
        readmission_candidates.append((stay, admission_date))

    # Check each IHS for readmission within 30 days
    for ihs, ihs_discharge in ihs_discharges:
        for readmit, readmit_admission in readmission_candidates:
            if readmit.get("id") == ihs.get("id"):
                continue
            days_diff = (readmit_admission - ihs_discharge).days
            if 1 <= days_diff <= 30:
                evaluated.append(f"Encounter/{readmit.get('id')}")
                return True, evaluated

    return False, evaluated


def calculate_pcr_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the PCR measure (observed readmission for individual)."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="PCR",
        measure_name="Plan All-Cause Readmissions",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
