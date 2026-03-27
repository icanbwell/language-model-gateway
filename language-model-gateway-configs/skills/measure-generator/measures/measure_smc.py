"""
HEDIS MY 2025 - Cardiovascular Monitoring for People With Cardiovascular Disease
and Schizophrenia (SMC)

The percentage of members 18-64 years of age with schizophrenia or schizoaffective
disorder and cardiovascular disease, who had an LDL-C test during the measurement
year.
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
    get_encounter_end_date,
    get_encounter_class,
    get_condition_onset,
    get_procedure_date,
    get_observation_date,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("SMC")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_schizophrenia(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Identify members with schizophrenia or schizoaffective disorder during MY.
    Same logic as SMD: one acute inpatient with dx OR two visits on different dates.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    schiz_codes = all_codes(VALUE_SETS, "Schizophrenia")
    bh_acute_ip = all_codes(VALUE_SETS, "BH Stand Alone Acute Inpatient")
    visit_unspecified = all_codes(VALUE_SETS, "Visit Setting Unspecified")
    bh_outpatient = all_codes(VALUE_SETS, "BH Outpatient")
    partial_hosp = all_codes(
        VALUE_SETS, "Partial Hospitalization or Intensive Outpatient"
    )
    ed_codes = all_codes(VALUE_SETS, "ED")
    telephone_visits = all_codes(VALUE_SETS, "Telephone Visits")
    online_assess = all_codes(VALUE_SETS, "Online Assessments")
    ect = all_codes(VALUE_SETS, "Electroconvulsive Therapy")
    bh_nonacute = all_codes(VALUE_SETS, "BH Stand Alone Nonacute Inpatient")

    # Check acute inpatient with schizophrenia
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
            has_schiz = _encounter_has_diagnosis(bundle, enc, schiz_codes)
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

        if _encounter_has_diagnosis(bundle, enc, schiz_codes):
            visit_dates.append((enc_date, f"Encounter/{enc.get('id', 'unknown')}"))

    unique_dates = {d for d, _ in visit_dates}
    if len(unique_dates) >= 2:
        for _, ref in visit_dates[:2]:
            evaluated.append(ref)
        return True, evaluated

    return False, evaluated


def _encounter_has_diagnosis(
    bundle: dict, enc: dict, dx_codes: dict[str, set[str]]
) -> bool:
    """Check if an encounter has a diagnosis matching the given codes."""
    for dx in enc.get("diagnosis", []):
        cc = dx.get("condition", {}).get("concept", {})
        if cc and codeable_concept_has_any_code(cc, dx_codes):
            return True
    for cond in get_resources_by_type(bundle, "Condition"):
        cond_enc = cond.get("encounter", {}).get("reference", "")
        if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
            if resource_has_any_code(cond, dx_codes):
                return True
    return False


def _has_cardiovascular_disease(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Identify CVD via event (AMI, CABG, PCI in prior year) or
    diagnosis (IVD in both MY and prior year).
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    ami_codes = all_codes(VALUE_SETS, "AMI")
    cabg_codes = all_codes(VALUE_SETS, "CABG")
    pci_codes = all_codes(VALUE_SETS, "PCI")
    ivd_codes = all_codes(VALUE_SETS, "IVD")
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")
    outpatient_codes = all_codes(VALUE_SETS, "Outpatient")
    acute_ip = all_codes(VALUE_SETS, "Acute Inpatient")

    # Event-based: AMI discharge in prior year
    for enc in get_resources_by_type(bundle, "Encounter"):
        discharge_date = get_encounter_end_date(enc)
        if not discharge_date or not is_date_in_range(discharge_date, py_start, py_end):
            continue
        # Check if inpatient
        is_ip = resource_has_any_code(enc, inpatient_codes) or any(
            codeable_concept_has_any_code(t, inpatient_codes)
            for t in enc.get("type", [])
        )
        if not is_ip:
            continue
        if _encounter_has_diagnosis(bundle, enc, ami_codes):
            evaluated.append(f"Encounter/{enc.get('id', 'unknown')}")
            return True, evaluated

    # CABG or PCI in prior year
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, py_start, py_end):
            continue
        if resource_has_any_code(proc, cabg_codes) or resource_has_any_code(
            proc, pci_codes
        ):
            evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
            return True, evaluated

    # Diagnosis-based: IVD in BOTH MY and prior year
    has_ivd_my = False
    has_ivd_py = False
    for cond in get_resources_by_type(bundle, "Condition"):
        onset = get_condition_onset(cond)
        if not onset:
            continue
        if resource_has_any_code(cond, ivd_codes):
            if is_date_in_range(onset, my_start, my_end):
                has_ivd_my = True
            if is_date_in_range(onset, py_start, py_end):
                has_ivd_py = True
            if has_ivd_my and has_ivd_py:
                evaluated.append(f"Condition/{cond.get('id', 'unknown')}")
                return True, evaluated

    # Also check encounter diagnoses
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date:
            continue
        for dx in enc.get("diagnosis", []):
            cc = dx.get("condition", {}).get("concept", {})
            if cc and codeable_concept_has_any_code(cc, ivd_codes):
                if is_date_in_range(enc_date, my_start, my_end):
                    has_ivd_my = True
                if is_date_in_range(enc_date, py_start, py_end):
                    has_ivd_py = True
                if has_ivd_my and has_ivd_py:
                    evaluated.append(f"Encounter/{enc.get('id', 'unknown')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Members 18-64 with schizophrenia AND cardiovascular disease."""
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

    has_cvd, cvd_refs = _has_cardiovascular_disease(bundle, measurement_year)
    evaluated.extend(cvd_refs)
    if not has_cvd:
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
    """An LDL-C test performed during the measurement year."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    ldl_lab = all_codes(VALUE_SETS, "LDL C Lab Test")
    ldl_result = all_codes(VALUE_SETS, "LDL C Test Result or Finding")

    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not obs_date or not is_date_in_range(obs_date, my_start, my_end):
            continue
        if resource_has_any_code(obs, ldl_lab) or resource_has_any_code(
            obs, ldl_result
        ):
            evaluated.append(f"Observation/{obs.get('id', 'unknown')}")
            return True, evaluated

    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, my_start, my_end):
            continue
        if resource_has_any_code(proc, ldl_lab) or resource_has_any_code(
            proc, ldl_result
        ):
            evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_smc_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the SMC measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="SMC",
        measure_name="Cardiovascular Monitoring for People With Cardiovascular Disease and Schizophrenia",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
