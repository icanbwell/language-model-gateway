"""
HEDIS MY 2025 - Immunizations for Adolescents (IMA-E)

The percentage of adolescents 13 years of age who had one dose of
meningococcal vaccine, one Tdap vaccine, and completed the HPV vaccine
series by their 13th birthday.

Calculates a rate for each vaccine and two combination rates
(Combo 1: Meningococcal + Tdap, Combo 2: all three).
"""

from __future__ import annotations

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    parse_date,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    find_conditions_with_codes,
    find_procedures_with_codes,
    build_multi_rate_measure_report,
    all_codes,
    SNOMED,
    CVX,
)

VALUE_SETS = load_value_sets_from_csv("IMA-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_immunization_dates(
    bundle: dict,
    imm_vs_name: str,
    proc_vs_name: str,
    start: date,
    end: date,
) -> list[date]:
    """Collect unique vaccination dates from Immunization and Procedure resources."""
    dates: set[date] = set()
    imm_codes = all_codes(VALUE_SETS, imm_vs_name)
    proc_codes = all_codes(VALUE_SETS, proc_vs_name)

    for imm in get_resources_by_type(bundle, "Immunization"):
        occ = parse_date(imm.get("occurrenceDateTime"))
        if not occ or not is_date_in_range(occ, start, end):
            continue
        if resource_has_any_code(imm, imm_codes):
            dates.add(occ)
        vc = imm.get("vaccineCode", {})
        if codeable_concept_has_any_code(vc, imm_codes):
            dates.add(occ)

    for proc, proc_date in find_procedures_with_codes(bundle, proc_codes, start, end):
        if proc_date:
            dates.add(proc_date)

    return sorted(dates)


def _has_anaphylaxis(bundle: dict, snomed_code: str, by_date: date) -> bool:
    codes = {SNOMED: {snomed_code}}
    return len(find_conditions_with_codes(bundle, codes, date(1900, 1, 1), by_date)) > 0


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Adolescents who turn 13 during the measurement year."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    my_start, my_end = measurement_year_dates(measurement_year)
    thirteenth = date(birth_date.year + 13, birth_date.month, birth_date.day)
    if my_start <= thirteenth <= my_end:
        return True, []
    return False, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Hospice and death."""
    return check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=False,
    )


# ---------------------------------------------------------------------------
# Numerator - individual vaccines
# ---------------------------------------------------------------------------


def _check_meningococcal(bundle: dict, birth_date: date) -> bool:
    """At least 1 meningococcal between 10th and 13th birthday; or anaphylaxis."""
    tenth = date(birth_date.year + 10, birth_date.month, birth_date.day)
    thirteenth = date(birth_date.year + 13, birth_date.month, birth_date.day)
    dates = _get_immunization_dates(
        bundle,
        "Meningococcal Immunization",
        "Meningococcal Vaccine Procedure",
        tenth,
        thirteenth,
    )
    if len(dates) >= 1:
        return True
    if _has_anaphylaxis(bundle, "428301000124106", thirteenth):
        return True
    return False


def _check_tdap(bundle: dict, birth_date: date) -> bool:
    """At least 1 Tdap between 10th and 13th birthday; or anaphylaxis/encephalitis."""
    tenth = date(birth_date.year + 10, birth_date.month, birth_date.day)
    thirteenth = date(birth_date.year + 13, birth_date.month, birth_date.day)

    # Tdap: CVX 115 + procedure value set
    proc_codes = all_codes(VALUE_SETS, "Tdap Vaccine Procedure")
    dates: set[date] = set()
    for imm in get_resources_by_type(bundle, "Immunization"):
        occ = parse_date(imm.get("occurrenceDateTime"))
        if not occ or not is_date_in_range(occ, tenth, thirteenth):
            continue
        vc = imm.get("vaccineCode", {})
        for coding in vc.get("coding", []):
            if coding.get("system") == CVX and coding.get("code") == "115":
                dates.add(occ)
    for proc, proc_date in find_procedures_with_codes(
        bundle, proc_codes, tenth, thirteenth
    ):
        if proc_date:
            dates.add(proc_date)

    if len(dates) >= 1:
        return True

    # Anaphylaxis or encephalitis due to DTP/Tdap
    ana_codes = all_codes(
        VALUE_SETS, "Anaphylaxis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if ana_codes and find_conditions_with_codes(
        bundle, ana_codes, date(1900, 1, 1), thirteenth
    ):
        return True
    enc_codes = all_codes(
        VALUE_SETS, "Encephalitis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if enc_codes and find_conditions_with_codes(
        bundle, enc_codes, date(1900, 1, 1), thirteenth
    ):
        return True
    return False


def _check_hpv(bundle: dict, birth_date: date) -> bool:
    """2-dose (146 days apart) or 3-dose HPV between 9th and 13th birthday; or anaphylaxis."""
    ninth = date(birth_date.year + 9, birth_date.month, birth_date.day)
    thirteenth = date(birth_date.year + 13, birth_date.month, birth_date.day)
    dates = _get_immunization_dates(
        bundle,
        "HPV Immunization",
        "HPV Vaccine Procedure",
        ninth,
        thirteenth,
    )
    if len(dates) >= 3:
        return True
    if len(dates) >= 2:
        # Check 146-day minimum interval
        for i in range(len(dates)):
            for j in range(i + 1, len(dates)):
                if (dates[j] - dates[i]).days >= 146:
                    return True
    if _has_anaphylaxis(bundle, "428241000124101", thirteenth):
        return True
    return False


# ---------------------------------------------------------------------------
# Numerator (single-rate wrapper for run_measure compatibility)
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    combo2 = (
        _check_meningococcal(bundle, birth_date)
        and _check_tdap(bundle, birth_date)
        and _check_hpv(bundle, birth_date)
    )
    return combo2, []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_ima_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate IMA-E with multi-rate report."""
    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated = eligible_refs + exclusion_refs

    birth_date = get_patient_birth_date(bundle)

    rate_names = ["Meningococcal", "Tdap", "HPV", "Combo1", "Combo2"]

    if not is_eligible or not birth_date:
        groups = [
            {
                "code": f"IMA-E-{r}",
                "display": f"IMA-E {r}",
                "initial_population": False,
                "denominator_exclusion": False,
                "numerator": False,
            }
            for r in rate_names
        ]
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="IMA-E",
            measure_name="Immunizations for Adolescents",
            measurement_year=measurement_year,
            groups=groups,
            evaluated_resources=all_evaluated,
        )

    mening = _check_meningococcal(bundle, birth_date)
    tdap = _check_tdap(bundle, birth_date)
    hpv = _check_hpv(bundle, birth_date)
    combo1 = mening and tdap
    combo2 = combo1 and hpv

    results = {
        "Meningococcal": mening,
        "Tdap": tdap,
        "HPV": hpv,
        "Combo1": combo1,
        "Combo2": combo2,
    }
    groups = [
        {
            "code": f"IMA-E-{r}",
            "display": f"IMA-E {r}",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": results[r],
        }
        for r in rate_names
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="IMA-E",
        measure_name="Immunizations for Adolescents",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
