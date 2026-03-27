"""
HEDIS MY 2025 - Chlamydia Screening (CHL).

The percentage of members 16-24 years of age who were recommended for routine
chlamydia screening, were identified as sexually active and had at least one
test for chlamydia during the measurement year.
"""

from datetime import timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    parse_date,
    is_date_in_range,
    measurement_year_dates,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
    LOINC,
)

VALUE_SETS = load_value_sets_from_csv("CHL")


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: members 16-24 as of Dec 31, recommended for routine chlamydia
    screening (female administrative gender, or female sex assigned at birth,
    or female sex parameter for clinical use), AND sexually active during the
    measurement year.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 16 or age > 24:
        return False, evaluated

    # Check recommended for routine chlamydia screening
    patient = get_patient(bundle)
    if not patient:
        return False, evaluated

    gender = patient.get("gender", "")
    is_recommended = gender == "female"

    if not is_recommended:
        # Check sex assigned at birth via observations (LOINC 76689-9)
        for obs in get_resources_by_type(bundle, "Observation"):
            for coding in obs.get("code", {}).get("coding", []):
                if coding.get("system") == LOINC and coding.get("code") == "76689-9":
                    value_cc = obs.get("valueCodeableConcept", {})
                    for vc in value_cc.get("coding", []):
                        if vc.get("code") == "LA3-6":  # Female
                            is_recommended = True
                            break
                if is_recommended:
                    break
            if is_recommended:
                break

    if not is_recommended:
        return False, evaluated

    # Check sexually active via claim/encounter data or pharmacy data
    sexually_active = False

    # Claim/encounter: Diagnoses Indicating Sexual Activity
    dx_codes = all_codes(VALUE_SETS, "Diagnoses Indicating Sexual Activity")
    if dx_codes:
        hits = find_conditions_with_codes(bundle, dx_codes, my_start, my_end)
        if hits:
            sexually_active = True
            for cond, _ in hits:
                evaluated.append(f"Condition/{cond.get('id')}")

    # Claim/encounter: Procedures Indicating Sexual Activity
    if not sexually_active:
        proc_codes = all_codes(VALUE_SETS, "Procedures Indicating Sexual Activity")
        if proc_codes:
            hits = find_procedures_with_codes(bundle, proc_codes, my_start, my_end)
            if hits:
                sexually_active = True
                for proc, _ in hits:
                    evaluated.append(f"Procedure/{proc.get('id')}")

    # Pregnancy Tests (need Step 2 filtering)
    pregnancy_test_only = False
    if not sexually_active:
        pt_codes = all_codes(VALUE_SETS, "Pregnancy Tests")
        if pt_codes:
            pt_hits = find_observations_with_codes(bundle, pt_codes, my_start, my_end)
            if not pt_hits:
                pt_hits = find_procedures_with_codes(bundle, pt_codes, my_start, my_end)
            if pt_hits:
                # Step 2: remove if pregnancy test + isotretinoin/x-ray within 6 days
                radiology_codes = all_codes(VALUE_SETS, "Diagnostic Radiology")
                for pt_resource, pt_date in pt_hits:
                    if pt_date is None:
                        continue
                    exclude_this_test = False
                    window_end = pt_date + timedelta(days=6)

                    # Check for diagnostic radiology within 6 days
                    if radiology_codes:
                        rad_hits = find_procedures_with_codes(
                            bundle, radiology_codes, pt_date, window_end
                        )
                        if rad_hits:
                            exclude_this_test = True

                    if not exclude_this_test:
                        sexually_active = True
                        pregnancy_test_only = True
                        rtype = pt_resource.get("resourceType", "Observation")
                        evaluated.append(f"{rtype}/{pt_resource.get('id')}")
                        break

    # Pharmacy data: contraceptive medications
    if not sexually_active:
        # Contraceptive medications are identified via [Direct Reference] codes
        # in the CSV; they load under that value set name. Check MedicationDispense
        # and MedicationRequest for any medication dispensing event.
        for rtype in ("MedicationDispense", "MedicationRequest"):
            for med in get_resources_by_type(bundle, rtype):
                med_date = parse_date(
                    med.get("whenHandedOver") or med.get("authoredOn")
                )
                if med_date and is_date_in_range(med_date, my_start, my_end):
                    # If there are direct reference medication codes, check them
                    direct_codes = all_codes(VALUE_SETS, "[Direct Reference]")
                    if direct_codes:
                        mcc = med.get("medicationCodeableConcept", {})
                        for coding in mcc.get("coding", []):
                            sys = coding.get("system", "")
                            code = coding.get("code", "")
                            if code in direct_codes.get(sys, set()):
                                sexually_active = True
                                evaluated.append(f"{rtype}/{med.get('id')}")
                                break
                if sexually_active:
                    break
            if sexually_active:
                break

    if not sexually_active:
        return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions:
    - Sex assigned at birth = Male (LOINC 76689-9 = LA2-8)
    - Hospice, death
    """
    evaluated: list[str] = []

    # Check male sex assigned at birth
    for obs in get_resources_by_type(bundle, "Observation"):
        for coding in obs.get("code", {}).get("coding", []):
            if coding.get("system") == LOINC and coding.get("code") == "76689-9":
                value_cc = obs.get("valueCodeableConcept", {})
                for vc in value_cc.get("coding", []):
                    if vc.get("code") == "LA2-8":  # Male
                        return True, evaluated

    # Common exclusions
    excluded, refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    At least one chlamydia test (Chlamydia Tests Value Set) during the
    measurement year.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    chlamydia_codes = all_codes(VALUE_SETS, "Chlamydia Tests")
    if not chlamydia_codes:
        return False, evaluated

    obs_hits = find_observations_with_codes(bundle, chlamydia_codes, my_start, my_end)
    if obs_hits:
        for obs, _ in obs_hits:
            evaluated.append(f"Observation/{obs.get('id')}")
        return True, evaluated

    proc_hits = find_procedures_with_codes(bundle, chlamydia_codes, my_start, my_end)
    if proc_hits:
        for proc, _ in proc_hits:
            evaluated.append(f"Procedure/{proc.get('id')}")
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_chl_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the CHL measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="CHL",
        measure_name="Chlamydia Screening",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
