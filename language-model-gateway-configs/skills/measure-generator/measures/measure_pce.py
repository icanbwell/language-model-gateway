"""
HEDIS MY 2025 - Pharmacotherapy Management of COPD Exacerbation (PCE).

The percentage of COPD exacerbations for members 40 years of age and older
who had an acute inpatient discharge or ED visit on or between January 1 -
November 30 of the measurement year and who were dispensed appropriate
medications. Two rates are reported:

1. Dispensed a Systemic Corticosteroid (or active prescription) within
   14 days of the event.
2. Dispensed a Bronchodilator (or active prescription) within 30 days
   of the event.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    parse_date,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    find_encounters_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("PCE")


def _get_intake_period(measurement_year: int) -> tuple[date, date]:
    """Intake period: January 1 to November 30 of the measurement year."""
    return date(measurement_year, 1, 1), date(measurement_year, 11, 30)


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: 40 years or older as of Jan 1 of the measurement year with a
    COPD exacerbation (acute inpatient discharge or ED visit with principal
    diagnosis of COPD) during the intake period (Jan 1 - Nov 30).
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_jan1 = date(measurement_year, 1, 1)
    age = calculate_age(birth_date, my_jan1)
    if age < 40:
        return False, evaluated

    intake_start, intake_end = _get_intake_period(measurement_year)
    copd_codes = all_codes(VALUE_SETS, "Chronic Obstructive Pulmonary Diseases")
    if not copd_codes:
        return False, evaluated

    # Find ED visits with COPD diagnosis
    ed_codes = all_codes(VALUE_SETS, "ED")
    if ed_codes:
        ed_visits = find_encounters_with_codes(
            bundle, ed_codes, intake_start, intake_end
        )
        for enc, enc_date in ed_visits:
            if resource_has_any_code(enc, copd_codes):
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, copd_codes):
                    evaluated.append(f"Encounter/{enc.get('id')}")
                    return True, evaluated

    # Find acute inpatient discharges with COPD diagnosis
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")
    if inpatient_codes:
        inpatient_visits = find_encounters_with_codes(
            bundle, inpatient_codes, intake_start, intake_end
        )
        for enc, _ in inpatient_visits:
            # Exclude nonacute
            if nonacute_codes and resource_has_any_code(enc, nonacute_codes):
                continue
            # Check COPD diagnosis
            if resource_has_any_code(enc, copd_codes):
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, copd_codes):
                    evaluated.append(f"Encounter/{enc.get('id')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions: hospice, death.
    """
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


# ---------------------------------------------------------------------------
# Numerator helpers
# ---------------------------------------------------------------------------


def _find_episode_date(bundle: dict, measurement_year: int) -> date | None:
    """Find the COPD episode date (discharge date for inpatient, service date for ED)."""
    intake_start, intake_end = _get_intake_period(measurement_year)
    copd_codes = all_codes(VALUE_SETS, "Chronic Obstructive Pulmonary Diseases")
    if not copd_codes:
        return None

    # Check ED visits
    ed_codes = all_codes(VALUE_SETS, "ED")
    if ed_codes:
        ed_visits = find_encounters_with_codes(
            bundle, ed_codes, intake_start, intake_end
        )
        for enc, enc_date in ed_visits:
            has_copd = resource_has_any_code(enc, copd_codes)
            if not has_copd:
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, copd_codes):
                        has_copd = True
                        break
            if has_copd:
                return enc_date

    # Check acute inpatient discharges
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")
    if inpatient_codes:
        inpatient_visits = find_encounters_with_codes(
            bundle, inpatient_codes, intake_start, intake_end
        )
        for enc, _ in inpatient_visits:
            if nonacute_codes and resource_has_any_code(enc, nonacute_codes):
                continue
            has_copd = resource_has_any_code(enc, copd_codes)
            if not has_copd:
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, copd_codes):
                        has_copd = True
                        break
            if has_copd:
                # Use discharge date for inpatient
                discharge = get_encounter_end_date(enc) or get_encounter_date(enc)
                return discharge

    return None


