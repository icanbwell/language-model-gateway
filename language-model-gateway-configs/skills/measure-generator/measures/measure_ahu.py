"""
HEDIS MY 2025 - Acute Hospital Utilization (AHU).

For members 18 years of age and older, the risk-adjusted ratio of
observed-to-expected acute inpatient and observation stay discharges
during the measurement year.

This is a member-based, risk-adjusted utilization measure (rate per 1000).
For individual patient calculation, we report the observed count of
qualifying discharges as the numerator.
"""

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_end_date,
    build_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("AHU")


def _is_acute_stay(encounter: dict) -> bool:
    """Check if an encounter is an acute inpatient or observation stay."""
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    observation_codes = all_codes(VALUE_SETS, "Observation Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")

    is_ip_or_obs = False
    for code_set in (inpatient_codes, observation_codes):
        if code_set and (
            resource_has_any_code(encounter, code_set)
            or any(
                codeable_concept_has_any_code(t, code_set)
                for t in encounter.get("type", [])
            )
        ):
            is_ip_or_obs = True
            break

    if not is_ip_or_obs:
        return False

    if nonacute_codes and (
        resource_has_any_code(encounter, nonacute_codes)
        or any(
            codeable_concept_has_any_code(t, nonacute_codes)
            for t in encounter.get("type", [])
        )
    ):
        return False

    return True


def _should_exclude_discharge(encounter: dict) -> bool:
    """Check if a discharge should be excluded from observed events.

    Excludes: mental health/chemical dependency, live-born infant,
    maternity, planned stays, and death discharges.
    """
    mental_codes = all_codes(VALUE_SETS, "Mental and Behavioral Disorders")
    delivery_codes = all_codes(VALUE_SETS, "Deliveries Infant Record")
    maternity_dx_codes = all_codes(VALUE_SETS, "Maternity Diagnosis")
    maternity_codes = all_codes(VALUE_SETS, "Maternity")
    chemo_codes = all_codes(VALUE_SETS, "Chemotherapy Encounter")
    rehab_codes = all_codes(VALUE_SETS, "Rehabilitation")
    kidney_codes = all_codes(VALUE_SETS, "Kidney Transplant")
    bmt_codes = all_codes(VALUE_SETS, "Bone Marrow Transplant")
    organ_codes = all_codes(VALUE_SETS, "Organ Transplant Other Than Kidney")
    pancreatic_codes = all_codes(
        VALUE_SETS, "Introduction of Autologous Pancreatic Cells"
    )
    planned_proc_codes = all_codes(VALUE_SETS, "Potentially Planned Procedures")
    acute_dx_codes = all_codes(VALUE_SETS, "Acute Condition")

    for code_set in (mental_codes, delivery_codes, maternity_dx_codes, maternity_codes):
        if code_set and (
            resource_has_any_code(encounter, code_set)
            or any(
                codeable_concept_has_any_code(t, code_set)
                for t in encounter.get("type", [])
            )
        ):
            return True

    # Planned stays
    if chemo_codes and resource_has_any_code(encounter, chemo_codes):
        return True
    if rehab_codes and resource_has_any_code(encounter, rehab_codes):
        return True

    for transplant_codes in (kidney_codes, bmt_codes, organ_codes, pancreatic_codes):
        if transplant_codes and (
            resource_has_any_code(encounter, transplant_codes)
            or any(
                codeable_concept_has_any_code(t, transplant_codes)
                for t in encounter.get("type", [])
            )
        ):
            return True

    if planned_proc_codes:
        has_planned = resource_has_any_code(encounter, planned_proc_codes) or any(
            codeable_concept_has_any_code(t, planned_proc_codes)
            for t in encounter.get("type", [])
        )
        if has_planned:
            has_acute = acute_dx_codes and (
                resource_has_any_code(encounter, acute_dx_codes)
                or any(
                    codeable_concept_has_any_code(t, acute_dx_codes)
                    for t in encounter.get("type", [])
                )
            )
            if not has_acute:
                return True

    # Death discharge
    discharge_disp = encounter.get("hospitalization", {}).get(
        "dischargeDisposition", {}
    )
    for coding in discharge_disp.get("coding", []):
        if coding.get("code") in ("20", "exp", "died"):
            return True

    return False


def _count_qualifying_discharges(
    bundle: dict, measurement_year: int
) -> tuple[int, list[str]]:
    """Count acute inpatient/observation discharges in the MY after exclusions."""
    my_start, my_end = measurement_year_dates(measurement_year)
    count = 0
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        if not _is_acute_stay(enc):
            continue
        discharge_date = get_encounter_end_date(enc)
        if not discharge_date or not is_date_in_range(discharge_date, my_start, my_end):
            continue
        if _should_exclude_discharge(enc):
            continue
        count += 1
        evaluated.append(f"Encounter/{enc.get('id')}")

    return count, evaluated


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient is 18+ as of Dec 31 of MY."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    if age >= 18:
        return True, []
    return False, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusion: hospice."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient had any qualifying acute discharges.

    For individual reporting, numerator = True if count > 0.
    The actual count is reported in the measure report.
    """
    count, evaluated = _count_qualifying_discharges(bundle, measurement_year)
    return count > 0, evaluated


def calculate_ahu_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the AHU measure.

    For individual patient, reports the observed discharge count.
    """
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    if not is_eligible:
        return build_measure_report(
            patient_id=patient_id,
            measure_abbreviation="AHU",
            measure_name="Acute Hospital Utilization",
            measurement_year=measurement_year,
            initial_population=False,
            denominator_exclusion=False,
            numerator=False,
            evaluated_resources=all_evaluated,
        )

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    discharge_count, num_refs = _count_qualifying_discharges(bundle, measurement_year)
    all_evaluated.extend(num_refs)

    report = build_measure_report(
        patient_id=patient_id,
        measure_abbreviation="AHU",
        measure_name="Acute Hospital Utilization",
        measurement_year=measurement_year,
        initial_population=True,
        denominator_exclusion=is_excluded,
        numerator=discharge_count > 0,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )

    # Add observed count as extension for utilization reporting
    report["extension"] = [
        {
            "url": "http://ncqa.org/fhir/StructureDefinition/observed-event-count",
            "valueInteger": discharge_count,
        }
    ]

    return report
