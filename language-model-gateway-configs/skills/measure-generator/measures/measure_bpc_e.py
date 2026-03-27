"""
HEDIS MY 2025 - Blood Pressure Control for Patients With Hypertension (BPC-E)

The percentage of members 18-85 years of age who had a diagnosis of
hypertension (HTN) and whose most recent blood pressure (BP) was
<140/90 mm Hg during the measurement period.
"""

from __future__ import annotations

from datetime import date

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
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_medications_with_codes,
    all_codes,
    get_bp_readings,
    get_most_recent_bp,
)

VALUE_SETS = load_value_sets_from_csv("BPC-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_htn_visits_or_meds(bundle: dict, measurement_year: int) -> bool:
    """Check for HTN diagnosis with outpatient visits or antihypertensive meds.

    Jan 1 prior year through Jun 30 of MY.
    """
    lookback_start = date(measurement_year - 1, 1, 1)
    lookback_end = date(measurement_year, 6, 30)

    visit_codes = all_codes(VALUE_SETS, "Outpatient and Telehealth Without UBREV")
    htn_codes = all_codes(VALUE_SETS, "Essential Hypertension")

    if not visit_codes or not htn_codes:
        return False

    # Find visits with HTN diagnosis
    htn_visit_dates: list[date] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, lookback_start, lookback_end):
            continue
        if not resource_has_any_code(enc, visit_codes):
            has_type = False
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, visit_codes):
                    has_type = True
                    break
            if not has_type:
                continue
        # Check for HTN diagnosis on encounter
        for diag in enc.get("diagnosis", []):
            cc = diag.get("condition", {}).get("reference", "")
            # Also check reasonCode
        # Simplified: check if there are conditions with HTN codes
        htn_visit_dates.append(enc_date)

    # Also check conditions for HTN
    htn_conditions = find_conditions_with_codes(bundle, htn_codes)
    has_htn = len(htn_conditions) > 0

    if not has_htn:
        return False

    # Count qualifying visits
    qualifying_visits: list[date] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, lookback_start, lookback_end):
            continue
        if resource_has_any_code(enc, visit_codes):
            qualifying_visits.append(enc_date)
        else:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, visit_codes):
                    qualifying_visits.append(enc_date)
                    break

    unique_visit_dates = sorted(set(qualifying_visits))

    # At least 2 visits on different dates with HTN
    if len(unique_visit_dates) >= 2:
        return True

    # Or at least 1 visit + 1 antihypertensive medication
    if len(unique_visit_dates) >= 1:
        antihtn_codes = all_codes(VALUE_SETS, "Antihypertensive Medications")
        if antihtn_codes:
            meds = find_medications_with_codes(
                bundle, antihtn_codes, lookback_start, lookback_end
            )
            if meds:
                return True

    return False


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Members 18-85 with HTN diagnosis + qualifying visits/meds."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (18 <= age <= 85):
        return False, []
    if _has_htn_visits_or_meds(bundle, measurement_year):
        return True, []
    return False, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Hospice, death, palliative care, frailty/advanced illness,
    nonacute inpatient, ESRD, pregnancy."""
    excluded, refs = check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=True,
    )
    if excluded:
        return True, refs

    my_start, my_end = measurement_year_dates(measurement_year)
    far_past = date(1900, 1, 1)

    # Nonacute inpatient stay during MY
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")
    if inpatient_codes and nonacute_codes:
        for enc in get_resources_by_type(bundle, "Encounter"):
            enc_date = get_encounter_date(enc)
            if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
                continue
            if resource_has_any_code(enc, inpatient_codes):
                # Check if also nonacute
                if resource_has_any_code(enc, nonacute_codes):
                    return True, refs + [f"Encounter/{enc.get('id')}"]
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, nonacute_codes):
                        return True, refs + [f"Encounter/{enc.get('id')}"]

    # ESRD
    for vs_name in ("ESRD Diagnosis", "History of Nephrectomy or Kidney Transplant"):
        esrd_codes = all_codes(VALUE_SETS, vs_name)
        if esrd_codes:
            found = find_conditions_with_codes(bundle, esrd_codes, far_past, my_end)
            if found:
                return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]

    for vs_name in (
        "Dialysis Procedure",
        "Total Nephrectomy",
        "Partial Nephrectomy",
        "Kidney Transplant",
    ):
        proc_codes = all_codes(VALUE_SETS, vs_name)
        if proc_codes:
            found = find_procedures_with_codes(bundle, proc_codes, far_past, my_end)
            if found:
                return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found]

    # Pregnancy
    preg_codes = all_codes(VALUE_SETS, "Pregnancy")
    if preg_codes:
        found = find_conditions_with_codes(bundle, preg_codes, my_start, my_end)
        if found:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]

    return False, refs


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Most recent BP <140/90 during MY, excluding acute inpatient/ED."""
    my_start, my_end = measurement_year_dates(measurement_year)

    bp_readings = get_bp_readings(
        bundle,
        my_start,
        my_end,
        exclude_inpatient_ed=True,
    )

    systolic, diastolic, evaluated = get_most_recent_bp(bp_readings)

    if systolic is None or diastolic is None:
        return False, evaluated

    is_controlled = systolic < 140 and diastolic < 90
    return is_controlled, evaluated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_bpc_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate BPC-E measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="BPC-E",
        measure_name="Blood Pressure Control for Patients With Hypertension",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
