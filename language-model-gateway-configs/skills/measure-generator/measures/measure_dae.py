"""
HEDIS MY 2025 - Use of High-Risk Medications in Older Adults (DAE).

INVERSE measure (lower = better). Two rates + total:
  Rate 1: At least 2 dispensing events for high-risk medications from same drug class.
  Rate 2: At least 2 dispensing events for high-risk meds except for appropriate diagnosis
          (antipsychotics without schizophrenia/bipolar, benzos without seizure/REM/withdrawal/GAD).
  Total: Deduplicated union of Rate 1 and Rate 2.

Members 67+ (Medicare).
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
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("DAE")

# High-risk medication value set names for Rate 1
_RATE1_MED_VS_NAMES = [
    "Potentially Harmful Antihistamines for Older Adults Medications",
    "Potentially Harmful Antiparkinsonian Agents for Older Adults Medications",
    "Potentially Harmful Gastrointestinal Antispasmodics for Older Adults Medications",
    "Dipyridamole Medications",
    "Guanfacine Medications",
    "Nifedipine Medications",
    "Potentially Harmful Antidepressants for Older Adults Medications",
    "Potentially Harmful Barbiturates for Older Adults Medications",
    "Ergoloid Mesylates Medications",
    "Meprobamate Medications",
    "Potentially Harmful Estrogens for Older Adults Medications",
    "Potentially Harmful Sulfonylureas for Older Adults Medications",
    "Desiccated Thyroid Medications",
    "Megestrol Medications",
    "Potentially Harmful Nonbenzodiazepine Hypnotics for Older Adults Medications",
    "Potentially Harmful Skeletal Muscle Relaxants for Older Adults Medications",
    "Meperidine Combinations Medications",
    "Potentially Harmful Pain Medications for Older Adults Medications",
    "Potentially Harmful Antiinfectives for Older Adults Medications",
]


def _check_age(bundle: dict, measurement_year: int) -> bool:
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False
    _, my_end = measurement_year_dates(measurement_year)
    return calculate_age(birth_date, my_end) >= 67


def _get_dispensing_dates_for_vs(
    bundle: dict, vs_codes: dict[str, set[str]], my_start: date, my_end: date
) -> list[date]:
    """Get unique dispensing dates for a medication value set."""
    dates: list[date] = []
    meds = find_medications_with_codes(bundle, vs_codes, my_start, my_end)
    for m, d in meds:
        if d:
            dates.append(d)
    return dates


def _has_two_dispensing_events(dates: list[date]) -> bool:
    """Check if there are at least 2 dispensing events on different dates."""
    return len(set(dates)) >= 2


def _check_rate1_numerator(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Rate 1: 2+ dispensing events for high-risk meds from same drug class."""
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)

    for vs_name in _RATE1_MED_VS_NAMES:
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if not vs_codes:
            continue
        dates = _get_dispensing_dates_for_vs(bundle, vs_codes, my_start, my_end)
        if _has_two_dispensing_events(dates):
            meds = find_medications_with_codes(bundle, vs_codes, my_start, my_end)
            evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in meds)
            return True, evaluated

    return False, evaluated


def _check_rate2_numerator(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Rate 2: High-risk meds except for appropriate diagnosis.

    Antipsychotics without schizophrenia/bipolar.
    Benzodiazepines without seizure/REM sleep/benzo withdrawal/alcohol withdrawal/GAD.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    py_start = date(measurement_year - 1, 1, 1)

    # Antipsychotics
    antipsych_codes = all_codes(
        VALUE_SETS, "Potentially Harmful Antipsychotics for Older Adults Medications"
    )
    if antipsych_codes:
        dates = _get_dispensing_dates_for_vs(bundle, antipsych_codes, my_start, my_end)
        if _has_two_dispensing_events(dates):
            # Check for appropriate diagnosis (schizophrenia, bipolar)
            ipsd = min(set(dates))
            has_appropriate = False
            for vs_name in (
                "Schizophrenia",
                "Bipolar Disorder",
                "Other Bipolar Disorder",
            ):
                dx_codes = all_codes(VALUE_SETS, vs_name)
                if dx_codes and find_conditions_with_codes(
                    bundle, dx_codes, py_start, ipsd
                ):
                    has_appropriate = True
                    break
            if not has_appropriate:
                meds = find_medications_with_codes(
                    bundle, antipsych_codes, my_start, my_end
                )
                evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in meds)
                return True, evaluated

    # Benzodiazepines
    benzo_codes = all_codes(
        VALUE_SETS, "Potentially Harmful Benzodiazepines for Older Adults Medications"
    )
    if benzo_codes:
        dates = _get_dispensing_dates_for_vs(bundle, benzo_codes, my_start, my_end)
        if _has_two_dispensing_events(dates):
            ipsd = min(set(dates))
            has_appropriate = False
            for vs_name in (
                "Seizure Disorders",
                "REM Sleep Behavior Disorder",
                "Benzodiazepine Withdrawal",
                "Alcohol Withdrawal",
                "Generalized Anxiety Disorder",
            ):
                dx_codes = all_codes(VALUE_SETS, vs_name)
                if dx_codes and find_conditions_with_codes(
                    bundle, dx_codes, py_start, ipsd
                ):
                    has_appropriate = True
                    break
            if not has_appropriate:
                meds = find_medications_with_codes(
                    bundle, benzo_codes, my_start, my_end
                )
                evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in meds)
                return True, evaluated

    return False, evaluated


def calculate_dae_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate DAE measure and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    if not _check_age(bundle, measurement_year):
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="DAE",
            measure_name="Use of High-Risk Medications in Older Adults",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "DAE-1",
                    "display": "High Risk Medications to Avoid",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "DAE-2",
                    "display": "High Risk Medications Except Appropriate Diagnosis",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    # Common exclusions (hospice, death, palliative care)
    common_excl, common_refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(common_refs)

    # Rate 1
    r1_num = False
    if not common_excl:
        r1_num, r1_refs = _check_rate1_numerator(bundle, measurement_year)
        all_evaluated.extend(r1_refs)

    # Rate 2
    r2_num = False
    if not common_excl:
        r2_num, r2_refs = _check_rate2_numerator(bundle, measurement_year)
        all_evaluated.extend(r2_refs)

    groups = [
        {
            "code": "DAE-1",
            "display": "High Risk Medications to Avoid",
            "initial_population": True,
            "denominator_exclusion": common_excl,
            "numerator": r1_num,
        },
        {
            "code": "DAE-2",
            "display": "High Risk Medications Except Appropriate Diagnosis",
            "initial_population": True,
            "denominator_exclusion": common_excl,
            "numerator": r2_num,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="DAE",
        measure_name="Use of High-Risk Medications in Older Adults",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
