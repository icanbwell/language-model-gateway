"""
HEDIS MY 2025 - Follow-Up After Hospitalization for Mental Illness (FUH)

The percentage of discharges for members 6 years of age and older who were
hospitalized for a principal diagnosis of mental illness, or any diagnosis of
intentional self-harm, and had a mental health follow-up service.

Two rates are reported:
  1. Follow-up within 30 days after discharge.
  2. Follow-up within 7 days after discharge.
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
    get_encounter_end_date,
    get_procedure_date,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("FUH")

# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def _find_qualifying_discharges(
    bundle: dict, measurement_year: int
) -> list[dict[str, Any]]:
    """
    Find acute inpatient discharges with a principal diagnosis of mental illness
    or any diagnosis of intentional self-harm, between Jan 1 and Dec 1 of MY.
    Returns list of dicts with discharge_date and encounter reference.
    """
    my_start = date(measurement_year, 1, 1)
    my_dec1 = date(measurement_year, 12, 1)

    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")
    mental_illness_codes = all_codes(VALUE_SETS, "Mental Illness")
    self_harm_codes = all_codes(VALUE_SETS, "Intentional Self Harm")

    discharges: list[dict[str, Any]] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        # Must be an inpatient stay
        if not resource_has_any_code(enc, inpatient_codes):
            is_inpatient = False
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, inpatient_codes):
                    is_inpatient = True
                    break
            if not is_inpatient:
                continue

        # Exclude nonacute stays
        if resource_has_any_code(enc, nonacute_codes):
            continue
        is_nonacute = False
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, nonacute_codes):
                is_nonacute = True
                break
        if is_nonacute:
            continue

        discharge_date = get_encounter_end_date(enc)
        if not discharge_date:
            continue
        if not is_date_in_range(discharge_date, my_start, my_dec1):
            continue

        # Check principal diagnosis of mental illness or any diagnosis of self-harm
        diagnoses = enc.get("diagnosis", [])
        has_qualifying_dx = False

        for dx in diagnoses:
            condition_cc = dx.get("condition", {}).get("concept", {})
            if not condition_cc:
                # Try reference-based diagnosis
                continue
            rank = dx.get("rank", 999)
            # Principal diagnosis = rank 1 for mental illness
            if rank == 1 and codeable_concept_has_any_code(
                condition_cc, mental_illness_codes
            ):
                has_qualifying_dx = True
                break
            # Any position for intentional self-harm
            if codeable_concept_has_any_code(condition_cc, self_harm_codes):
                has_qualifying_dx = True
                break

        # Also check conditions linked to encounter
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

        if has_qualifying_dx:
            discharges.append(
                {
                    "encounter": enc,
                    "discharge_date": discharge_date,
                    "enc_ref": f"Encounter/{enc.get('id', 'unknown')}",
                }
            )

    return discharges


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient has a qualifying discharge and is >= 6 years old."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    discharges = _find_qualifying_discharges(bundle, measurement_year)
    if not discharges:
        return False, evaluated

    # Check age >= 6 at discharge
    qualifying = []
    for d in discharges:
        age = calculate_age(birth_date, d["discharge_date"])
        if age >= 6:
            qualifying.append(d)
            evaluated.append(d["enc_ref"])

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


def _has_followup_visit(
    bundle: dict, after_date: date, end_date: date
) -> tuple[bool, list[str]]:
    """
    Check for a mental health follow-up service between after_date (exclusive)
    and end_date (inclusive). For FUH, do not include services on date of discharge.
    """
    evaluated: list[str] = []
    search_start = after_date + timedelta(days=1)

    # Value sets used for follow-up identification
    visit_unspecified = all_codes(VALUE_SETS, "Visit Setting Unspecified")
    outpatient_pos = all_codes(VALUE_SETS, "Outpatient POS")
    bh_outpatient = all_codes(VALUE_SETS, "BH Outpatient")
    mh_diagnosis = all_codes(VALUE_SETS, "Mental Health Diagnosis")
    partial_hosp = all_codes(
        VALUE_SETS, "Partial Hospitalization or Intensive Outpatient"
    )
    telehealth_pos = all_codes(VALUE_SETS, "Telehealth POS")
    telephone_visits = all_codes(VALUE_SETS, "Telephone Visits")
    tcm_services = all_codes(VALUE_SETS, "Transitional Care Management Services")
    bh_setting = all_codes(VALUE_SETS, "Behavioral Healthcare Setting")
    ect = all_codes(VALUE_SETS, "Electroconvulsive Therapy")
    psych_collab = all_codes(VALUE_SETS, "Psychiatric Collaborative Care Management")
    peer_support = all_codes(VALUE_SETS, "Peer Support Services")
    residential_bh = all_codes(VALUE_SETS, "Residential Behavioral Health Treatment")

    # Check encounters
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, search_start, end_date):
            continue

        enc_ref = f"Encounter/{enc.get('id', 'unknown')}"

        # Check various follow-up criteria
        # BH Outpatient with MH diagnosis
        if resource_has_any_code(enc, bh_outpatient) or any(
            codeable_concept_has_any_code(t, bh_outpatient) for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Behavioral Healthcare Setting
        if resource_has_any_code(enc, bh_setting) or any(
            codeable_concept_has_any_code(t, bh_setting) for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Partial hospitalization or intensive outpatient
        if resource_has_any_code(enc, partial_hosp) or any(
            codeable_concept_has_any_code(t, partial_hosp) for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Telephone visits with MH diagnosis
        if resource_has_any_code(enc, telephone_visits) or any(
            codeable_concept_has_any_code(t, telephone_visits)
            for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Transitional care management
        if resource_has_any_code(enc, tcm_services) or any(
            codeable_concept_has_any_code(t, tcm_services) for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Psychiatric collaborative care management
        if resource_has_any_code(enc, psych_collab) or any(
            codeable_concept_has_any_code(t, psych_collab) for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Peer support with MH diagnosis
        if resource_has_any_code(enc, peer_support) or any(
            codeable_concept_has_any_code(t, peer_support) for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Residential behavioral health treatment
        if resource_has_any_code(enc, residential_bh) or any(
            codeable_concept_has_any_code(t, residential_bh)
            for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

        # Visit Setting Unspecified (outpatient context)
        if resource_has_any_code(enc, visit_unspecified) or any(
            codeable_concept_has_any_code(t, visit_unspecified)
            for t in enc.get("type", [])
        ):
            evaluated.append(enc_ref)
            return True, evaluated

    # Check procedures (e.g., ECT)
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, search_start, end_date):
            continue
        if resource_has_any_code(proc, ect):
            evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
            return True, evaluated
        if resource_has_any_code(proc, psych_collab):
            evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
            return True, evaluated

    return False, evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check for 30-day follow-up (used for single-rate; multi-rate handled below)."""
    discharges = _find_qualifying_discharges(bundle, measurement_year)
    if not discharges:
        return False, []

    discharge = discharges[0]
    end_30 = discharge["discharge_date"] + timedelta(days=30)
    return _has_followup_visit(bundle, discharge["discharge_date"], end_30)


