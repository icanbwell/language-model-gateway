"""
HEDIS MY 2025 - Asthma Medication Ratio (AMR).

The percentage of members 5-64 years of age who were identified as having
persistent asthma and had a ratio of controller medications to total asthma
medications of 0.50 or greater during the measurement year.

This is a medication ratio measure. The numerator is based on the ratio of
controller medication units to total asthma medication units >= 0.50.
"""

from datetime import date

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
    get_medication_date,
    medication_has_code,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("AMR")

# Controller medication value set names (from the spec's Asthma Controller
# Medications table). These map to medication list names in the CSV.
_CONTROLLER_MED_LIST_NAMES = (
    "Omalizumab Medications List",
    "Dupilumab Medications List",
    "Benralizumab Medications List",
    "Mepolizumab Medications List",
    "Reslizumab Medications List",
    "Budesonide Formoterol Medications List",
    "Fluticasone Salmeterol Medications List",
    "Fluticasone Vilanterol Medications List",
    "Formoterol Mometasone Medications List",
    "Beclomethasone Medications List",
    "Budesonide Medications List",
    "Ciclesonide Medications List",
    "Flunisolide Medications List",
    "Fluticasone Medications List",
    "Mometasone Medications List",
    "Montelukast Medications List",
    "Zafirlukast Medications List",
    "Zileuton Medications List",
    "Fluticasone Furoate Umeclidinium Vilanterol Medications List",
    "Salmeterol Medications List",
    "Tiotropium Medications List",
    "Theophylline Medications List",
)

# Reliever medication value set names
_RELIEVER_MED_LIST_NAMES = (
    "Albuterol Budesonide Medications List",
    "Albuterol Medications List",
    "Levalbuterol Medications List",
)


def _count_medication_units(
    bundle: dict,
    med_list_names: tuple[str, ...],
    start: date,
    end: date,
) -> tuple[int, list[str]]:
    """
    Count medication units for the given medication list names in date range.

    Each dispensing event counts as one unit (simplified; in full implementation
    would account for days supply, package size, etc.).
    """
    total_units = 0
    evaluated: list[str] = []

    for vs_name in med_list_names:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        meds = find_medications_with_codes(bundle, vs_codes, start, end)
        for med, _ in meds:
            total_units += 1
            rtype = med.get("resourceType", "MedicationDispense")
            evaluated.append(f"{rtype}/{med.get('id')}")

    # Also check [Direct Reference] codes grouped by medication
    # (These contain NDC codes that map to specific medications)
    direct_codes = all_codes(VALUE_SETS, "[Direct Reference]")
    if direct_codes:
        for rtype_name in ("MedicationDispense", "MedicationRequest"):
            for med in get_resources_by_type(bundle, rtype_name):
                med_date = get_medication_date(med)
                if not med_date or not is_date_in_range(med_date, start, end):
                    continue
                if medication_has_code(med, direct_codes):
                    total_units += 1
                    evaluated.append(f"{rtype_name}/{med.get('id')}")

    return total_units, evaluated


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible: 5-64 years as of Dec 31, with persistent asthma identified
    in both the measurement year and the year prior.

    Persistent asthma criteria (must be met in BOTH years):
    - At least 1 ED/acute inpatient with principal asthma diagnosis, OR
    - At least 4 outpatient visits with any asthma diagnosis AND 2+ asthma
      medication dispensing events, OR
    - At least 4 asthma medication dispensing events.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 5 or age > 64:
        return False, evaluated

    asthma_codes = all_codes(VALUE_SETS, "Asthma")
    if not asthma_codes:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    for year_start, year_end in [(my_start, my_end), (py_start, py_end)]:
        year_met = False

        # Criterion 1: ED/acute inpatient with asthma diagnosis
        ed_acute_codes = all_codes(VALUE_SETS, "ED and Acute Inpatient")
        if ed_acute_codes:
            hits = find_encounters_with_codes(
                bundle, ed_acute_codes, year_start, year_end
            )
            for enc, _ in hits:
                if resource_has_any_code(enc, asthma_codes):
                    year_met = True
                    evaluated.append(f"Encounter/{enc.get('id')}")
                    break
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, asthma_codes):
                        year_met = True
                        evaluated.append(f"Encounter/{enc.get('id')}")
                        break
                if year_met:
                    break

        # Criterion 2/3: outpatient visits with asthma + meds, or 4+ meds
        if not year_met:
            all_med_names = _CONTROLLER_MED_LIST_NAMES + _RELIEVER_MED_LIST_NAMES
            med_count, _ = _count_medication_units(
                bundle, all_med_names, year_start, year_end
            )
            if med_count >= 4:
                year_met = True
            elif med_count >= 2:
                # Check for 4+ outpatient visits with asthma diagnosis
                outpatient_codes = all_codes(VALUE_SETS, "Outpatient and Telehealth")
                if outpatient_codes:
                    outpatient_hits = find_encounters_with_codes(
                        bundle, outpatient_codes, year_start, year_end
                    )
                    asthma_visit_dates: set[date] = set()
                    for enc, enc_date in outpatient_hits:
                        has_asthma = resource_has_any_code(enc, asthma_codes)
                        if not has_asthma:
                            for t in enc.get("type", []):
                                if codeable_concept_has_any_code(t, asthma_codes):
                                    has_asthma = True
                                    break
                        if has_asthma and enc_date:
                            asthma_visit_dates.add(enc_date)
                    if len(asthma_visit_dates) >= 4:
                        year_met = True

        if not year_met:
            return False, evaluated

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions:
    - Respiratory diseases with different treatment approaches than asthma
      any time through Dec 31 of the measurement year.
    - No asthma controller or reliever medications dispensed during the
      measurement year.
    - Hospice, death.
    """
    evaluated: list[str] = []

    # Respiratory diseases exclusion (any time through end of MY)
    resp_codes = all_codes(
        VALUE_SETS,
        "Respiratory Diseases With Different Treatment Approaches Than Asthma",
    )
    if resp_codes:
        # Look through entire history up to end of measurement year
        _, my_end = measurement_year_dates(measurement_year)
        resp_hits = find_conditions_with_codes(bundle, resp_codes)
        for cond, onset in resp_hits:
            if onset is None or onset <= my_end:
                evaluated.append(f"Condition/{cond.get('id')}")
                return True, evaluated

    # No controller or reliever meds during measurement year
    my_start, my_end = measurement_year_dates(measurement_year)
    all_med_names = _CONTROLLER_MED_LIST_NAMES + _RELIEVER_MED_LIST_NAMES
    med_count, _ = _count_medication_units(bundle, all_med_names, my_start, my_end)
    if med_count == 0:
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
    Medication ratio >= 0.50.

    Ratio = controller medication units / total asthma medication units.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    controller_units, ctrl_refs = _count_medication_units(
        bundle, _CONTROLLER_MED_LIST_NAMES, my_start, my_end
    )
    evaluated.extend(ctrl_refs)

    reliever_units, rel_refs = _count_medication_units(
        bundle, _RELIEVER_MED_LIST_NAMES, my_start, my_end
    )
    evaluated.extend(rel_refs)

    total_units = controller_units + reliever_units
    if total_units == 0:
        return False, evaluated

    ratio = controller_units / total_units
    if ratio >= 0.50:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_amr_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the AMR measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="AMR",
        measure_name="Asthma Medication Ratio",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
