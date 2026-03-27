"""
HEDIS MY 2025 - Statin Therapy for Patients With Diabetes (SPD)

The percentage of members 40-75 years of age during the measurement year with
diabetes who do not have clinical ASCVD who met the following criteria:
  Rate 1: Received at least one statin medication of any intensity during MY.
  Rate 2: Remained on a statin for at least 80% of the treatment period (PDC>=80%).

Eligible population: diabetes identified by claims or pharmacy data during MY or PY.
Members with ASCVD (MI, CABG, PCI, revascularization, IVD) are excluded (they
fall under SPC instead).
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    prior_year_dates,
    get_medication_date,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("SPD")

# All statin medication value set names (high, moderate, and low intensity)
STATIN_VS_NAMES = [
    "Atorvastatin High Intensity Medications",
    "Amlodipine Atorvastatin High Intensity Medications",
    "Rosuvastatin High Intensity Medications",
    "Simvastatin High Intensity Medications",
    "Ezetimibe Simvastatin High Intensity Medications",
    "Atorvastatin Moderate Intensity Medications",
    "Amlodipine Atorvastatin Moderate Intensity Medications",
    "Rosuvastatin Moderate Intensity Medications",
    "Simvastatin Moderate Intensity Medications",
    "Ezetimibe Simvastatin Moderate Intensity Medications",
    "Pravastatin Moderate Intensity Medications",
    "Lovastatin Moderate Intensity Medications",
    "Fluvastatin Moderate Intensity Medications",
    "Pitavastatin Moderate Intensity Medications",
    "Ezetimibe Simvastatin Low Intensity Medications",
    "Fluvastatin Low Intensity Medications",
    "Lovastatin Low Intensity Medications",
    "Pravastatin Low Intensity Medications",
    "Simvastatin Low Intensity Medications",
]


def _get_all_statin_codes() -> dict[str, set[str]]:
    """Combine all statin medication value set codes into one mapping."""
    combined: dict[str, set[str]] = {}
    for vs_name in STATIN_VS_NAMES:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _has_diabetes(bundle: dict, measurement_year: int) -> bool:
    """Identify members with diabetes via claims/encounter data or pharmacy data."""
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, _ = prior_year_dates(measurement_year)
    lookback_start = py_start

    diabetes_codes = all_codes(VALUE_SETS, "Diabetes")
    if not diabetes_codes:
        return False

    conditions = find_conditions_with_codes(
        bundle, diabetes_codes, lookback_start, my_end
    )
    onset_dates = sorted({d for _, d in conditions if d is not None})
    if len(onset_dates) >= 2:
        return True

    if conditions:
        for rtype in ("MedicationDispense", "MedicationRequest"):
            for med in get_resources_by_type(bundle, rtype):
                med_date = get_medication_date(med)
                if med_date and is_date_in_range(med_date, lookback_start, my_end):
                    return True

    return False


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check SPD eligible population:
    - Age 40-75 as of Dec 31 of MY
    - Has diabetes (by claims or pharmacy data)
    - Does NOT have clinical ASCVD (those members belong to SPC)
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (40 <= age <= 75):
        return False, evaluated

    if not _has_diabetes(bundle, measurement_year):
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check SPD exclusions:
    - Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    - ASCVD events in prior year (MI, CABG, PCI, revascularization)
    - IVD diagnosis in both MY and PY
    - Pregnancy, IVF, estrogen agonists during MY or PY
    - ESRD, dialysis, cirrhosis during MY or PY
    - Muscular pain/disease during MY
    - Muscular reactions to statins any time through end of MY
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    # ASCVD events in prior year
    for vs_name in ("MI", "Old Myocardial Infarction"):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes and find_conditions_with_codes(bundle, codes, py_start, py_end):
            return True, refs

    for vs_name in ("CABG", "PCI", "Other Revascularization"):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes and find_procedures_with_codes(bundle, codes, py_start, py_end):
            return True, refs

    # IVD diagnosis in both years
    ivd_codes = all_codes(VALUE_SETS, "IVD")
    if ivd_codes:
        has_my = bool(find_conditions_with_codes(bundle, ivd_codes, my_start, my_end))
        has_py = bool(find_conditions_with_codes(bundle, ivd_codes, py_start, py_end))
        if has_my and has_py:
            return True, refs

    # Pregnancy
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy")
    if pregnancy_codes and find_conditions_with_codes(
        bundle, pregnancy_codes, py_start, my_end
    ):
        return True, refs

    # IVF
    ivf_codes = all_codes(VALUE_SETS, "IVF")
    if ivf_codes and find_procedures_with_codes(bundle, ivf_codes, py_start, my_end):
        return True, refs

    # ESRD
    esrd_codes = all_codes(VALUE_SETS, "ESRD Diagnosis")
    if esrd_codes and find_conditions_with_codes(bundle, esrd_codes, py_start, my_end):
        return True, refs

    # Dialysis
    dialysis_codes = all_codes(VALUE_SETS, "Dialysis Procedure")
    if dialysis_codes and find_procedures_with_codes(
        bundle, dialysis_codes, py_start, my_end
    ):
        return True, refs

    # Cirrhosis
    cirrhosis_codes = all_codes(VALUE_SETS, "Cirrhosis")
    if cirrhosis_codes and find_conditions_with_codes(
        bundle, cirrhosis_codes, py_start, my_end
    ):
        return True, refs

    # Muscular Pain and Disease (MY only)
    muscular_codes = all_codes(VALUE_SETS, "Muscular Pain and Disease")
    if muscular_codes and find_conditions_with_codes(
        bundle, muscular_codes, my_start, my_end
    ):
        return True, refs

    # Muscular Reactions to Statins (any time through end of MY)
    muscular_statin_codes = all_codes(VALUE_SETS, "Muscular Reactions to Statins")
    if muscular_statin_codes:
        far_past = date(1900, 1, 1)
        if find_conditions_with_codes(bundle, muscular_statin_codes, far_past, my_end):
            return True, refs

    return False, refs


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check SPD Rate 1 numerator:
    At least one dispensing event for any intensity statin during MY.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    statin_codes = _get_all_statin_codes()

    if statin_codes:
        meds = find_medications_with_codes(bundle, statin_codes, my_start, my_end)
        if meds:
            for med, _ in meds:
                evaluated.append(f"MedicationDispense/{med.get('id', '')}")
            return True, evaluated

    return False, evaluated


def _check_rate2_numerator(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check SPD Rate 2 numerator: PDC >= 80% during the treatment period.

    Treatment period = IPSD through Dec 31 of MY.
    IPSD = earliest statin dispensing date during MY.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    statin_codes = _get_all_statin_codes()

    if not statin_codes:
        return False, evaluated

    meds = find_medications_with_codes(bundle, statin_codes, my_start, my_end)
    if not meds:
        return False, evaluated

    dispensing_dates = [d for _, d in meds if d is not None]
    if not dispensing_dates:
        return False, evaluated

    ipsd = min(dispensing_dates)
    treatment_days = (my_end - ipsd).days + 1

    if treatment_days <= 0:
        return False, evaluated

    covered_days: set[date] = set()

    for med, med_date in meds:
        if med_date is None:
            continue
        days_supply = (
            med.get("daysSupply", {}).get("value")
            or med.get("quantity", {}).get("value")
            or 30
        )
        if isinstance(days_supply, str):
            try:
                days_supply = int(float(days_supply))
            except (ValueError, TypeError):
                days_supply = 30

        for i in range(int(days_supply)):
            d = med_date + timedelta(days=i)
            if ipsd <= d <= my_end:
                covered_days.add(d)

    pdc = (len(covered_days) / treatment_days) * 100
    pdc_rounded = round(pdc)

    return pdc_rounded >= 80, evaluated


def calculate_spd_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the SPD measure (both rates) for a patient bundle."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    rate1_compliant = False
    rate2_compliant = False
    if is_eligible:
        rate1_compliant, r1_refs = check_numerator(bundle, measurement_year)
        all_evaluated.extend(r1_refs)

        if rate1_compliant:
            rate2_compliant, r2_refs = _check_rate2_numerator(bundle, measurement_year)
            all_evaluated.extend(r2_refs)

    groups = [
        {
            "code": "SPD-Rate1",
            "display": "Received Statin Therapy",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": rate1_compliant,
        },
        {
            "code": "SPD-Rate2",
            "display": "Statin Adherence 80%",
            "initial_population": is_eligible and rate1_compliant,
            "denominator_exclusion": is_excluded,
            "numerator": rate2_compliant,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="SPD",
        measure_name="Statin Therapy for Patients With Diabetes",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
