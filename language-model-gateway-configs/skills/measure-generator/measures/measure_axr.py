"""
HEDIS MY 2025 - Antibiotic Utilization for Respiratory Conditions (AXR).

The percentage of episodes for members 3 months of age and older with a
diagnosis of a respiratory condition that resulted in an antibiotic
dispensing event.

This is an episode-based measure. The intake period is July 1 of the year
prior to the measurement year through June 30 of the measurement year.

For individual-level calculation, we identify qualifying respiratory
episodes and check whether an antibiotic was dispensed on or within 3 days
after the episode date.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_class,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("AXR")


def _intake_period(measurement_year: int) -> tuple[date, date]:
    """Return intake period: July 1 prior year through June 30 of MY."""
    return date(measurement_year - 1, 7, 1), date(measurement_year, 6, 30)


def _encounter_has_respiratory_dx(encounter: dict) -> bool:
    """Check if encounter has a respiratory condition diagnosis."""
    resp_codes = all_codes(VALUE_SETS, "Respiratory Conditions and Symptoms")
    if not resp_codes:
        return False
    # Check encounter reason/diagnosis references or type codes
    for t in encounter.get("type", []):
        if codeable_concept_has_any_code(t, resp_codes):
            return True
    if resource_has_any_code(encounter, resp_codes):
        return True
    # Check reasonCode on the encounter
    for rc in encounter.get("reasonCode", []):
        if codeable_concept_has_any_code(rc, resp_codes):
            return True
    return False


def _encounter_is_outpatient_or_ed(encounter: dict) -> bool:
    """Check if encounter is outpatient, ED, telephone, e-visit or virtual."""
    outpatient_ed_codes = all_codes(VALUE_SETS, "Outpatient, ED and Telehealth")
    if not outpatient_ed_codes:
        # Fallback: check encounter class
        enc_class = get_encounter_class(encounter)
        return enc_class in ("AMB", "EMER", "VR", "")
    if resource_has_any_code(encounter, outpatient_ed_codes):
        return True
    for t in encounter.get("type", []):
        if codeable_concept_has_any_code(t, outpatient_ed_codes):
            return True
    return False


def _encounter_results_in_inpatient(encounter: dict, bundle: dict) -> bool:
    """Check if an encounter resulted in an inpatient stay."""
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    if not inpatient_codes:
        return False
    enc_date = get_encounter_date(encounter)
    if not enc_date:
        return False
    for enc in get_resources_by_type(bundle, "Encounter"):
        if resource_has_any_code(enc, inpatient_codes):
            ip_date = get_encounter_date(enc)
            if ip_date and ip_date == enc_date:
                return True
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, inpatient_codes):
                ip_date = get_encounter_date(enc)
                if ip_date and ip_date == enc_date:
                    return True
    return False


def _has_comorbid_condition(bundle: dict, episode_date: date) -> bool:
    """Check for comorbid conditions in 365 days prior to and including episode."""
    comorbid_codes = all_codes(VALUE_SETS, "Comorbid Conditions")
    if not comorbid_codes:
        return False
    lookback_start = episode_date - timedelta(days=365)
    conditions = find_conditions_with_codes(
        bundle, comorbid_codes, lookback_start, episode_date
    )
    return len(conditions) > 0


def _has_competing_diagnosis(bundle: dict, episode_date: date) -> bool:
    """Check for competing diagnosis on episode date or 3 days after."""
    competing_codes = all_codes(VALUE_SETS, "AXR Competing Diagnosis")
    if not competing_codes:
        return False
    window_end = episode_date + timedelta(days=3)
    conditions = find_conditions_with_codes(
        bundle, competing_codes, episode_date, window_end
    )
    if conditions:
        return True
    encounters = find_encounters_with_codes(
        bundle, competing_codes, episode_date, window_end
    )
    return len(encounters) > 0


def _has_active_antibiotic(bundle: dict, episode_date: date) -> bool:
    """Check for antibiotic in 30-day lookback or active on episode date."""
    # Use AXR Antibiotic Medications value set if available; otherwise use
    # generic antibiotic-related value sets from the CSV
    antibiotic_codes: dict[str, set[str]] = {}
    for vs_name in VALUE_SETS:
        if "antibiotic" in vs_name.lower():
            for sys, codes in VALUE_SETS[vs_name].items():
                antibiotic_codes.setdefault(sys, set()).update(codes)
    if not antibiotic_codes:
        return False
    lookback_start = episode_date - timedelta(days=30)
    meds = find_medications_with_codes(
        bundle, antibiotic_codes, lookback_start, episode_date - timedelta(days=1)
    )
    return len(meds) > 0


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Identify if the patient has at least one qualifying respiratory episode.

    A qualifying episode is an outpatient/ED/telehealth visit with a respiratory
    diagnosis during the intake period, for a member >= 3 months old, after
    applying negative history filters.
    """
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    intake_start, intake_end = _intake_period(measurement_year)
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, intake_start, intake_end):
            continue
        if not _encounter_is_outpatient_or_ed(enc):
            continue
        if not _encounter_has_respiratory_dx(enc):
            continue

        # Age must be >= 3 months at episode date
        age_days = (enc_date - birth_date).days
        if age_days < 90:
            continue

        # Exclude if results in inpatient stay
        if _encounter_results_in_inpatient(enc, bundle):
            continue

        # Negative comorbid condition history (365 days)
        if _has_comorbid_condition(bundle, enc_date):
            continue

        # Negative medication history (30-day lookback)
        if _has_active_antibiotic(bundle, enc_date):
            continue

        # Negative competing diagnosis (episode date + 3 days)
        if _has_competing_diagnosis(bundle, enc_date):
            continue

        evaluated.append(f"Encounter/{enc.get('id')}")
        return True, evaluated

    return False, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusion: hospice."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if antibiotic was dispensed on or within 3 days of episode date.

    For individual patient calculation, we check the first qualifying episode.
    """
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    intake_start, intake_end = _intake_period(measurement_year)
    evaluated: list[str] = []

    # Collect antibiotic codes across all antibiotic-related value sets
    antibiotic_codes: dict[str, set[str]] = {}
    for vs_name in VALUE_SETS:
        if "antibiotic" in vs_name.lower():
            for sys, codes in VALUE_SETS[vs_name].items():
                antibiotic_codes.setdefault(sys, set()).update(codes)

    if not antibiotic_codes:
        return False, []

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, intake_start, intake_end):
            continue
        if not _encounter_is_outpatient_or_ed(enc):
            continue
        if not _encounter_has_respiratory_dx(enc):
            continue

        age_days = (enc_date - birth_date).days
        if age_days < 90:
            continue

        if _encounter_results_in_inpatient(enc, bundle):
            continue
        if _has_comorbid_condition(bundle, enc_date):
            continue
        if _has_active_antibiotic(bundle, enc_date):
            continue
        if _has_competing_diagnosis(bundle, enc_date):
            continue

        # This is a qualifying episode - check for antibiotic dispensing
        dispense_window_end = enc_date + timedelta(days=3)
        meds = find_medications_with_codes(
            bundle, antibiotic_codes, enc_date, dispense_window_end
        )
        if meds:
            for med, _ in meds:
                evaluated.append(
                    f"{med.get('resourceType', 'MedicationDispense')}/{med.get('id')}"
                )
            return True, evaluated

        return False, evaluated

    return False, evaluated


def calculate_axr_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the AXR measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="AXR",
        measure_name="Antibiotic Utilization for Respiratory Conditions",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
