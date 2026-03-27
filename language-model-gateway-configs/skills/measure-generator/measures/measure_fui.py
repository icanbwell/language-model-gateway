"""
HEDIS MY 2025 - Follow-Up After High-Intensity Care for Substance Use Disorder (FUI)

The percentage of acute inpatient hospitalizations, residential treatment or
withdrawal management visits for a diagnosis of substance use disorder among
members 13 years of age and older that result in a follow-up visit or service
for substance use disorder.

Two rates are reported:
  1. Follow-up within 30 days after the visit or discharge.
  2. Follow-up within 7 days after the visit or discharge.
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
    get_medication_date,
    medication_has_code,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("FUI")

# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def _find_qualifying_episodes(
    bundle: dict, measurement_year: int
) -> list[dict[str, Any]]:
    """
    Find acute inpatient discharges, residential treatment stays, or
    withdrawal management visits with principal diagnosis of SUD,
    between Jan 1 and Dec 1 of MY.
    """
    my_start = date(measurement_year, 1, 1)
    my_dec1 = date(measurement_year, 12, 1)

    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_other = all_codes(
        VALUE_SETS,
        "Nonacute Inpatient Stay Other Than Behavioral Health Accommodations",
    )
    aod_codes = all_codes(VALUE_SETS, "AOD Abuse and Dependence")
    detox_codes = all_codes(VALUE_SETS, "Detoxification")

    episodes: list[dict[str, Any]] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        is_inpatient = resource_has_any_code(enc, inpatient_codes) or any(
            codeable_concept_has_any_code(t, inpatient_codes)
            for t in enc.get("type", [])
        )

        is_detox = resource_has_any_code(enc, detox_codes) or any(
            codeable_concept_has_any_code(t, detox_codes) for t in enc.get("type", [])
        )

        if not is_inpatient and not is_detox:
            continue

        # For inpatient, exclude nonacute other than BH
        if is_inpatient:
            if resource_has_any_code(enc, nonacute_other) or any(
                codeable_concept_has_any_code(t, nonacute_other)
                for t in enc.get("type", [])
            ):
                continue

        # Determine episode date
        if is_inpatient:
            episode_date = get_encounter_end_date(enc)  # discharge date
        else:
            episode_date = get_encounter_date(enc)  # date of service for detox

        if not episode_date or not is_date_in_range(episode_date, my_start, my_dec1):
            continue

        # Check principal diagnosis of SUD
        has_sud_dx = False
        for dx in enc.get("diagnosis", []):
            condition_cc = dx.get("condition", {}).get("concept", {})
            if not condition_cc:
                continue
            rank = dx.get("rank", 999)
            if rank == 1 and codeable_concept_has_any_code(condition_cc, aod_codes):
                has_sud_dx = True
                break

        if not has_sud_dx:
            for cond in get_resources_by_type(bundle, "Condition"):
                cond_enc = cond.get("encounter", {}).get("reference", "")
                if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                    if resource_has_any_code(cond, aod_codes):
                        has_sud_dx = True
                        break

        if has_sud_dx:
            episodes.append(
                {
                    "encounter": enc,
                    "episode_date": episode_date,
                    "enc_ref": f"Encounter/{enc.get('id', 'unknown')}",
                }
            )

    return episodes


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient has qualifying episodes and is >= 13 years old."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    episodes = _find_qualifying_episodes(bundle, measurement_year)
    qualifying = []
    for ep in episodes:
        age = calculate_age(birth_date, ep["episode_date"])
        if age >= 13:
            qualifying.append(ep)
            evaluated.append(ep["enc_ref"])

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
    bundle: dict, episode_date: date, end_date: date, exclude_episode_date: bool = True
) -> tuple[bool, list[str]]:
    """
    Check for SUD follow-up visit after episode date. For FUI, do not include
    visits on the date of the denominator episode.
    """
    evaluated: list[str] = []
    search_start = (
        episode_date + timedelta(days=1) if exclude_episode_date else episode_date
    )

    aod_codes = all_codes(VALUE_SETS, "AOD Abuse and Dependence")
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
    oud_weekly = all_codes(VALUE_SETS, "OUD Weekly Non Drug Service")
    oud_monthly = all_codes(VALUE_SETS, "OUD Monthly Office Based Treatment")
    residential_bh = all_codes(VALUE_SETS, "Residential Behavioral Health Treatment")
    aod_med_treatment = all_codes(VALUE_SETS, "AOD Medication Treatment")
    oud_drug_tx = all_codes(VALUE_SETS, "OUD Weekly Drug Treatment Service")
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")

    followup_vs_list = [
        bh_outpatient,
        visit_unspecified,
        partial_hosp,
        telephone_visits,
        online_assess,
        sud_services,
        sud_counseling,
        oud_weekly,
        oud_monthly,
        residential_bh,
        inpatient_codes,
    ]

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, search_start, end_date):
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
        if not proc_date or not is_date_in_range(proc_date, search_start, end_date):
            continue
        for vs in [sud_services, sud_counseling, aod_med_treatment, oud_drug_tx]:
            if resource_has_any_code(proc, vs):
                evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
                return True, evaluated

    # Check medication dispensing events (pharmacotherapy)
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date or not is_date_in_range(med_date, search_start, end_date):
                continue
            # Check OUD/AUD medication lists via medication codes
            if medication_has_code(med, aod_med_treatment) or medication_has_code(
                med, oud_drug_tx
            ):
                evaluated.append(f"{rtype}/{med.get('id', 'unknown')}")
                return True, evaluated

    return False, evaluated


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check 30-day follow-up."""
    episodes = _find_qualifying_episodes(bundle, measurement_year)
    if not episodes:
        return False, []
    ep = episodes[0]
    return _has_sud_followup(
        bundle, ep["episode_date"], ep["episode_date"] + timedelta(days=30)
    )


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_fui_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the FUI measure with 7-day and 30-day follow-up rates."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="FUI",
            measure_name="Follow-Up After High-Intensity Care for Substance Use Disorder",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "FUI-30day",
                    "display": "30-Day Follow-Up",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "FUI-7day",
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

    episodes = _find_qualifying_episodes(bundle, measurement_year)
    ep = episodes[0] if episodes else None

    numerator_30 = False
    refs_30: list[str] = []
    numerator_7 = False
    refs_7: list[str] = []

    if ep:
        numerator_30, refs_30 = _has_sud_followup(
            bundle, ep["episode_date"], ep["episode_date"] + timedelta(days=30)
        )
        numerator_7, refs_7 = _has_sud_followup(
            bundle, ep["episode_date"], ep["episode_date"] + timedelta(days=7)
        )

    all_evaluated.extend(refs_30)
    all_evaluated.extend(refs_7)

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="FUI",
        measure_name="Follow-Up After High-Intensity Care for Substance Use Disorder",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "FUI-30day",
                "display": "30-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_30,
            },
            {
                "code": "FUI-7day",
                "display": "7-Day Follow-Up",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": numerator_7,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
