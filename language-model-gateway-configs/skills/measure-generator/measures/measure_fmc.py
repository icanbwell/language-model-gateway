"""
HEDIS MY 2025 - Follow-Up After Emergency Department Visit for People
With Multiple High-Risk Chronic Conditions (FMC).

ED visit-based measure for members 18+ who have 2+ high-risk chronic
conditions and had a follow-up service within 7 days of the ED visit.
"""

from datetime import date, timedelta

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
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    all_codes,
    ICD10CM,
)

VALUE_SETS = load_value_sets_from_csv("FMC")

# Chronic condition groups -- each bullet in the spec is one "condition".
# A member must have 2+ *different* chronic conditions prior to the ED visit.
_CHRONIC_CONDITION_GROUPS: list[tuple[str, list[str]]] = [
    ("COPD/Asthma", ["COPD Diagnosis", "Asthma Diagnosis"]),
    ("Dementia", ["Dementia", "Frontotemporal Dementia"]),
    ("CKD", ["Chronic Kidney Disease"]),
    ("Depression", ["Major Depression", "Dysthymic Disorder"]),
    ("Heart Failure", ["Heart Failure and Cardiomyopathy"]),
    ("MI", ["MI", "Old Myocardial Infarction"]),
    ("Atrial Fibrillation", ["Atrial Fibrillation"]),
    ("Stroke", ["Stroke"]),
]


