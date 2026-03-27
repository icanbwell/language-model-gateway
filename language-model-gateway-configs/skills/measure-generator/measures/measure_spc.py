"""
HEDIS MY 2025 - Statin Therapy for Patients With Cardiovascular Disease (SPC)

The percentage of males 21-75 and females 40-75 who were identified as having
clinical ASCVD and met the following criteria:
  Rate 1: Received at least one high- or moderate-intensity statin during MY.
  Rate 2: Remained on a statin for at least 80% of the treatment period (PDC>=80%).

Eligible population identified by event (MI, CABG, PCI, revascularization in prior
year) OR diagnosis (IVD in both MY and prior year).
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_patient_gender,
    calculate_age,
    measurement_year_dates,
    prior_year_dates,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("SPC")

# All statin medication value set names (high and moderate intensity)
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
]


def _get_all_statin_codes() -> dict[str, set[str]]:
    """Combine all statin medication value set codes into one mapping."""
    combined: dict[str, set[str]] = {}
    for vs_name in STATIN_VS_NAMES:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _has_ascvd_event_prior_year(bundle: dict, measurement_year: int) -> bool:
    """Check for MI, CABG, PCI or other revascularization in the prior year."""
    py_start, py_end = prior_year_dates(measurement_year)

    for vs_name in ("MI", "Old Myocardial Infarction"):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes and find_conditions_with_codes(bundle, codes, py_start, py_end):
            return True

    for vs_name in ("CABG", "PCI", "Other Revascularization"):
        codes = all_codes(VALUE_SETS, vs_name)
        if codes and find_procedures_with_codes(bundle, codes, py_start, py_end):
            return True

    return False


def _has_ivd_diagnosis_both_years(bundle: dict, measurement_year: int) -> bool:
    """Check for IVD diagnosis in both MY and prior year with qualifying encounters."""
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)

    ivd_codes = all_codes(VALUE_SETS, "IVD")
    encounter_codes = all_codes(
        VALUE_SETS, "Outpatient, Telehealth and Acute Inpatient"
    )

    if not ivd_codes:
        return False

    has_my = bool(find_conditions_with_codes(bundle, ivd_codes, my_start, my_end))
    has_py = bool(find_conditions_with_codes(bundle, ivd_codes, py_start, py_end))

    return has_my and has_py


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check SPC eligible population:
    - Males 21-75 or females 40-75 as of Dec 31 MY
    - Identified as having ASCVD by event or diagnosis
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    gender = get_patient_gender(bundle)
    if not birth_date or not gender:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)

    if gender == "male" and not (21 <= age <= 75):
        return False, evaluated
    if gender == "female" and not (40 <= age <= 75):
        return False, evaluated
    if gender not in ("male", "female"):
        return False, evaluated

    # Check event-based or diagnosis-based identification
    if _has_ascvd_event_prior_year(bundle, measurement_year):
        return True, evaluated
    if _has_ivd_diagnosis_both_years(bundle, measurement_year):
        return True, evaluated

    return False, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check SPC exclusions:
    - Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    - Pregnancy during MY or prior year
    - IVF during MY or prior year
    - Estrogen agonists (clomiphene) during MY or prior year
    - ESRD during MY or prior year
    - Dialysis during MY or prior year
    - Cirrhosis during MY or prior year
    - Muscular pain/disease during MY
    - Muscular reactions to statins any time through end of MY
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    my_start, my_end = measurement_year_dates(measurement_year)
    py_start, py_end = prior_year_dates(measurement_year)
    lookback_start = py_start

    # Pregnancy
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy")
    if pregnancy_codes and find_conditions_with_codes(
        bundle, pregnancy_codes, lookback_start, my_end
    ):
        return True, refs

    # IVF
    ivf_codes = all_codes(VALUE_SETS, "IVF")
    if ivf_codes and find_procedures_with_codes(
        bundle, ivf_codes, lookback_start, my_end
    ):
        return True, refs

    # ESRD
    esrd_codes = all_codes(VALUE_SETS, "ESRD Diagnosis")
    if esrd_codes and find_conditions_with_codes(
        bundle, esrd_codes, lookback_start, my_end
    ):
        return True, refs

    # Dialysis
    dialysis_codes = all_codes(VALUE_SETS, "Dialysis Procedure")
    if dialysis_codes and find_procedures_with_codes(
        bundle, dialysis_codes, lookback_start, my_end
    ):
        return True, refs

    # Cirrhosis
    cirrhosis_codes = all_codes(VALUE_SETS, "Cirrhosis")
    if cirrhosis_codes and find_conditions_with_codes(
        bundle, cirrhosis_codes, lookback_start, my_end
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
    Check SPC Rate 1 numerator:
    At least one dispensing event for a high- or moderate-intensity statin during MY.
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
    Check SPC Rate 2 numerator: PDC >= 80% during the treatment period.

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

    # Find IPSD (earliest dispensing date)
    dispensing_dates = [d for _, d in meds if d is not None]
    if not dispensing_dates:
        return False, evaluated

    ipsd = min(dispensing_dates)
    treatment_days = (my_end - ipsd).days + 1

    if treatment_days <= 0:
        return False, evaluated

    # Count covered days (simplified: sum days supply, cap at MY end)
    covered_days: set[date] = set()
    from datetime import timedelta

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


def calculate_spc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the SPC measure (both rates) for a patient bundle."""
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
            "code": "SPC-Rate1",
            "display": "Received Statin Therapy",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": rate1_compliant,
        },
        {
            "code": "SPC-Rate2",
            "display": "Statin Adherence 80%",
            "initial_population": is_eligible and rate1_compliant,
            "denominator_exclusion": is_excluded,
            "numerator": rate2_compliant,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="SPC",
        measure_name="Statin Therapy for Patients With Cardiovascular Disease",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
