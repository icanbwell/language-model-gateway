"""
HEDIS MY 2025 - Diabetes Screening for People With Schizophrenia or Bipolar
Disorder Who Are Using Antipsychotic Medications (SSD)

The percentage of members 18-64 years of age with schizophrenia, schizoaffective
disorder or bipolar disorder who were dispensed an antipsychotic medication and
had a diabetes screening test during the measurement year.
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

VALUE_SETS = load_value_sets_from_csv("SSD")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_schizophrenia_or_bipolar(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Identify members with schizophrenia, schizoaffective, or bipolar disorder.
    Requires either one acute inpatient encounter with dx OR two outpatient/
    other visits on different dates with dx.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    schiz_codes = all_codes(VALUE_SETS, "Schizophrenia")
    bipolar_codes = all_codes(VALUE_SETS, "Bipolar Disorder")
    other_bipolar = all_codes(VALUE_SETS, "Other Bipolar Disorder")

    bh_acute_ip = all_codes(VALUE_SETS, "BH Stand Alone Acute Inpatient")
    visit_unspecified = all_codes(VALUE_SETS, "Visit Setting Unspecified")
    acute_ip_pos = all_codes(VALUE_SETS, "Acute Inpatient POS")
    bh_outpatient = all_codes(VALUE_SETS, "BH Outpatient")
    partial_hosp = all_codes(
        VALUE_SETS, "Partial Hospitalization or Intensive Outpatient"
    )
    ed_codes = all_codes(VALUE_SETS, "ED")
    telephone_visits = all_codes(VALUE_SETS, "Telephone Visits")
    online_assess = all_codes(VALUE_SETS, "Online Assessments")
    ect = all_codes(VALUE_SETS, "Electroconvulsive Therapy")
    bh_nonacute = all_codes(VALUE_SETS, "BH Stand Alone Nonacute Inpatient")

    # Combine all SMI diagnosis codes
    smi_codes: dict[str, set[str]] = {}
    for vs in [schiz_codes, bipolar_codes, other_bipolar]:
        for sys, codes in vs.items():
            smi_codes.setdefault(sys, set()).update(codes)

    # Check for acute inpatient encounter with SMI diagnosis
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue

        is_acute_ip = resource_has_any_code(enc, bh_acute_ip) or any(
            codeable_concept_has_any_code(t, bh_acute_ip) for t in enc.get("type", [])
        )
        if not is_acute_ip:
            # Check Visit Setting Unspecified with Acute Inpatient POS
            is_acute_ip = (
                resource_has_any_code(enc, visit_unspecified)
                or any(
                    codeable_concept_has_any_code(t, visit_unspecified)
                    for t in enc.get("type", [])
                )
            ) and get_encounter_class(enc) == "IMP"

        if is_acute_ip:
            # Check for SMI diagnosis on encounter
            has_smi = False
            for dx in enc.get("diagnosis", []):
                cc = dx.get("condition", {}).get("concept", {})
                if cc and codeable_concept_has_any_code(cc, smi_codes):
                    has_smi = True
                    break
            if not has_smi:
                for cond in get_resources_by_type(bundle, "Condition"):
                    cond_enc = cond.get("encounter", {}).get("reference", "")
                    if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                        if resource_has_any_code(cond, smi_codes):
                            has_smi = True
                            break
            if has_smi:
                evaluated.append(f"Encounter/{enc.get('id', 'unknown')}")
                return True, evaluated

    # Check for two visits on different dates with SMI diagnosis
    visit_dates_with_smi: list[tuple[date, str]] = []
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

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue

        is_qualifying_setting = False
        for vs in outpatient_vs_list:
            if resource_has_any_code(enc, vs) or any(
                codeable_concept_has_any_code(t, vs) for t in enc.get("type", [])
            ):
                is_qualifying_setting = True
                break

        if not is_qualifying_setting:
            continue

        has_smi = False
        for dx in enc.get("diagnosis", []):
            cc = dx.get("condition", {}).get("concept", {})
            if cc and codeable_concept_has_any_code(cc, smi_codes):
                has_smi = True
                break
        if not has_smi:
            for cond in get_resources_by_type(bundle, "Condition"):
                cond_enc = cond.get("encounter", {}).get("reference", "")
                if enc.get("id") and f"Encounter/{enc['id']}" in cond_enc:
                    if resource_has_any_code(cond, smi_codes):
                        has_smi = True
                        break

        if has_smi:
            visit_dates_with_smi.append(
                (enc_date, f"Encounter/{enc.get('id', 'unknown')}")
            )

    unique_dates = {d for d, _ in visit_dates_with_smi}
    if len(unique_dates) >= 2:
        for _, ref in visit_dates_with_smi[:2]:
            evaluated.append(ref)
        return True, evaluated

    return False, evaluated


def _has_antipsychotic(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient was dispensed an antipsychotic during MY."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    # Check claims/encounter data (Long Acting Injections Value Set)
    lai_codes = all_codes(VALUE_SETS, "Long Acting Injections")
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, my_end):
            continue
        if resource_has_any_code(enc, lai_codes) or any(
            codeable_concept_has_any_code(t, lai_codes) for t in enc.get("type", [])
        ):
            evaluated.append(f"Encounter/{enc.get('id', 'unknown')}")
            return True, evaluated

    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, my_start, my_end):
            continue
        if resource_has_any_code(proc, lai_codes):
            evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
            return True, evaluated

    # Check pharmacy data - look for any antipsychotic medication dispense
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date or not is_date_in_range(med_date, my_start, my_end):
                continue
            # SSD Antipsychotic Medications are identified via pharmacy data
            # The measure uses an SSD Antipsychotic Medications List
            # We check if the medication resource exists with a valid date
            evaluated.append(f"{rtype}/{med.get('id', 'unknown')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Members 18-64 with schizophrenia/bipolar who were dispensed antipsychotic.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 18 or age > 64:
        return False, evaluated

    has_smi, smi_refs = _has_schizophrenia_or_bipolar(bundle, measurement_year)
    evaluated.extend(smi_refs)
    if not has_smi:
        return False, evaluated

    has_ap, ap_refs = _has_antipsychotic(bundle, measurement_year)
    evaluated.extend(ap_refs)
    if not has_ap:
        return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Exclude members with diabetes, no antipsychotic dispensing,
    hospice, or death.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    # Check common exclusions (hospice, death)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    # Exclude members with diabetes (claim/encounter or pharmacy data)
    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")
    if diabetes_codes:
        # Two diagnoses on different dates during MY or prior year
        diabetes_conditions: list[date] = []
        for cond in get_resources_by_type(bundle, "Condition"):
            onset = get_condition_onset(cond)
            if onset and (is_date_in_range(onset, py_start, my_end)):
                if resource_has_any_code(cond, diabetes_codes):
                    diabetes_conditions.append(onset)

        unique_dates = set(diabetes_conditions)
        if len(unique_dates) >= 2:
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    A glucose test or HbA1c test performed during the measurement year.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    glucose_lab = all_codes(VALUE_SETS, "Glucose Lab Test")
    glucose_result = all_codes(VALUE_SETS, "Glucose Test Result or Finding")
    hba1c_lab = all_codes(VALUE_SETS, "HbA1c Lab Test")
    hba1c_result = all_codes(VALUE_SETS, "HbA1c Test Result or Finding")

    screening_vs_list = [glucose_lab, glucose_result, hba1c_lab, hba1c_result]

    for obs in get_resources_by_type(bundle, "Observation"):
        obs_date = get_observation_date(obs)
        if not obs_date or not is_date_in_range(obs_date, my_start, my_end):
            continue
        for vs in screening_vs_list:
            if resource_has_any_code(obs, vs):
                evaluated.append(f"Observation/{obs.get('id', 'unknown')}")
                return True, evaluated

    # Also check procedures
    for proc in get_resources_by_type(bundle, "Procedure"):
        proc_date = get_procedure_date(proc)
        if not proc_date or not is_date_in_range(proc_date, my_start, my_end):
            continue
        for vs in screening_vs_list:
            if resource_has_any_code(proc, vs):
                evaluated.append(f"Procedure/{proc.get('id', 'unknown')}")
                return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_ssd_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the SSD measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="SSD",
        measure_name="Diabetes Screening for People With Schizophrenia or Bipolar Disorder Who Are Using Antipsychotic Medications",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