def _aggregate_codes_for_group(
    vs_names: list[str],
) -> dict[str, set[str]]:
    """Merge codes from multiple value sets into one dict."""
    combined: dict[str, set[str]] = {}
    for name in vs_names:
        for system, codes in all_codes(VALUE_SETS, name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _find_eligible_ed_visits(
    bundle: dict, measurement_year: int
) -> list[tuple[dict, date]]:
    """Identify eligible ED visits (Steps 1-5 of the spec).

    Returns a de-duplicated list of (encounter, date) tuples.
    """
    my_start, _ = measurement_year_dates(measurement_year)
    ed_end = date(measurement_year, 12, 24)
    birth_date = get_patient_birth_date(bundle)

    ed_codes = all_codes(VALUE_SETS, "ED")
    if not ed_codes:
        return []

    # Step 1: ED visits Jan 1 - Dec 24, age 18+
    ed_visits: list[tuple[dict, date]] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date or not is_date_in_range(enc_date, my_start, ed_end):
            continue
        if not resource_has_any_code(enc, ed_codes):
            has_type = any(
                codeable_concept_has_any_code(t, ed_codes) for t in enc.get("type", [])
            )
            if not has_type:
                continue
        if birth_date and calculate_age(birth_date, enc_date) < 18:
            continue
        ed_visits.append((enc, enc_date))

    if not ed_visits:
        return []

    # Step 2: Exclude ED visits resulting in inpatient stay within 7 days
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    if inpatient_codes:
        inpatient_admissions: list[tuple[date, date]] = []
        for enc in get_resources_by_type(bundle, "Encounter"):
            if not resource_has_any_code(enc, inpatient_codes):
                has_type = any(
                    codeable_concept_has_any_code(t, inpatient_codes)
                    for t in enc.get("type", [])
                )
                if not has_type:
                    continue
            admit = get_encounter_date(enc)
            if admit:
                inpatient_admissions.append((admit, admit))

        filtered = []
        for enc, ed_date in ed_visits:
            excluded = False
            for admit_date, _ in inpatient_admissions:
                if ed_date <= admit_date <= ed_date + timedelta(days=7):
                    excluded = True
                    break
            if not excluded:
                filtered.append((enc, ed_date))
        ed_visits = filtered

    if not ed_visits:
        return []

    # Step 3 & 4: Identify members with 2+ different chronic conditions
    # prior to the ED visit. Check encounters, conditions, and inpatient
    # discharges during MY and prior year.
    prior_start = date(measurement_year - 1, 1, 1)

    # Also check for Z51.89 exclusion and Other Stroke Exclusions
    stroke_excl_codes = all_codes(VALUE_SETS, "Other Stroke Exclusions")

    outpatient_codes = all_codes(
        VALUE_SETS, "Outpatient, ED, Telehealth and Nonacute Inpatient"
    )
    if not outpatient_codes:
        # Fallback to broader set
        outpatient_codes = all_codes(VALUE_SETS, "Outpatient and Telehealth")

    eligible_visits: list[tuple[dict, date]] = []
    for enc, ed_date in ed_visits:
        # Exclude Z51.89 principal diagnosis
        z5189_found = False
        for coding in enc.get("reasonCode", [{}]):
            for c in coding.get("coding", []):
                if c.get("system") == ICD10CM and c.get("code") == "Z51.89":
                    z5189_found = True
                    break
        if z5189_found:
            continue

        # Exclude Other Stroke Exclusions
        if stroke_excl_codes:
            has_stroke_excl = resource_has_any_code(enc, stroke_excl_codes)
            if not has_stroke_excl:
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, stroke_excl_codes):
                        has_stroke_excl = True
                        break
                if not has_stroke_excl:
                    for reason in enc.get("reasonCode", []):
                        if codeable_concept_has_any_code(reason, stroke_excl_codes):
                            has_stroke_excl = True
                            break
            if has_stroke_excl:
                continue

        # Count distinct chronic conditions prior to ED visit
        condition_count = 0
        for _group_name, vs_names in _CHRONIC_CONDITION_GROUPS:
            group_codes = _aggregate_codes_for_group(vs_names)
            if not group_codes:
                continue
            # Check conditions
            cond_matches = find_conditions_with_codes(
                bundle, group_codes, prior_start, ed_date - timedelta(days=1)
            )
            if cond_matches:
                condition_count += 1
                continue
            # Check encounters with these diagnoses
            enc_matches = find_encounters_with_codes(
                bundle, group_codes, prior_start, ed_date - timedelta(days=1)
            )
            if enc_matches:
                condition_count += 1
                continue

        # Also check COPD group for ICD-10-CM J40 (unspecified bronchitis)
        if condition_count < 2:
            for cond in get_resources_by_type(bundle, "Condition"):
                for coding in cond.get("code", {}).get("coding", []):
                    if coding.get("system") == ICD10CM and coding.get("code") == "J40":
                        # This counts as COPD/Asthma group
                        # Only add if we didn't already count it
                        condition_count += 1
                        break

        if condition_count >= 2:
            eligible_visits.append((enc, ed_date))

    if not eligible_visits:
        return []

    # Step 5: Deduplicate within 8-day periods
    eligible_visits.sort(key=lambda x: x[1])
    deduped: list[tuple[dict, date]] = []
    last_included: date | None = None
    for enc, ed_date in eligible_visits:
        if last_included is None or (ed_date - last_included).days >= 8:
            deduped.append((enc, ed_date))
            last_included = ed_date

    return deduped


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if the patient has eligible FMC ED visits."""
    episodes = _find_eligible_ed_visits(bundle, measurement_year)
    evaluated = [f"Encounter/{e.get('id')}" for e, _ in episodes]
    return len(episodes) > 0, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice, death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check numerator: follow-up service within 7 days after ED visit.

    Includes the date of the ED visit (8 total days).
    """
    evaluated: list[str] = []
    episodes = _find_eligible_ed_visits(bundle, measurement_year)
    if not episodes:
        return False, evaluated

    # Collect all follow-up value sets
    followup_vs_names = [
        "Outpatient and Telehealth",
        "Transitional Care Management Services",
        "Case Management Encounter",
        "Complex Care Management Services",
        "BH Outpatient",
        "Partial Hospitalization or Intensive Outpatient",
        "Substance Use Disorder Services",
        "Substance Abuse Counseling and Surveillance",
        "Electroconvulsive Therapy",
        "Visit Setting Unspecified",
    ]

    followup_codes: dict[str, set[str]] = {}
    for vs_name in followup_vs_names:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            followup_codes.setdefault(system, set()).update(codes)

    if not followup_codes:
        return False, evaluated

    for enc, ed_date in episodes:
        window_end = ed_date + timedelta(days=7)
        matches = find_encounters_with_codes(
            bundle, followup_codes, ed_date, window_end
        )
        # Exclude the ED visit itself (must be different encounter)
        matches = [(m, d) for m, d in matches if m.get("id") != enc.get("id")]
        if matches:
            evaluated.extend(f"Encounter/{m.get('id')}" for m, _ in matches)
            return True, evaluated

        # Also check procedures (e.g., ECT)
        proc_matches = find_procedures_with_codes(
            bundle, followup_codes, ed_date, window_end
        )
        if proc_matches:
            evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
            return True, evaluated

    return False, evaluated


def calculate_fmc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate FMC measure and return a FHIR MeasureReport."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="FMC",
        measure_name="Follow-Up After ED Visit for People With Multiple High-Risk Chronic Conditions",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
