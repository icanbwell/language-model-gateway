"""
HEDIS MY 2025 - Diabetes Monitoring for People With Diabetes and Schizophrenia (SMD)

The percentage of members 18-64 years of age with schizophrenia or schizoaffective
disorder and diabetes who had both an LDL-C test and an HbA1c test during the
measurement year.
"""

from datetime import date
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
    prior_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_class,
    get_condition_onset,
    get_procedure_date,
    get_observation_date,
    get_medication_date,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("SMD")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_schizophrenia(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Identify members with schizophrenia or schizoaffective disorder.
    Requires one acute inpatient encounter with dx OR two visits on different dates.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    schiz_codes = all_codes(VALUE_SETS, "Schizophrenia")
    bh_acute_ip = all_codes(VALUE_SETS, "BH Stand Alone Acute Inpatient")
    bh_outpatient = all_codes(VALUE_SETS, "BH Outpatient")
    visit_unspecified = all_codes(VALUE_SETS, "Visit Setting Unspecified")
    partial_hosp = all_codes(
        VALUE_SETS, "Partial Hospitalization or Intensive Outpatient"
    )
    ed_codes = all_codes(VALUE_SETS, "ED")
    telephone_visits = all_codes(VALUE_SETS, "Telephone Visits")
    online_assess = all_codes(VALUE_SETS, "Online Assessments")
    ect = all_codes(VALUE_SETS, "Electroconvulsive Therapy")
    bh_nonacute = all_codes(VALUE_SETS, "BH Stand Alone Nonacute Inpatient")

    # Check acute inpatient with schizophrenia diagnosis
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue

        is_acute_ip = resource_has_any_code(enc, bh_acute_ip) or any(
            codeable_concept_has_any_code(t, bh_acute_ip) for t in enc.get("type", [])
        )
        if not is_acute_ip:
            is_acute_ip = (
                resource_has_any_code(enc, visit_unspecified)
                or any(
                    codeable_concept_has_any_code(t, visit_unspecified)
                    for t in enc.get("type", [])
                )
            ) and get_encounter_class(enc) == "IMP"

        if is_acute_ip:
            has_schiz = False
            for dx in enc.get("diagnosis", []):
                cc = dx.get("condition", {}).get("concept", {})
                if cc and codeable_concept_has_any_code(cc, schiz_codes):
                    has_schiz = True
                    break
            if not has_schiz:
                for cond in get_resources_by_type(bundle, "Condition"):
                    cond_enc = cond.get("encounter", {}).get("reference", "")
                    if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                        if resource_has_any_code(cond, schiz_codes):
                            has_schiz = True
                            break
            if has_schiz:
                evaluated.append(f"Encounter/{enc.get('id', 'unknown')}")
                return True, evaluated

    # Two visits on different dates
    outpatient_vs_list = [
        bh_outpatient,
        visit_unspecified,
        partial_hosp,
        ed_codes,
        telephone_visits,
        online_assess,
        ect,
        bh_nonacute,
    ]

    visit_dates: list[tuple[date, str]] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue

        is_qualifying = False
        for vs in outpatient_vs_list:
            if resource_has_any_code(enc, vs) or any(
                codeable_concept_has_any_code(t, vs) for t in enc.get("type", [])
            ):
                is_qualifying = True
                break

        if not is_qualifying:
            continue

        has_schiz = False
        for dx in enc.get("diagnosis", []):
            cc = dx.get("condition", {}).get("concept", {})
            if cc and codeable_concept_has_any_code(cc, schiz_codes):
                has_schiz = True
                break
        if not has_schiz:
            for cond in get_resources_by_type(bundle, "Condition"):
                cond_enc = cond.get("encounter", {}).get("reference", "")
                if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                    if resource_has_any_code(cond, schiz_codes):
                        has_schiz = True
                        break

        if has_schiz:
            visit_dates.append((enc_date, f"Encounter/{enc.get('id', 'unknown')}"))

    unique_dates = {d for d, _ in visit_dates}
    if len(unique_dates) >= 2:
        for _, ref in visit_dates[:2]:
            evaluated.append(ref)
        return True, evaluated

    return False, evaluated


def _has_diabetes(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Identify members with diabetes via claims (2 dx on different dates)
    or pharmacy data (diabetes meds + 1 dx) during MY or prior year.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")

    # Claim/encounter data: 2 diagnoses on different dates
    dx_dates: list[date] = []
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if onset and (is_date_in_range(onset, py_start, my_end)):
            if resource_has_any_code(cond, diabetes_codes):
                dx_dates.append(onset)
                evaluated.append(f"Condition/{cond.get('id', 'unknown')}")

    if len(set(dx_dates)) >= 2:
        return True, evaluated

    # Also check encounter diagnoses
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not (is_date_in_range(enc_date, py_start, my_end)):
            continue
        for dx in enc.get("diagnosis", []):
            cc = dx.get("condition", {}).get("concept", {})
            if cc and codeable_concept_has_any_code(cc, diabetes_codes):
                dx_dates.append(enc_date)
                evaluated.append(f"Encounter/{enc.get('id', 'unknown')}")
                break

    if len(set(dx_dates)) >= 2:
        return True, evaluated

    # Pharmacy data: diabetes meds + 1 dx
    if len(set(dx_dates)) >= 1:
        for rtype in ("MedicationDispense", "MedicationRequest"):
            for med in get_resources_by_type(bundle, rtype):
                med_date = get_medication_date(med)
                if med_date and is_date_in_range(med_date, py_start, my_end):
                    evaluated.append(f"{rtype}/{med.get('id', 'unknown')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Members 18-64 with schizophrenia AND diabetes."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 18 or age > 64:
        return False, evaluated

    has_schiz, schiz_refs = _has_schizophrenia(bundle, measurement_year)
    evaluated.extend(schiz_refs)
    if not has_schiz:
        return False, evaluated

    has_dm, dm_refs = _has_diabetes(bundle, measurement_year)
    evaluated.extend(dm_refs)
    if not has_dm:
        return False, evaluated

    return True, evaluated


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


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Both an HbA1c test AND an LDL-C test performed during the measurement year.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    hba1c_lab = all_codes(VALUE_SETS, "HbA1c Lab Test")
    hba1c_result = all_codes(VALUE_SETS, "HbA1c Test Result or Finding")
    ldl_lab = all_codes(VALUE_SETS, "LDL C Lab Test")
    ldl_result = all_codes(VALUE_SETS, "LDL C Test Result or Finding")

    has_hba1c = False
    has_ldl = False

    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not obs_date or not is_date_in_range(obs_date, my_start, my_end):
            continue

        obs_ref = f"Observation/{obs.get('id', 'unknown')}"
        if not has_hba1c:
            if resource_has_any_code(obs, hba1c_lab) or resource_has_any_code(
                obs, hba1c_result
            ):
                has_hba1c = True
                evaluated.append(obs_ref)

        if not has_ldl:
            if resource_has_any_code(obs, ldl_lab) or resource_has_any_code(
                obs, ldl_result
            ):
                has_ldl = True
                evaluated.append(obs_ref)

    # Also check procedures
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, my_start, my_end):
            continue

        proc_ref = f"Procedure/{proc.get('id', 'unknown')}"
        if not has_hba1c:
            if resource_has_any_code(proc, hba1c_lab) or resource_has_any_code(
                proc, hba1c_result
            ):
                has_hba1c = True
                evaluated.append(proc_ref)

        if not has_ldl:
            if resource_has_any_code(proc, ldl_lab) or resource_has_any_code(
                proc, ldl_result
            ):
                has_ldl = True
                evaluated.append(proc_ref)

    return has_hba1c and has_ldl, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_smd_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the SMD measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="SMD",
        measure_name="Diabetes Monitoring for People With Diabetes and Schizophrenia",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
