"""
HEDIS MY 2025 - Child and Adolescent Well-Care Visits (WCV).

The percentage of members 3-21 years of age who had at least one comprehensive
well-care visit with a PCP or an OB/GYN practitioner during the measurement year.

Telehealth visits are excluded from the numerator (MY 2025 change).
"""

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
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("WCV")


def _is_telehealth_encounter(encounter: dict) -> bool:
    """Check if an encounter is a telehealth visit that should be excluded."""
    telehealth_pos_codes = all_codes(VALUE_SETS, "Telehealth POS")
    online_codes = all_codes(VALUE_SETS, "Online Assessments")
    telephone_codes = all_codes(VALUE_SETS, "Telephone Visits")

    for code_set in (telehealth_pos_codes, online_codes, telephone_codes):
        if code_set and resource_has_any_code(encounter, code_set):
            return True
        if code_set:
            for t in encounter.get("type", []):
                if codeable_concept_has_any_code(t, code_set):
                    return True
    return False


def _is_lab_claim(encounter: dict) -> bool:
    """Check if the encounter is a laboratory claim (POS code 81)."""
    for t in encounter.get("type", []):
        for coding in t.get("coding", []):
            if coding.get("code") == "81":
                return True
    return False


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient is 3-21 years as of Dec 31 of the measurement year."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    if 3 <= age <= 21:
        return True, []
    return False, []


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice and death."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if patient had 1+ well-care visits during the measurement year.

    Either a Well Care Visit or an Encounter for Well Care (excluding lab
    claims with POS code 81). Telehealth visits are excluded.
    """
    my_start, my_end = measurement_year_dates(measurement_year)
    well_care_codes = all_codes(VALUE_SETS, "Well Care Visit")
    encounter_well_care_codes = all_codes(VALUE_SETS, "Encounter for Well Care")
    evaluated: list[str] = []

    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not is_date_in_range(enc_date, my_start, my_end):
            continue
        if _is_telehealth_encounter(enc):
            continue

        matched = False
        # Check Well Care Visit value set
        if well_care_codes and resource_has_any_code(enc, well_care_codes):
            matched = True
        if not matched and well_care_codes:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, well_care_codes):
                    matched = True
                    break

        # Check Encounter for Well Care value set (exclude lab claims)
        if not matched and encounter_well_care_codes:
            if _is_lab_claim(enc):
                continue
            if resource_has_any_code(enc, encounter_well_care_codes):
                matched = True
            if not matched:
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, encounter_well_care_codes):
                        matched = True
                        break

        if matched:
            evaluated.append(f"Encounter/{enc.get('id')}")
            return True, evaluated

    return False, evaluated


def calculate_wcv_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the WCV measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="WCV",
        measure_name="Child and Adolescent Well-Care Visits",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
