"""
HEDIS MY 2025 - Controlling High Blood Pressure (CBP).

The percentage of members 18-85 years of age who had a diagnosis of
hypertension (HTN) and whose blood pressure (BP) was adequately controlled
(<140/90 mm Hg) during the measurement year.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    get_bp_readings,
    get_most_recent_bp,
    all_codes,
    ICD10CM,
)

VALUE_SETS = load_value_sets_from_csv("CBP")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: 18-85 years as of Dec 31 of the measurement year, with at
    least two outpatient/telehealth visits on different dates of service
    with a diagnosis of hypertension between Jan 1 of the year prior to the
    measurement year and June 30 of the measurement year.

    Also removes members with nonacute inpatient admission during the
    measurement year.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 18 or age > 85:
        return False, evaluated

    # Step 1: At least 2 outpatient visits with HTN diagnosis
    outpatient_codes = all_codes(VALUE_SETS, "Outpatient and Telehealth Without UBREV")
    htn_codes = all_codes(VALUE_SETS, "Essential Hypertension")
    if not outpatient_codes or not htn_codes:
        return False, evaluated

    lookback_start = date(measurement_year - 1, 1, 1)
    lookback_end = date(measurement_year, 6, 30)

    outpatient_visits = find_encounters_with_codes(
        bundle, outpatient_codes, lookback_start, lookback_end
    )

    htn_visit_dates: list[tuple[date, dict]] = []
    for enc, enc_date in outpatient_visits:
        if not enc_date:
            continue
        has_htn = resource_has_any_code(enc, htn_codes)
        if not has_htn:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, htn_codes):
                    has_htn = True
                    break
        # Also check conditions with HTN codes around the encounter date
        if not has_htn:
            htn_conditions = find_conditions_with_codes(
                bundle, htn_codes, enc_date, enc_date
            )
            if htn_conditions:
                has_htn = True

        if has_htn:
            htn_visit_dates.append((enc_date, enc))

    # Need at least 2 visits on different dates
    unique_dates = {d for d, _ in htn_visit_dates}
    if len(unique_dates) < 2:
        return False, evaluated

    for _, enc in htn_visit_dates:
        evaluated.append(f"Encounter/{enc.get('id')}")

    # Step 2: Remove members with nonacute inpatient admission during MY
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")
    if inpatient_codes and nonacute_codes:
        inpatient_visits = find_encounters_with_codes(
            bundle, inpatient_codes, my_start, my_end
        )
        for enc, _ in inpatient_visits:
            if resource_has_any_code(enc, nonacute_codes):
                return False, evaluated
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, nonacute_codes):
                    return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions:
    - Hospice, death, palliative care
    - ESRD diagnosis or procedure (any time through end of MY)
    - Pregnancy during the measurement year
    - Frailty + advanced illness (ages 66-80) or frailty alone (81+)
    """
    evaluated: list[str] = []

    # Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=True
    )
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)

    # Palliative care ICD-10-CM Z51.5
    z515_codes = {ICD10CM: {"Z51.5"}}
    pall_hits = find_conditions_with_codes(bundle, z515_codes, my_start, my_end)
    if pall_hits:
        for cond, _ in pall_hits:
            evaluated.append(f"Condition/{cond.get('id')}")
        return True, evaluated

    # ESRD diagnosis (any time through end of MY)
    for vs_name in ("ESRD Diagnosis", "History of Nephrectomy or Kidney Transplant"):
        esrd_codes = all_codes(VALUE_SETS, vs_name)
        if esrd_codes:
            esrd_hits = find_conditions_with_codes(bundle, esrd_codes)
            for cond, onset in esrd_hits:
                if onset is None or onset <= my_end:
                    evaluated.append(f"Condition/{cond.get('id')}")
                    return True, evaluated

    # ESRD procedures (any time through end of MY)
    for vs_name in (
        "Dialysis Procedure",
        "Total Nephrectomy",
        "Partial Nephrectomy",
        "Kidney Transplant",
    ):
        esrd_proc_codes = all_codes(VALUE_SETS, vs_name)
        if esrd_proc_codes:
            # Search broad date range
            early_date = date(1900, 1, 1)
            proc_hits = find_procedures_with_codes(
                bundle, esrd_proc_codes, early_date, my_end
            )
            if proc_hits:
                for proc, _ in proc_hits:
                    evaluated.append(f"Procedure/{proc.get('id')}")
                return True, evaluated

    # Pregnancy during the measurement year
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy")
    if pregnancy_codes:
        preg_hits = find_conditions_with_codes(
            bundle, pregnancy_codes, my_start, my_end
        )
        if preg_hits:
            for cond, _ in preg_hits:
                evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Most recent BP reading during the measurement year must be < 140/90.

    Uses get_bp_readings and get_most_recent_bp from hedis_common.
    Excludes BP taken in acute inpatient or ED settings.
    The BP reading must occur on or after the second HTN diagnosis date.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    # Get BP readings (excludes inpatient/ED by default)
    bp_readings = get_bp_readings(bundle, my_start, my_end, exclude_inpatient_ed=True)

    if not bp_readings:
        return False, evaluated

    systolic, diastolic, bp_refs = get_most_recent_bp(bp_readings)
    evaluated.extend(bp_refs)

    if systolic is None or diastolic is None:
        return False, evaluated

    # Adequate control: systolic < 140 AND diastolic < 90
    if systolic < 140 and diastolic < 90:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_cbp_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the CBP measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="CBP",
        measure_name="Controlling High Blood Pressure",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
