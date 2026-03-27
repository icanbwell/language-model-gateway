"""
HEDIS MY 2025 - Potentially Harmful Drug-Disease Interactions in Older Adults (DDE).

Three rates (INVERSE - lower = better):
  1. History of Falls + anticholinergics/antiepileptics/antipsychotics/benzos/hypnotics/antidepressants
  2. Dementia + antipsychotics/benzos/hypnotics/tricyclics/anticholinergics
  3. CKD + Cox-2 selective NSAIDs or nonaspirin NSAIDs

Members 67+ with a disease/condition who received a potentially harmful medication.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    calculate_age,
    measurement_year_dates,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("DDE")


def _lookback_dates(measurement_year: int) -> tuple[date, date]:
    """Jan 1 of year prior through Dec 1 of measurement year."""
    return date(measurement_year - 1, 1, 1), date(measurement_year, 12, 1)


def _check_age(bundle: dict, measurement_year: int) -> bool:
    """Check age >= 67 as of Dec 31 MY."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False
    _, my_end = measurement_year_dates(measurement_year)
    return calculate_age(birth_date, my_end) >= 67


def _check_rate1_eligible(
    bundle: dict, measurement_year: int
) -> tuple[bool, date | None, list[str]]:
    """Rate 1: History of falls or hip fracture.

    Returns (eligible, iesd, evaluated_refs).
    """
    evaluated: list[str] = []
    lb_start, lb_end = _lookback_dates(measurement_year)

    # Falls
    falls_codes = all_codes(VALUE_SETS, "Falls")
    if falls_codes:
        matches = find_conditions_with_codes(bundle, falls_codes, lb_start, lb_end)
        if matches:
            earliest = min(d for _, d in matches if d)
            evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, earliest, evaluated

    # Hip fractures with qualifying encounter
    hip_codes = all_codes(VALUE_SETS, "Hip Fractures")
    visit_codes = all_codes(
        VALUE_SETS, "Outpatient, ED, Acute Inpatient and Nonacute Inpatient"
    )
    if hip_codes:
        matches = find_conditions_with_codes(bundle, hip_codes, lb_start, lb_end)
        if matches:
            earliest = min(d for _, d in matches if d)
            evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, earliest, evaluated

    return False, None, evaluated


