"""
HEDIS MY 2025 - Use of Imaging Studies for Low Back Pain (LBP).

INVERSE measure: numerator = imaging study occurred (lower rate = better).
Members 18-75 with low back pain who had imaging within 28 days of diagnosis.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_condition_onset,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("LBP")


def _find_iesd(bundle: dict, measurement_year: int) -> date | None:
    """Find the Index Episode Start Date (IESD).

    Earliest encounter with uncomplicated low back pain during intake period
    (Jan 1 - Dec 3 of MY), with no LBP diagnosis in 180 days prior.
    """
    intake_start = date(measurement_year, 1, 1)
    intake_end = date(measurement_year, 12, 3)

    lbp_codes = all_codes(VALUE_SETS, "Uncomplicated Low Back Pain")
    if not lbp_codes:
        return None

    # Find all LBP encounters in intake period
    lbp_encounters: list[date] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, intake_start, intake_end):
            continue
        if resource_has_any_code(enc, lbp_codes):
            lbp_encounters.append(enc_date)
            continue
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, lbp_codes):
                lbp_encounters.append(enc_date)
                break
        for reason in enc.get("reasonCode", []):
            if codeable_concept_has_any_code(reason, lbp_codes):
                lbp_encounters.append(enc_date)
                break

    # Also check Condition resources
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if onset and is_date_in_range(onset, intake_start, intake_end):
            if resource_has_any_code(cond, lbp_codes):
                lbp_encounters.append(onset)

    if not lbp_encounters:
        return None

    lbp_encounters.sort()

    # Test for negative diagnosis history (180 days prior)
    for candidate in lbp_encounters:
        lookback_start = candidate - timedelta(days=180)
        lookback_end = candidate - timedelta(days=1)
        prior = find_conditions_with_codes(
            bundle, lbp_codes, lookback_start, lookback_end
        )
        prior_enc = find_encounters_with_codes(
            bundle, lbp_codes, lookback_start, lookback_end
        )
        if not prior and not prior_enc:
            return candidate

    return None


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check eligible population: age 18-75, has IESD."""
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 18 or age > 75:
        return False, evaluated

    iesd = _find_iesd(bundle, measurement_year)
    if not iesd:
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions for LBP."""
    all_evaluated: list[str] = []

    # Common exclusions (hospice, death, palliative care, frailty)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=True
    )
    all_evaluated.extend(refs)
    if excluded:
        return True, all_evaluated

    iesd = _find_iesd(bundle, measurement_year)
    if not iesd:
        return False, all_evaluated

    iesd_plus_28 = iesd + timedelta(days=28)
    history_start = date(1900, 1, 1)

    # Cancer, HIV, transplant, osteoporosis, spondylopathy - any time through IESD+28
    dx_history_codes = all_codes(
        VALUE_SETS, "Diagnosis History That May Warrant Imaging"
    )
    if dx_history_codes:
        matches = find_conditions_with_codes(
            bundle, dx_history_codes, history_start, iesd_plus_28
        )
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    # Procedure history - any time through IESD+28
    proc_history_codes = all_codes(
        VALUE_SETS, "Procedure History That May Warrant Imaging"
    )
    if proc_history_codes:
        matches = find_procedures_with_codes(
            bundle, proc_history_codes, history_start, iesd_plus_28
        )
        if matches:
            all_evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in matches)
            return True, all_evaluated

    # Recent diagnoses (365 days prior to IESD through IESD+28)
    recent_dx_codes = all_codes(VALUE_SETS, "Recent Diagnoses That May Warrant Imaging")
    if recent_dx_codes:
        lookback = iesd - timedelta(days=365)
        matches = find_conditions_with_codes(
            bundle, recent_dx_codes, lookback, iesd_plus_28
        )
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    # Recent injuries (90 days prior to IESD through IESD+28)
    injury_codes = all_codes(VALUE_SETS, "Recent Injuries That May Warrant Imaging")
    if injury_codes:
        lookback = iesd - timedelta(days=90)
        matches = find_conditions_with_codes(
            bundle, injury_codes, lookback, iesd_plus_28
        )
        if matches:
            all_evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, all_evaluated

    return False, all_evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: imaging study on IESD or within 28 days after.

    INVERSE measure - numerator hit = bad outcome (unnecessary imaging).
    """
    evaluated: list[str] = []

    iesd = _find_iesd(bundle, measurement_year)
    if not iesd:
        return False, evaluated

    imaging_codes = all_codes(VALUE_SETS, "Imaging Study")
    if not imaging_codes:
        return False, evaluated

    window_end = iesd + timedelta(days=28)

    # Check procedures
    proc_matches = find_procedures_with_codes(bundle, imaging_codes, iesd, window_end)
    if proc_matches:
        evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
        return True, evaluated

    # Check observations (diagnostic imaging results)
    obs_matches = find_observations_with_codes(bundle, imaging_codes, iesd, window_end)
    if obs_matches:
        evaluated.extend(f"Observation/{o.get('id')}" for o, _ in obs_matches)
        return True, evaluated

    return False, evaluated


def calculate_lbp_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate LBP measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="LBP",
        measure_name="Use of Imaging Studies for Low Back Pain",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
