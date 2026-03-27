"""
HEDIS MY 2025 - Appropriate Treatment for Upper Respiratory Infection (URI).

INVERSE measure: numerator = antibiotic dispensed (lower rate = better).
Episode-based: members 3 months+ with URI diagnosis who received antibiotics.
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
    find_conditions_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("URI")


def _get_intake_period(measurement_year: int) -> tuple[date, date]:
    """Intake period: July 1 prior year to June 30 measurement year."""
    return date(measurement_year - 1, 7, 1), date(measurement_year, 6, 30)


def _find_uri_episodes(bundle: dict, measurement_year: int) -> list[tuple[dict, date]]:
    """Identify eligible URI episodes after applying all filters.

    Steps: outpatient/ED/telehealth visits with URI diagnosis during intake,
    then filter for comorbid conditions, medication history, competing
    diagnoses, and deduplicate within 31-day windows.
    """
    intake_start, intake_end = _get_intake_period(measurement_year)
    birth_date = get_patient_birth_date(bundle)

    # Step 1: Outpatient/ED/Telehealth visits with URI diagnosis
    visit_codes = all_codes(VALUE_SETS, "Outpatient, ED and Telehealth")
    uri_codes = all_codes(VALUE_SETS, "URI")
    if not visit_codes or not uri_codes:
        return []

    episodes: list[tuple[dict, date]] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, intake_start, intake_end):
            continue
        if not resource_has_any_code(enc, visit_codes):
            has_visit_type = any(
                codeable_concept_has_any_code(t, visit_codes)
                for t in enc.get("type", [])
            )
            if not has_visit_type:
                continue
        # Check URI diagnosis
        has_uri = resource_has_any_code(enc, uri_codes)
        if not has_uri:
            for reason in enc.get("reasonCode", []):
                if codeable_concept_has_any_code(reason, uri_codes):
                    has_uri = True
                    break
        if not has_uri:
            continue
        # Age check: 3 months+ as of episode date
        if birth_date:
            age_days = (enc_date - birth_date).days
            if age_days < 90:
                continue
        episodes.append((enc, enc_date))

    if not episodes:
        return []

    # Step 2: Exclude visits resulting in inpatient stay
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    if inpatient_codes:
        inpatient_dates: set[date] = set()
        for enc in get_resources_by_type(bundle, "Encounter"):
            if resource_has_any_code(enc, inpatient_codes):
                enc_date = get_encounter_date(enc)
                if enc_date:
                    inpatient_dates.add(enc_date)
        episodes = [(e, d) for e, d in episodes if d not in inpatient_dates]

    # Step 3: Negative comorbid condition history (365 days prior)
    comorbid_codes = all_codes(VALUE_SETS, "Comorbid Conditions")
    if comorbid_codes:
        filtered = []
        for enc, ep_date in episodes:
            lookback = ep_date - timedelta(days=365)
            comorbids = find_conditions_with_codes(
                bundle, comorbid_codes, lookback, ep_date
            )
            if not comorbids:
                filtered.append((enc, ep_date))
        episodes = filtered

    # Step 4: Negative medication history (30 days prior)
    # Uses AAB Antibiotic Medications - check multiple possible value set names
    abx_codes = all_codes(VALUE_SETS, "AAB Antibiotic Medications")
    if not abx_codes:
        abx_codes = all_codes(VALUE_SETS, "Antibiotic Medications")
    if abx_codes:
        filtered = []
        for enc, ep_date in episodes:
            lookback = ep_date - timedelta(days=30)
            meds = find_medications_with_codes(
                bundle, abx_codes, lookback, ep_date - timedelta(days=1)
            )
            if not meds:
                filtered.append((enc, ep_date))
        episodes = filtered

    # Step 5: Negative competing diagnosis (episode date + 3 days)
    pharyngitis_codes = all_codes(VALUE_SETS, "Pharyngitis")
    competing_codes = all_codes(VALUE_SETS, "Competing Diagnosis")
    if pharyngitis_codes or competing_codes:
        filtered = []
        for enc, ep_date in episodes:
            window_end = ep_date + timedelta(days=3)
            has_competing = False
            if pharyngitis_codes:
                if find_conditions_with_codes(
                    bundle, pharyngitis_codes, ep_date, window_end
                ):
                    has_competing = True
            if not has_competing and competing_codes:
                if find_conditions_with_codes(
                    bundle, competing_codes, ep_date, window_end
                ):
                    has_competing = True
            if not has_competing:
                filtered.append((enc, ep_date))
        episodes = filtered

    # Step 7: Deduplicate within 31-day windows
    episodes.sort(key=lambda x: x[1])
    deduped: list[tuple[dict, date]] = []
    last_included: date | None = None
    for enc, ep_date in episodes:
        if last_included is None or (ep_date - last_included).days >= 31:
            deduped.append((enc, ep_date))
            last_included = ep_date

    return deduped


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if the patient has eligible URI episodes."""
    episodes = _find_uri_episodes(bundle, measurement_year)
    evaluated = [f"Encounter/{e.get('id')}" for e, _ in episodes]
    return len(episodes) > 0, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice, death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: antibiotic dispensed on or 3 days after episode date.

    INVERSE measure - numerator hit = bad outcome (antibiotic prescribed).
    """
    evaluated: list[str] = []
    episodes = _find_uri_episodes(bundle, measurement_year)
    if not episodes:
        return False, evaluated

    abx_codes = all_codes(VALUE_SETS, "AAB Antibiotic Medications")
    if not abx_codes:
        abx_codes = all_codes(VALUE_SETS, "Antibiotic Medications")
    if not abx_codes:
        return False, evaluated

    for enc, ep_date in episodes:
        window_end = ep_date + timedelta(days=3)
        meds = find_medications_with_codes(bundle, abx_codes, ep_date, window_end)
        if meds:
            evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in meds)
            return True, evaluated

    return False, evaluated


def calculate_uri_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate URI measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="URI",
        measure_name="Appropriate Treatment for Upper Respiratory Infection",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