def _check_rate1_exclusion(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Rate 1 exclusion: psychosis, schizophrenia, bipolar, MDD, seizure."""
    evaluated: list[str] = []
    lb_start, lb_end = _lookback_dates(measurement_year)

    for vs_name in (
        "Psychosis",
        "Schizophrenia",
        "Bipolar Disorder",
        "Other Bipolar Disorder",
        "Major Depression or Dysthymia",
        "Seizure Disorders",
    ):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes:
            matches = find_conditions_with_codes(bundle, codes, lb_start, lb_end)
            if matches:
                evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
                return True, evaluated

    return False, evaluated


def _check_rate2_eligible(
    bundle: dict, measurement_year: int
) -> tuple[bool, date | None, list[str]]:
    """Rate 2: Dementia diagnosis or dementia medication."""
    evaluated: list[str] = []
    lb_start, lb_end = _lookback_dates(measurement_year)

    dementia_codes = all_codes(VALUE_SETS, "Dementia")
    if dementia_codes:
        matches = find_conditions_with_codes(bundle, dementia_codes, lb_start, lb_end)
        if matches:
            earliest = min(d for _, d in matches if d)
            evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
            return True, earliest, evaluated

    # Dementia medications
    dem_med_codes = all_codes(VALUE_SETS, "Dementia Medications")
    if dem_med_codes:
        matches = find_medications_with_codes(bundle, dem_med_codes, lb_start, lb_end)
        if matches:
            earliest = min(d for _, d in matches if d)
            evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in matches)
            return True, earliest, evaluated

    return False, None, evaluated


def _check_rate2_exclusion(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Rate 2 exclusion: psychosis, schizophrenia, bipolar."""
    evaluated: list[str] = []
    lb_start, lb_end = _lookback_dates(measurement_year)

    for vs_name in (
        "Psychosis",
        "Schizophrenia",
        "Bipolar Disorder",
        "Other Bipolar Disorder",
    ):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes:
            matches = find_conditions_with_codes(bundle, codes, lb_start, lb_end)
            if matches:
                evaluated.extend(f"Condition/{c.get('id')}" for c, _ in matches)
                return True, evaluated

    return False, evaluated


def _check_rate3_eligible(
    bundle: dict, measurement_year: int
) -> tuple[bool, date | None, list[str]]:
    """Rate 3: Chronic kidney disease (ESRD, CKD Stage 4, dialysis, etc.)."""
    evaluated: list[str] = []
    lb_start, lb_end = _lookback_dates(measurement_year)

    for vs_name in (
        "ESRD Diagnosis",
        "CKD Stage 4",
        "Dialysis Procedure",
        "Total Nephrectomy",
        "Kidney Transplant",
    ):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes:
            cond_matches = find_conditions_with_codes(bundle, codes, lb_start, lb_end)
            if cond_matches:
                earliest = min(d for _, d in cond_matches if d)
                evaluated.extend(f"Condition/{c.get('id')}" for c, _ in cond_matches)
                return True, earliest, evaluated
            proc_matches = find_procedures_with_codes(bundle, codes, lb_start, lb_end)
            if proc_matches:
                earliest = min(d for _, d in proc_matches if d)
                evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
                return True, earliest, evaluated

    return False, None, evaluated


def calculate_dde_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate DDE measure (3 rates) and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []
    _, my_end = measurement_year_dates(measurement_year)

    if not _check_age(bundle, measurement_year):
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="DDE",
            measure_name="Potentially Harmful Drug-Disease Interactions in Older Adults",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "DDE-1",
                    "display": "History of Falls",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "DDE-2",
                    "display": "Dementia",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "DDE-3",
                    "display": "Chronic Kidney Disease",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    # Common exclusions
    common_excl, common_refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(common_refs)

    groups: list[dict] = []

    # Rate 1: History of Falls
    r1_elig, r1_iesd, r1_refs = _check_rate1_eligible(bundle, measurement_year)
    all_evaluated.extend(r1_refs)
    r1_excl = common_excl
    r1_num = False
    if r1_elig and not common_excl:
        excl, excl_refs = _check_rate1_exclusion(bundle, measurement_year)
        all_evaluated.extend(excl_refs)
        r1_excl = excl
        if not excl and r1_iesd:
            falls_med_codes = all_codes(
                VALUE_SETS,
                "Potentially Harmful Drugs for Older Adults With a History of Falls Medications",
            )
            if falls_med_codes:
                meds = find_medications_with_codes(
                    bundle, falls_med_codes, r1_iesd, my_end
                )
                if meds:
                    all_evaluated.extend(
                        f"MedicationDispense/{m.get('id')}" for m, _ in meds
                    )
                    r1_num = True
    groups.append(
        {
            "code": "DDE-1",
            "display": "History of Falls",
            "initial_population": r1_elig,
            "denominator_exclusion": r1_excl if r1_elig else False,
            "numerator": r1_num,
        }
    )

    # Rate 2: Dementia
    r2_elig, r2_iesd, r2_refs = _check_rate2_eligible(bundle, measurement_year)
    all_evaluated.extend(r2_refs)
    r2_excl = common_excl
    r2_num = False
    if r2_elig and not common_excl:
        excl, excl_refs = _check_rate2_exclusion(bundle, measurement_year)
        all_evaluated.extend(excl_refs)
        r2_excl = excl
        if not excl and r2_iesd:
            dem_med_codes = all_codes(
                VALUE_SETS,
                "Potentially Harmful Drugs for Older Adults With a History of Dementia Medications",
            )
            if dem_med_codes:
                meds = find_medications_with_codes(
                    bundle, dem_med_codes, r2_iesd, my_end
                )
                if meds:
                    all_evaluated.extend(
                        f"MedicationDispense/{m.get('id')}" for m, _ in meds
                    )
                    r2_num = True
    groups.append(
        {
            "code": "DDE-2",
            "display": "Dementia",
            "initial_population": r2_elig,
            "denominator_exclusion": r2_excl if r2_elig else False,
            "numerator": r2_num,
        }
    )

    # Rate 3: Chronic Kidney Disease
    r3_elig, r3_iesd, r3_refs = _check_rate3_eligible(bundle, measurement_year)
    all_evaluated.extend(r3_refs)
    r3_excl = common_excl
    r3_num = False
    if r3_elig and not common_excl and r3_iesd:
        ckd_med_codes = all_codes(
            VALUE_SETS,
            "Potentially Harmful Drugs for Older Adults With a History of Chronic Kidney Disease Medications",
        )
        if ckd_med_codes:
            meds = find_medications_with_codes(bundle, ckd_med_codes, r3_iesd, my_end)
            if meds:
                all_evaluated.extend(
                    f"MedicationDispense/{m.get('id')}" for m, _ in meds
                )
                r3_num = True
    groups.append(
        {
            "code": "DDE-3",
            "display": "Chronic Kidney Disease",
            "initial_population": r3_elig,
            "denominator_exclusion": r3_excl if r3_elig else False,
            "numerator": r3_num,
        }
    )

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="DDE",
        measure_name="Potentially Harmful Drug-Disease Interactions in Older Adults",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
