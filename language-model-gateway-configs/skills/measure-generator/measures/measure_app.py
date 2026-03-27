"""
HEDIS MY 2025 - Use of First-Line Psychosocial Care for Children and Adolescents
on Antipsychotics (APP)

The percentage of children and adolescents 1-17 years of age who had a new
prescription for an antipsychotic medication and had documentation of psychosocial
care as first-line treatment.
"""

from datetime import date, timedelta
from typing import Any

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
    get_procedure_date,
    get_medication_date,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("APP")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_antipsychotic_dispenses(
    bundle: dict, start: date, end: date
) -> list[dict[str, Any]]:
    """Find all antipsychotic medication dispensing events in date range."""
    events: list[dict[str, Any]] = []

    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date or not is_date_in_range(med_date, start, end):
                continue
            # Any antipsychotic medication - check if resource exists
            events.append(
                {
                    "date": med_date,
                    "ref": f"{rtype}/{med.get('id', 'unknown')}",
                }
            )

    return sorted(events, key=lambda e: e["date"])


def _find_ipsd(bundle: dict, measurement_year: int) -> tuple[date | None, list[str]]:
    """
    Find IPSD: earliest antipsychotic prescription in intake period
    (Jan 1 - Dec 1 of MY) with 120-day negative medication history.
    """
    evaluated: list[str] = []
    intake_start = date(measurement_year, 1, 1)
    intake_end = date(measurement_year, 12, 1)

    # Find all antipsychotic dispenses in intake period
    dispenses = _find_antipsychotic_dispenses(bundle, intake_start, intake_end)

    for disp in dispenses:
        # Test for negative medication history: 120 days prior with no antipsychotics
        lookback_start = disp["date"] - timedelta(days=120)
        lookback_end = disp["date"] - timedelta(days=1)
        prior = _find_antipsychotic_dispenses(bundle, lookback_start, lookback_end)
        if not prior:
            evaluated.append(disp["ref"])
            return disp["date"], evaluated

    return None, evaluated


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Children 1-17 with a new antipsychotic prescription (IPSD with 120-day
    negative medication history).
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 1 or age > 17:
        return False, evaluated

    ipsd, ipsd_refs = _find_ipsd(bundle, measurement_year)
    evaluated.extend(ipsd_refs)
    if not ipsd:
        return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Exclude members with schizophrenia, bipolar, other psychotic/developmental
    disorders on >= 2 different dates during MY. Also hospice and death.
    """
    evaluated: list[str] = []

    # Common exclusions (hospice, death)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)

    # Clinically appropriate exclusion: schizophrenia, bipolar, other psychotic/dev disorders
    schiz_codes = all_codes(VALUE_SETS, "Schizophrenia")
    bipolar_codes = all_codes(VALUE_SETS, "Bipolar Disorder")
    other_psych = all_codes(VALUE_SETS, "Other Psychotic and Developmental Disorders")

    # Combine all exclusion diagnosis codes
    excl_dx_codes: dict[str, set[str]] = {}
    for vs in [schiz_codes, bipolar_codes, other_psych]:
        for sys, codes in vs.items():
            excl_dx_codes.setdefault(sys, set()).update(codes)

    if not excl_dx_codes:
        return False, evaluated

    # Need >= 2 different dates of service with these diagnoses
    dx_dates: set[date] = set()

    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if onset and is_date_in_range(onset, my_start, my_end):
            if resource_has_any_code(cond, excl_dx_codes):
                dx_dates.add(onset)

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue
        for dx in enc.get("diagnosis", []):
            cc = dx.get("condition", {}).get("concept", {})
            if cc and codeable_concept_has_any_code(cc, excl_dx_codes):
                dx_dates.add(enc_date)
                break

    if len(dx_dates) >= 2:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Psychosocial care or residential behavioral health treatment in the 121-day
    period from 90 days prior to IPSD through 30 days after IPSD.
    """
    evaluated: list[str] = []

    ipsd, _ = _find_ipsd(bundle, measurement_year)
    if not ipsd:
        return False, evaluated

    window_start = ipsd - timedelta(days=90)
    window_end = ipsd + timedelta(days=30)

    psychosocial_codes = all_codes(VALUE_SETS, "Psychosocial Care")
    residential_bh = all_codes(VALUE_SETS, "Residential Behavioral Health Treatment")

    # Check encounters
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, window_start, window_end):
            continue

        enc_ref = f"Encounter/{enc.get('id', 'unknown')}"
        for vs in [psychosocial_codes, residential_bh]:
            if resource_has_any_code(enc, vs) or any(
                codeable_concept_has_any_code(t, vs) for t in enc.get("type", [])
            ):
                evaluated.append(enc_ref)
                return True, evaluated

    # Check procedures
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, window_start, window_end):
            continue
        for vs in [psychosocial_codes, residential_bh]:
            if resource_has_any_code(proc, vs):
                evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_app_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the APP measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="APP",
        measure_name="Use of First-Line Psychosocial Care for Children and Adolescents on Antipsychotics",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
