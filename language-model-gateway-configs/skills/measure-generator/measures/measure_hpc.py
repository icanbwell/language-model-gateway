"""
HEDIS MY 2025 - Hospitalization for Potentially Preventable Complications (HPC).

For members 67 years of age and older, the rate of discharges for
ambulatory care sensitive conditions (ACSC) per 1,000 members and the
risk-adjusted ratio of observed-to-expected discharges for ACSC by
chronic and acute conditions.

Three categories are reported:
  - Chronic ACSC (diabetes complications, COPD, asthma, hypertension, HF)
  - Acute ACSC (bacterial pneumonia, UTI, cellulitis, pressure ulcers)
  - Total ACSC (combined)

For individual patient calculation, we report the observed ACSC discharge
counts as the numerator.
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
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("HPC")


def _is_acute_stay(encounter: dict) -> bool:
    """Check if encounter is an acute inpatient or observation stay."""
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


def _has_dx_code(encounter: dict, value_set_name: str) -> bool:
    """Check if encounter has a principal diagnosis in the given value set."""
    codes = all_codes(VALUE_SETS, value_set_name)
    if not codes:
        return False
    if resource_has_any_code(encounter, codes):
        return True
    for t in encounter.get("type", []):
        if codeable_concept_has_any_code(t, codes):
            return True
    for rc in encounter.get("reasonCode", []):
        if codeable_concept_has_any_code(rc, codes):
            return True
    return False


def _has_exclusion_dx(encounter: dict, value_set_name: str) -> bool:
    """Check if encounter has any diagnosis in the exclusion value set."""
    return _has_dx_code(encounter, value_set_name)


def _is_chronic_acsc(encounter: dict) -> bool:
    """Check if a discharge qualifies as a chronic ACSC.

    Chronic ACSCs: diabetes short-term/long-term complications, uncontrolled
    diabetes, lower-extremity amputation with diabetes, COPD, asthma,
    heart failure, hypertension.
    """
    # Diabetes short-term complications
    if _has_dx_code(encounter, "Diabetes Short Term Complications"):
        return True

    # Diabetes long-term complications
    if _has_dx_code(encounter, "Diabetes Long Term Complications"):
        return True

    # Uncontrolled diabetes
    if _has_dx_code(encounter, "Uncontrolled Diabetes"):
        return True

    # Lower extremity amputation with diabetes diagnosis
    amp_codes = all_codes(VALUE_SETS, "Lower Extremity Amputation Procedures")
    diab_dx_codes = all_codes(VALUE_SETS, "Diabetes Diagnosis")
    traumatic_amp_codes = all_codes(
        VALUE_SETS, "Traumatic Amputation of Lower Extremity"
    )
    if amp_codes and diab_dx_codes:
        has_amp = resource_has_any_code(encounter, amp_codes) or any(
            codeable_concept_has_any_code(t, amp_codes)
            for t in encounter.get("type", [])
        )
        has_diab = resource_has_any_code(encounter, diab_dx_codes) or any(
            codeable_concept_has_any_code(t, diab_dx_codes)
            for t in encounter.get("type", [])
        )
        if has_amp and has_diab:
            if traumatic_amp_codes and _has_exclusion_dx(
                encounter, "Traumatic Amputation of Lower Extremity"
            ):
                pass  # Exclude
            else:
                return True

    # COPD (exclude cystic fibrosis/respiratory anomalies)
    if _has_dx_code(encounter, "COPD Diagnosis"):
        if not _has_exclusion_dx(
            encounter, "Cystic Fibrosis and Respiratory System Anomalies"
        ):
            return True

    # Asthma (exclude cystic fibrosis/respiratory anomalies)
    if _has_dx_code(encounter, "Asthma Diagnosis"):
        if not _has_exclusion_dx(
            encounter, "Cystic Fibrosis and Respiratory System Anomalies"
        ):
            return True

    # Heart failure (exclude cardiac procedures)
    if _has_dx_code(encounter, "Heart Failure Diagnosis"):
        if not _has_exclusion_dx(encounter, "Cardiac Procedure"):
            return True

    # Hypertension (exclude cardiac procedures and kidney disease + dialysis)
    if _has_dx_code(encounter, "Hypertension"):
        if _has_exclusion_dx(encounter, "Cardiac Procedure"):
            return False
        kidney_codes = all_codes(VALUE_SETS, "Stage I Through IV Kidney Disease")
        dialysis_codes = all_codes(VALUE_SETS, "Dialysis")
        if kidney_codes and dialysis_codes:
            has_kidney = resource_has_any_code(encounter, kidney_codes) or any(
                codeable_concept_has_any_code(t, kidney_codes)
                for t in encounter.get("type", [])
            )
            has_dialysis = resource_has_any_code(encounter, dialysis_codes) or any(
                codeable_concept_has_any_code(t, dialysis_codes)
                for t in encounter.get("type", [])
            )
            if has_kidney and has_dialysis:
                return False
        return True

    return False


def _is_acute_acsc(encounter: dict) -> bool:
    """Check if a discharge qualifies as an acute ACSC.

    Acute ACSCs: bacterial pneumonia, UTI, cellulitis, severe pressure ulcers.
    """
    # Bacterial pneumonia (exclude sickle cell and immunocompromised)
    if _has_dx_code(encounter, "Bacterial Pneumonia"):
        if _has_exclusion_dx(encounter, "Sickle Cell Anemia and HB S Disease"):
            return False
        if _has_exclusion_dx(encounter, "Immunocompromised State"):
            return False
        return True

    # UTI (exclude kidney/urinary tract disorders and immunocompromised)
    if _has_dx_code(encounter, "Urinary Tract Infection"):
        if _has_exclusion_dx(encounter, "Kidney and Urinary Tract Disorders"):
            return False
        if _has_exclusion_dx(encounter, "Immunocompromised State"):
            return False
        return True

    # Cellulitis
    if _has_dx_code(encounter, "Cellulitis"):
        return True

    # Severe pressure ulcers
    if _has_dx_code(encounter, "Severe Pressure Ulcers"):
        return True

    return False


def _count_acsc_discharges(
    bundle: dict, measurement_year: int
) -> tuple[int, int, list[str]]:
    """Count chronic and acute ACSC discharges during the measurement year.

    Returns (chronic_count, acute_count, evaluated_refs).
    """
    my_start, my_end = measurement_year_dates(measurement_year)
    chronic_count = 0
    acute_count = 0
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        if not _is_acute_stay(enc):
            continue
        discharge_date = get_encounter_end_date(enc)
        if not discharge_date or not is_date_in_range(discharge_date, my_start, my_end):
            continue

        if _is_chronic_acsc(enc):
            chronic_count += 1
            evaluated.append(f"Encounter/{enc.get('id')}")
        elif _is_acute_acsc(enc):
            acute_count += 1
            evaluated.append(f"Encounter/{enc.get('id')}")

    return chronic_count, acute_count, evaluated


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient is 67+ as of Dec 31 of MY."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    if age >= 67:
        return True, []
    return False, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice, I-SNP, LTI."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient has any ACSC discharges."""
    chronic, acute, evaluated = _count_acsc_discharges(bundle, measurement_year)
    return (chronic + acute) > 0, evaluated