def _check_systemic_corticosteroid(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Dispensed systemic corticosteroid on or within 14 days of episode date.
    Systemic corticosteroid medications are in [Direct Reference] or specific
    value sets loaded from the CSV.
    """
    evaluated: list[str] = []
    episode_date = _find_episode_date(bundle, measurement_year)
    if not episode_date:
        return False, evaluated

    window_end = episode_date + timedelta(days=14)

    # Check for corticosteroid medications - these may be under various
    # value set names or [Direct Reference] in the CSV
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = parse_date(med.get("whenHandedOver") or med.get("authoredOn"))
            if not med_date or not is_date_in_range(med_date, episode_date, window_end):
                continue
            # Check medication code against known corticosteroid generic names
            mcc = med.get("medicationCodeableConcept", {})
            display = mcc.get("text", "").lower()
            for coding in mcc.get("coding", []):
                disp = (coding.get("display") or "").lower()
                if any(
                    name in disp or name in display
                    for name in (
                        "cortisone",
                        "dexamethasone",
                        "hydrocortisone",
                        "methylprednisolone",
                        "prednisolone",
                        "prednisone",
                    )
                ):
                    evaluated.append(f"{rtype}/{med.get('id')}")
                    return True, evaluated

    # Also check [Direct Reference] codes if available
    direct_codes = all_codes(VALUE_SETS, "[Direct Reference]")
    if direct_codes:
        meds = find_medications_with_codes(
            bundle, direct_codes, episode_date, window_end
        )
        if meds:
            for med, _ in meds:
                rtype = med.get("resourceType", "MedicationDispense")
                evaluated.append(f"{rtype}/{med.get('id')}")
            return True, evaluated

    return False, evaluated


def _check_bronchodilator(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Dispensed bronchodilator on or within 30 days of episode date.
    """
    evaluated: list[str] = []
    episode_date = _find_episode_date(bundle, measurement_year)
    if not episode_date:
        return False, evaluated

    window_end = episode_date + timedelta(days=30)

    # Check medication resources for bronchodilator names
    bronchodilator_names = (
        "aclidinium",
        "ipratropium",
        "tiotropium",
        "umeclidinium",
        "albuterol",
        "arformoterol",
        "formoterol",
        "indacaterol",
        "levalbuterol",
        "metaproterenol",
        "olodaterol",
        "salmeterol",
        "budesonide-formoterol",
        "fluticasone-salmeterol",
        "fluticasone-vilanterol",
    )

    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = parse_date(med.get("whenHandedOver") or med.get("authoredOn"))
            if not med_date or not is_date_in_range(med_date, episode_date, window_end):
                continue
            mcc = med.get("medicationCodeableConcept", {})
            display = mcc.get("text", "").lower()
            for coding in mcc.get("coding", []):
                disp = (coding.get("display") or "").lower()
                if any(
                    name in disp or name in display for name in bronchodilator_names
                ):
                    evaluated.append(f"{rtype}/{med.get('id')}")
                    return True, evaluated

    # Also check [Direct Reference] codes
    direct_codes = all_codes(VALUE_SETS, "[Direct Reference]")
    if direct_codes:
        meds = find_medications_with_codes(
            bundle, direct_codes, episode_date, window_end
        )
        if meds:
            for med, _ in meds:
                rtype = med.get("resourceType", "MedicationDispense")
                evaluated.append(f"{rtype}/{med.get('id')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_pce_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate the PCE measure for an individual patient.

    Returns a FHIR MeasureReport with two rate groups:
    Systemic Corticosteroid and Bronchodilator.
    """
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    if not is_eligible:
        groups = [
            {
                "code": "PCE-Corticosteroid",
                "display": "Systemic Corticosteroid",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
            {
                "code": "PCE-Bronchodilator",
                "display": "Bronchodilator",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            },
        ]
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="PCE",
            measure_name="Pharmacotherapy Management of COPD Exacerbation",
            measurement_year=measurement_year,
            groups=groups,
            evaluated_resources=all_evaluated,
        )

    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(exclusion_refs)

    cortico_met, cortico_refs = _check_systemic_corticosteroid(bundle, measurement_year)
    all_evaluated.extend(cortico_refs)

    broncho_met, broncho_refs = _check_bronchodilator(bundle, measurement_year)
    all_evaluated.extend(broncho_refs)

    groups = [
        {
            "code": "PCE-Corticosteroid",
            "display": "Systemic Corticosteroid",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": cortico_met,
        },
        {
            "code": "PCE-Bronchodilator",
            "display": "Bronchodilator",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": broncho_met,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="PCE",
        measure_name="Pharmacotherapy Management of COPD Exacerbation",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