def _check_numerator_7day(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check for 7-day follow-up."""
    discharges = _find_qualifying_discharges(bundle, measurement_year)
    if not discharges:
        return False, []

    discharge = discharges[0]
    end_7 = discharge["discharge_date"] + timedelta(days=7)
    return _has_followup_visit(bundle, discharge["discharge_date"], end_7)


def _check_numerator_30day(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check for 30-day follow-up."""
    discharges = _find_qualifying_discharges(bundle, measurement_year)
    if not discharges:
        return False, []

    discharge = discharges[0]
    end_30 = discharge["discharge_date"] + timedelta(days=30)
    return _has_followup_visit(bundle, discharge["discharge_date"], end_30)


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_fuh_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the FUH measure with 7-day and 30-day follow-up rates."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="FUH",
            measure_name="Follow-Up After Hospitalization for Mental Illness",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "FUH-30day",
                    "display": "30-Day Follow-Up",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "FUH-7day",
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

    numerator_30, refs_30 = _check_numerator_30day(bundle, measurement_year)
    all_evaluated.extend(refs_30)

    numerator_7, refs_7 = _check_numerator_7day(bundle, measurement_year)
    all_evaluated.extend(refs_7)

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="FUH",
        measure_name="Follow-Up After Hospitalization for Mental Illness",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "FUH-30day",
                "display": "30-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_30,
            },
            {
                "code": "FUH-7day",
                "display": "7-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_7,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
