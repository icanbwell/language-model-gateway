"""
HEDIS MY 2025 - Adherence to Antipsychotic Medications for Individuals With
Schizophrenia (SAA)

The percentage of members 18 years of age and older during the measurement year
with schizophrenia or schizoaffective disorder who were dispensed and remained
on an antipsychotic medication for at least 80% of their treatment period.
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
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_class,
    get_condition_onset,
    get_procedure_date,
    get_medication_date,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("SAA")

# Long-acting injection value sets and their days supply
LAI_VS_DAYS = {
    "Long Acting Injections 14 Days Supply": 14,
    "Long Acting Injections 28 Days Supply": 28,
    "Long Acting Injections 30 Days Supply": 30,
    "Long Acting Injections 35 Days Supply": 35,
    "Long Acting Injections 104 Days Supply": 104,
    "Long Acting Injections 201 Days Supply": 201,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_schizophrenia(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Identify members with schizophrenia or schizoaffective disorder during MY.
    Same pattern as SSD/SMD/SMC: one acute inpatient with dx OR two visits.
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

    # Check acute inpatient
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
            if _enc_has_dx(bundle, enc, schiz_codes):
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
        if _enc_has_dx(bundle, enc, schiz_codes):
            visit_dates.append((enc_date, f"Encounter/{enc.get('id', 'unknown')}"))

    unique_dates = {d for d, _ in visit_dates}
    if len(unique_dates) >= 2:
        for _, ref in visit_dates[:2]:
            evaluated.append(ref)
        return True, evaluated

    return False, evaluated


def _enc_has_dx(bundle: dict, enc: dict, dx_codes: dict[str, set[str]]) -> bool:
    """Check if encounter has a diagnosis matching codes."""
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


def _get_antipsychotic_dispensing_events(
    bundle: dict, start: date, end: date
) -> list[dict[str, Any]]:
    """Find all antipsychotic medication dispensing events in date range."""
    events: list[dict[str, Any]] = []

    # Check pharmacy data - oral medications
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date or not is_date_in_range(med_date, start, end):
                continue

            days_supply = None
            if rtype == "MedicationDispense":
                ds = med.get("daysSupply", {}).get("value")
                if ds:
                    days_supply = int(ds)
            if not days_supply:
                days_supply = 30  # Default oral

            events.append(
                {
                    "date": med_date,
                    "days_supply": days_supply,
                    "ref": f"{rtype}/{med.get('id', 'unknown')}",
                    "is_lai": False,
                }
            )

    # Check claim/encounter data for long-acting injections
    for vs_name, ds in LAI_VS_DAYS.items():
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        for enc in get_resources_by_type(bundle, "Encounter"):
            enc_date = get_encounter_date(enc)
            if not enc_date or not is_date_in_range(enc_date, start, end):
                continue
            if resource_has_any_code(enc, vs_codes) or any(
                codeable_concept_has_any_code(t, vs_codes) for t in enc.get("type", [])
            ):
                events.append(
                    {
                        "date": enc_date,
                        "days_supply": ds,
                        "ref": f"Encounter/{enc.get('id', 'unknown')}",
                        "is_lai": True,
                    }
                )

        for proc in get_resources_by_type(bundle, "Procedure"):
            proc_date = get_procedure_date(proc)
            if not proc_date or not is_date_in_range(proc_date, start, end):
                continue
            if resource_has_any_code(proc, vs_codes):
                events.append(
                    {
                        "date": proc_date,
                        "days_supply": ds,
                        "ref": f"Procedure/{proc.get('id', 'unknown')}",
                        "is_lai": True,
                    }
                )

    return sorted(events, key=lambda e: e["date"])


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Members >= 18 with schizophrenia or schizoaffective disorder."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 18:
        return False, evaluated

    has_schiz, schiz_refs = _has_schizophrenia(bundle, measurement_year)
    evaluated.extend(schiz_refs)
    if not has_schiz:
        return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Exclude: dementia diagnosis, fewer than 2 antipsychotic dispensing events,
    hospice, death, frailty/advanced illness (age-dependent).
    """
    evaluated: list[str] = []

    # Common exclusions (hospice, death, palliative care, frailty)
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=True
    )
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)

    # Dementia diagnosis
    dementia_codes = all_codes(VALUE_SETS, "Dementia")
    if dementia_codes:
        for cond in get_resources_by_type(bundle, "Condition"):
            onset = get_condition_onset(cond)
            if onset and is_date_in_range(onset, my_start, my_end):
                if resource_has_any_code(cond, dementia_codes):
                    return True, evaluated

    # Fewer than 2 antipsychotic dispensing events
    dispensing_events = _get_antipsychotic_dispensing_events(bundle, my_start, my_end)
    if len(dispensing_events) < 2:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    PDC >= 80% for antipsychotic medications during the treatment period
    (IPSD through Dec 31 of MY).
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    # Find IPSD (earliest dispensing event for any antipsychotic in MY)
    events = _get_antipsychotic_dispensing_events(bundle, my_start, my_end)
    if not events:
        return False, evaluated

    ipsd = events[0]["date"]
    treatment_days = (my_end - ipsd).days + 1  # IPSD through Dec 31

    if treatment_days <= 0:
        return False, evaluated

    # Count covered days
    covered: set[int] = set()
    for event in events:
        offset = (event["date"] - ipsd).days
        for d in range(event["days_supply"]):
            day = offset + d
            if 0 <= day < treatment_days:
                covered.add(day)
        evaluated.append(event["ref"])

    pdc = len(covered) / treatment_days
    pdc_pct = round(pdc * 100)

    return pdc_pct >= 80, list(dict.fromkeys(evaluated))


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_saa_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """Calculate the SAA measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="SAA",
        measure_name="Adherence to Antipsychotic Medications for Individuals With Schizophrenia",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
