"""
HEDIS MY 2025 - Metabolic Monitoring for Children and Adolescents
on Antipsychotics (APM-E)

The percentage of children and adolescents 1-17 years of age who had
two or more antipsychotic prescriptions and had metabolic testing.

Three rates:
- Blood Glucose testing
- Cholesterol testing
- Blood Glucose AND Cholesterol testing
"""

from __future__ import annotations

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    parse_date,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    find_procedures_with_codes,
    find_observations_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("APM-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_two_antipsychotic_events(
    bundle: dict,
    measurement_year: int,
) -> bool:
    """Check for >= 2 antipsychotic dispensing events on different dates during MY."""
    my_start, my_end = measurement_year_dates(measurement_year)
    ap_codes = all_codes(VALUE_SETS, "APM Antipsychotic Medications")
    if not ap_codes:
        return False

    dispensing_dates: set[date] = set()
    for med, med_date in find_medications_with_codes(
        bundle, ap_codes, my_start, my_end
    ):
        if med_date:
            dispensing_dates.add(med_date)

    return len(dispensing_dates) >= 2


def _has_glucose_test(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check for blood glucose or HbA1c test during MY."""
    my_start, my_end = measurement_year_dates(measurement_year)
    evaluated: list[str] = []

    for vs_name in (
        "Glucose Lab Test",
        "Glucose Test Result or Finding",
        "HbA1c Lab Test",
        "HbA1c Test Result or Finding",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        found_obs = find_observations_with_codes(bundle, vs_codes, my_start, my_end)
        if found_obs:
            evaluated.append(f"Observation/{found_obs[0][0].get('id')}")
            return True, evaluated
        found_proc = find_procedures_with_codes(bundle, vs_codes, my_start, my_end)
        if found_proc:
            evaluated.append(f"Procedure/{found_proc[0][0].get('id')}")
            return True, evaluated
        # DiagnosticReport
        for dr in get_resources_by_type(bundle, "DiagnosticReport"):
            dr_date = parse_date(
                dr.get("effectiveDateTime")
                or (dr.get("effectivePeriod") or {}).get("start")
            )
            if dr_date and is_date_in_range(dr_date, my_start, my_end):
                if resource_has_any_code(dr, vs_codes):
                    evaluated.append(f"DiagnosticReport/{dr.get('id')}")
                    return True, evaluated

    return False, evaluated


def _has_cholesterol_test(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check for cholesterol or LDL-C test during MY."""
    my_start, my_end = measurement_year_dates(measurement_year)
    evaluated: list[str] = []

    for vs_name in (
        "Cholesterol Lab Test",
        "Cholesterol Test Result or Finding",
        "LDL C Lab Test",
        "LDL C Test Result or Finding",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        found_obs = find_observations_with_codes(bundle, vs_codes, my_start, my_end)
        if found_obs:
            evaluated.append(f"Observation/{found_obs[0][0].get('id')}")
            return True, evaluated
        found_proc = find_procedures_with_codes(bundle, vs_codes, my_start, my_end)
        if found_proc:
            evaluated.append(f"Procedure/{found_proc[0][0].get('id')}")
            return True, evaluated
        for dr in get_resources_by_type(bundle, "DiagnosticReport"):
            dr_date = parse_date(
                dr.get("effectiveDateTime")
                or (dr.get("effectivePeriod") or {}).get("start")
            )
            if dr_date and is_date_in_range(dr_date, my_start, my_end):
                if resource_has_any_code(dr, vs_codes):
                    evaluated.append(f"DiagnosticReport/{dr.get('id')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Members 1-17 by end of MY with >= 2 antipsychotic dispensing events."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (1 <= age <= 17):
        return False, []
    if not _has_two_antipsychotic_events(bundle, measurement_year):
        return False, []
    return True, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Hospice and death."""
    return check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=False,
    )


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Single-rate wrapper: returns True if both glucose AND cholesterol met."""
    glucose_met, glucose_refs = _has_glucose_test(bundle, measurement_year)
    chol_met, chol_refs = _has_cholesterol_test(bundle, measurement_year)
    return (glucose_met and chol_met), glucose_refs + chol_refs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_apm_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate APM-E with three-rate report."""
    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated = eligible_refs + exclusion_refs

    rate_names = ["BloodGlucose", "Cholesterol", "BloodGlucoseAndCholesterol"]

    if not is_eligible:
        groups = [
            {
                "code": f"APM-E-{r}",
                "display": f"APM-E {r}",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            }
            for r in rate_names
        ]
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="APM-E",
            measure_name="Metabolic Monitoring for Children and Adolescents on Antipsychotics",
            measurement_year=measurement_year,
            groups=groups,
            evaluated_resources=all_evaluated,
        )

    glucose_met, glucose_refs = _has_glucose_test(bundle, measurement_year)
    chol_met, chol_refs = _has_cholesterol_test(bundle, measurement_year)
    both_met = glucose_met and chol_met
    all_evaluated.extend(glucose_refs + chol_refs)

    groups = [
        {
            "code": "APM-E-BloodGlucose",
            "display": "APM-E Blood Glucose Testing",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": glucose_met,
        },
        {
            "code": "APM-E-Cholesterol",
            "display": "APM-E Cholesterol Testing",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": chol_met,
        },
        {
            "code": "APM-E-BloodGlucoseAndCholesterol",
            "display": "APM-E Blood Glucose and Cholesterol Testing",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": both_met,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="APM-E",
        measure_name="Metabolic Monitoring for Children and Adolescents on Antipsychotics",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
