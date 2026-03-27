"""
HEDIS MY 2025 - Follow-Up After Emergency Department Visit for Substance Use (FUA)

The percentage of ED visits among members age 13 years and older with a principal
diagnosis of substance use disorder (SUD), or any diagnosis of drug overdose,
for which there was follow-up.

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
    get_medication_date,
    medication_has_code,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("FUA")

# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def _find_qualifying_ed_visits(
    bundle: dict, measurement_year: int
) -> list[dict[str, Any]]:
    """
    Find ED visits with a principal diagnosis of SUD or any diagnosis of
    drug overdose, between Jan 1 and Dec 1 of MY.
    """
    my_start = date(measurement_year, 1, 1)
    my_dec1 = date(measurement_year, 12, 1)

    ed_codes = all_codes(VALUE_SETS, "ED")
    aod_codes = all_codes(VALUE_SETS, "AOD Abuse and Dependence")
    overdose_codes = all_codes(VALUE_SETS, "Unintentional Drug Overdose")
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    residential_bh = all_codes(VALUE_SETS, "Residential Behavioral Health Treatment")

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

        # Check diagnosis: principal SUD or any drug overdose
        has_qualifying_dx = False
        for dx in enc.get("diagnosis", []):
            condition_cc = dx.get("condition", {}).get("concept", {})
            if not condition_cc:
                continue
            rank = dx.get("rank", 999)
            if rank == 1 and codeable_concept_has_any_code(condition_cc, aod_codes):
                has_qualifying_dx = True
                break
            if codeable_concept_has_any_code(condition_cc, overdose_codes):
                has_qualifying_dx = True
                break

        if not has_qualifying_dx:
            for cond in get_resources_by_type(bundle, "Condition"):
                cond_enc = cond.get("encounter", {}).get("reference", "")
                if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                    if resource_has_any_code(cond, aod_codes):
                        has_qualifying_dx = True
                        break
                    if resource_has_any_code(cond, overdose_codes):
                        has_qualifying_dx = True
                        break

        if not has_qualifying_dx:
            continue

        # Exclude ED visits followed by inpatient admission within 30 days
        excluded = False
        for other_enc in get_resources_by_type(bundle, "Encounter"):
            if other_enc.get("id") == enc.get("id"):
                continue
            is_ip = resource_has_any_code(other_enc, inpatient_codes) or any(
                codeable_concept_has_any_code(t, inpatient_codes)
                for t in other_enc.get("type", [])
            )
            if is_ip:
                admit = get_encounter_date(other_enc)
                if admit and is_date_in_range(
                    admit, visit_date, visit_date + timedelta(days=30)
                ):
                    excluded = True
                    break

        # Exclude ED visits followed by residential treatment within 30 days
        if not excluded:
            for other_enc in get_resources_by_type(bundle, "Encounter"):
                if other_enc.get("id") == enc.get("id"):
                    continue
                is_res = resource_has_any_code(other_enc, residential_bh) or any(
                    codeable_concept_has_any_code(t, residential_bh)
                    for t in other_enc.get("type", [])
                )
                if is_res:
                    res_date = get_encounter_date(other_enc)
                    if res_date and is_date_in_range(
                        res_date, visit_date, visit_date + timedelta(days=30)
                    ):
                        excluded = True
                        break

        if excluded:
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
    """Check if patient has a qualifying ED visit and is >= 13 years old."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    visits = _find_qualifying_ed_visits(bundle, measurement_year)
    qualifying = []
    for v in visits:
        age = calculate_age(birth_date, v["visit_date"])
        if age >= 13:
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


def _has_sud_followup(
    bundle: dict, visit_date: date, end_date: date
) -> tuple[bool, list[str]]:
    """
    Check for SUD follow-up or pharmacotherapy within the window.
    For FUA, services on the date of ED visit ARE included.
    """
    evaluated: list[str] = []

    aod_codes = all_codes(VALUE_SETS, "AOD Abuse and Dependence")
    substance_induced = all_codes(VALUE_SETS, "Substance Induced Disorders")
    overdose_codes = all_codes(VALUE_SETS, "Unintentional Drug Overdose")
    bh_outpatient = all_codes(VALUE_SETS, "BH Outpatient")
    visit_unspecified = all_codes(VALUE_SETS, "Visit Setting Unspecified")
    partial_hosp = all_codes(
        VALUE_SETS, "Partial Hospitalization or Intensive Outpatient"
    )
    telephone_visits = all_codes(VALUE_SETS, "Telephone Visits")
    online_assess = all_codes(VALUE_SETS, "Online Assessments")
    sud_services = all_codes(VALUE_SETS, "Substance Use Disorder Services")
    sud_counseling = all_codes(
        VALUE_SETS, "Substance Abuse Counseling and Surveillance"
    )
    bh_assessment = all_codes(VALUE_SETS, "Behavioral Health Assessment")
    substance_use_svc = all_codes(VALUE_SETS, "Substance Use Services")
    peer_support = all_codes(VALUE_SETS, "Peer Support Services")
    oud_weekly = all_codes(VALUE_SETS, "OUD Weekly Non Drug Service")
    oud_monthly = all_codes(VALUE_SETS, "OUD Monthly Office Based Treatment")
    aod_med_treatment = all_codes(VALUE_SETS, "AOD Medication Treatment")
    oud_drug_tx = all_codes(VALUE_SETS, "OUD Weekly Drug Treatment Service")

    followup_vs_list = [
        bh_outpatient,
        visit_unspecified,
        partial_hosp,
        telephone_visits,
        online_assess,
        sud_services,
        sud_counseling,
        bh_assessment,
        substance_use_svc,
        peer_support,
        oud_weekly,
        oud_monthly,
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

    # Check procedures
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, visit_date, end_date):
            continue
        for vs in [
            sud_services,
            sud_counseling,
            bh_assessment,
            substance_use_svc,
            aod_med_treatment,
            oud_drug_tx,
        ]:
            if resource_has_any_code(proc, vs):
                evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
                return True, evaluated

    # Check pharmacotherapy dispensing events
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date or not is_date_in_range(med_date, visit_date, end_date):
                continue
            if medication_has_code(med, aod_med_treatment) or medication_has_code(
                med, oud_drug_tx
            ):
                evaluated.append(f"{rtype}/{med.get('id', 'unknown')}")
                return True, evaluated

    return False, evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check 30-day follow-up."""
    visits = _find_qualifying_ed_visits(bundle, measurement_year)
    if not visits:
        return False, []
    v = visits[0]
    return _has_sud_followup(
        bundle, v["visit_date"], v["visit_date"] + timedelta(days=30)
    )


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_fua_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the FUA measure with 7-day and 30-day follow-up rates."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="FUA",
            measure_name="Follow-Up After ED Visit for Substance Use",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "FUA-30day",
                    "display": "30-Day Follow-Up",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "FUA-7day",
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
        numerator_30, refs_30 = _has_sud_followup(
            bundle, v["visit_date"], v["visit_date"] + timedelta(days=30)
        )
        numerator_7, refs_7 = _has_sud_followup(
            bundle, v["visit_date"], v["visit_date"] + timedelta(days=7)
        )

    all_evaluated.extend(refs_30)
    all_evaluated.extend(refs_7)

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="FUA",
        measure_name="Follow-Up After ED Visit for Substance Use",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "FUA-30day",
                "display": "30-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_30,
            },
            {
                "code": "FUA-7day",
                "display": "7-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_7,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