def calculate_hpc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the HPC measure with chronic, acute, and total ACSC rates."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    chronic_count = 0
    acute_count = 0
    if is_eligible and not is_excluded:
        chronic_count, acute_count, num_refs = _count_acsc_discharges(
            bundle, measurement_year
        )
        all_evaluated.extend(num_refs)

    total_count = chronic_count + acute_count

    report = build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="HPC",
        measure_name="Hospitalization for Potentially Preventable Complications",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "HPC-Chronic",
                "display": "Chronic ACSC",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": chronic_count > 0,
            },
            {
                "code": "HPC-Acute",
                "display": "Acute ACSC",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": acute_count > 0,
            },
            {
                "code": "HPC-Total",
                "display": "Total ACSC",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": total_count > 0,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )

    # Add observed counts as extensions
    report["extension"] = [
        {
            "url": "http://ncqa.org/fhir/StructureDefinition/observed-chronic-acsc-count",
            "valueInteger": chronic_count,
        },
        {
            "url": "http://ncqa.org/fhir/StructureDefinition/observed-acute-acsc-count",
            "valueInteger": acute_count,
        },
        {
            "url": "http://ncqa.org/fhir/StructureDefinition/observed-total-acsc-count",
            "valueInteger": total_count,
        },
    ]

    return report
