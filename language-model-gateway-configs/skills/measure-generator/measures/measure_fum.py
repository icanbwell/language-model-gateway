"""
HEDIS MY 2025 - Follow-Up After Emergency Department Visit for Mental Illness (FUM)

The percentage of ED visits for members 6 years of age and older with a principal
diagnosis of mental illness, or any diagnosis of intentional self-harm, and had
a mental health follow-up service.

Two rates are reported:
  1. Follow-up within 30 days of the ED visit (31 total days).
  2. Follow-up within 7 days of the ED visit (8 total days).
"""

from datetime import date, timedelta
from typing import Any

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_procedure_date,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("FUM")

# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def _find_qualifying_ed_visits(
    bundle: dict, measurement_year: int
) -> list[dict[str, Any]]:
    """
    Find ED visits with a principal diagnosis of mental illness or any diagnosis
    of intentional self-harm, between Jan 1 and Dec 1 of MY.
    """
    my_start = date(measurement_year, 1, 1)
    my_dec1 = date(measurement_year, 12, 1)

    ed_codes = all_codes(VALUE_SETS, "ED")
    mental_illness_codes = all_codes(VALUE_SETS, "Mental Illness")
    self_harm_codes = all_codes(VALUE_SETS, "Intentional Self Harm")
    inpatient_except_psych = all_codes(
        VALUE_SETS, "Inpatient Stay Except Psychiatric Residential"
    )

    visits: list[dict[str, Any]] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        if not resource_has_any_code(enc, ed_codes):
            is_ed = False
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, ed_codes):
                    is_ed = True
                    break
            if not is_ed:
                continue

        visit_date = get_encounter_date(enc)
        if not visit_date or not is_date_in_range(visit_date, my_start, my_dec1):
            continue

        # Check diagnosis
        has_qualifying_dx = False
        diagnoses = enc.get("diagnosis", [])
        for dx in diagnoses:
            condition_cc = dx.get("condition", {}).get("concept", {})
            if not condition_cc:
                continue
            rank = dx.get("rank", 999)
            if rank == 1 and codeable_concept_has_any_code(
                condition_cc, mental_illness_codes
            ):
                has_qualifying_dx = True
                break
            if codeable_concept_has_any_code(condition_cc, self_harm_codes):
                has_qualifying_dx = True
                break

        if not has_qualifying_dx:
            for cond in get_resources_by_type(bundle, "Condition"):
                cond_enc = cond.get("encounter", {}).get("reference", "")
                if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                    if resource_has_any_code(cond, mental_illness_codes):
                        has_qualifying_dx = True
                        break
                    if resource_has_any_code(cond, self_harm_codes):
                        has_qualifying_dx = True
                        break

        if not has_qualifying_dx:
            continue

        # Exclude ED visits followed by inpatient admission within 30 days
        excluded_by_admission = False
        for other_enc in get_resources_by_type(bundle, "Encounter"):
            if other_enc.get("id") == enc.get("id"):
                continue
            if not resource_has_any_code(other_enc, inpatient_except_psych):
                has_ip = False
                for t in other_enc.get("type", []):
                    if codeable_concept_has_any_code(t, inpatient_except_psych):
                        has_ip = True
                        break
                if not has_ip:
                    continue
            admit_date = get_encounter_date(other_enc)
            if admit_date and is_date_in_range(
                admit_date, visit_date, visit_date + timedelta(days=30)
            ):
                excluded_by_admission = True
                break

        if excluded_by_admission:
            continue

        visits.append(
            {
                "encounter": enc,
                "visit_date": visit_date,
                "enc_ref": f"Encounter/{enc.get('id', 'unknown')}",
            }
        )

    return visits


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient has a qualifying ED visit and is >= 6 years old."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    visits = _find_qualifying_ed_visits(bundle, measurement_year)
    qualifying = []
    for v in visits:
        age = calculate_age(birth_date, v["visit_date"])
        if age >= 6:
            qualifying.append(v)
            evaluated.append(v["enc_ref"])

    return len(qualifying) > 0, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check hospice and death exclusions."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def _has_mh_followup(
    bundle: dict, visit_date: date, end_date: date
) -> tuple[bool, list[str]]:
    """
    Check for a mental health follow-up service between visit_date (inclusive)
    and end_date (inclusive). For FUM, services on the date of ED visit ARE included.
    """
    evaluated: list[str] = []

    bh_outpatient = all_codes(VALUE_SETS, "BH Outpatient")
    mh_diagnosis = all_codes(VALUE_SETS, "Mental Health Diagnosis")
    partial_hosp = all_codes(
        VALUE_SETS, "Partial Hospitalization or Intensive Outpatient"
    )
    telephone_visits = all_codes(VALUE_SETS, "Telephone Visits")
    online_assess = all_codes(VALUE_SETS, "Online Assessments")
    bh_setting = all_codes(VALUE_SETS, "Behavioral Healthcare Setting")
    ect = all_codes(VALUE_SETS, "Electroconvulsive Therapy")
    psych_collab = all_codes(VALUE_SETS, "Psychiatric Collaborative Care Management")
    peer_support = all_codes(VALUE_SETS, "Peer Support Services")
    residential_bh = all_codes(VALUE_SETS, "Residential Behavioral Health Treatment")
    visit_unspecified = all_codes(VALUE_SETS, "Visit Setting Unspecified")

    followup_vs_list = [
        bh_outpatient,
        partial_hosp,
        telephone_visits,
        online_assess,
        bh_setting,
        psych_collab,
        peer_support,
        residential_bh,
        visit_unspecified,
    ]

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, visit_date, end_date):
            continue

        enc_ref = f"Encounter/{enc.get('id', 'unknown')}"
        for vs in followup_vs_list:
            if resource_has_any_code(enc, vs) or any(
                codeable_concept_has_any_code(t, vs) for t in enc.get("type", [])
            ):
                evaluated.append(enc_ref)
                return True, evaluated

    # Check procedures (ECT, etc.)
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, visit_date, end_date):
            continue
        if resource_has_any_code(proc, ect) or resource_has_any_code(
            proc, psych_collab
        ):
            evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
            return True, evaluated

    return False, evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check 30-day follow-up (default single-rate)."""
    visits = _find_qualifying_ed_visits(bundle, measurement_year)
    if not visits:
        return False, []
    v = visits[0]
    return _has_mh_followup(
        bundle, v["visit_date"], v["visit_date"] + timedelta(days=30)
    )


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_fum_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the FUM measure with 7-day and 30-day follow-up rates."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="FUM",
            measure_name="Follow-Up After ED Visit for Mental Illness",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "FUM-30day",
                    "display": "30-Day Follow-Up",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "FUM-7day",
                    "display": "7-Day Follow-Up",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=all_evaluated,
        )

    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(exclusion_refs)

    visits = _find_qualifying_ed_visits(bundle, measurement_year)
    v = visits[0] if visits else None

    numerator_30 = False
    refs_30: list[str] = []
    numerator_7 = False
    refs_7: list[str] = []

    if v:
        numerator_30, refs_30 = _has_mh_followup(
            bundle, v["visit_date"], v["visit_date"] + timedelta(days=30)
        )
        numerator_7, refs_7 = _has_mh_followup(
            bundle, v["visit_date"], v["visit_date"] + timedelta(days=7)
        )

    all_evaluated.extend(refs_30)
    all_evaluated.extend(refs_7)

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="FUM",
        measure_name="Follow-Up After ED Visit for Mental Illness",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "FUM-30day",
                "display": "30-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_30,
            },
            {
                "code": "FUM-7day",
                "display": "7-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_7,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
