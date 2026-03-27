"""
HEDIS MY 2025 - Childhood Immunization Status (CIS-E)

The percentage of children 2 years of age who had four DTaP; three IPV;
one MMR; three HiB; three HepB; one VZV; four PCV; one HepA; two or three
rotavirus; and two influenza vaccines by their second birthday.

Calculates a rate for each vaccine and three combination rates
(Combo 3, Combo 7, Combo 10).
"""

from __future__ import annotations

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    parse_date,
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

VALUE_SETS = load_value_sets_from_csv("CIS-E")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_AGE_DAYS_42 = 42  # vaccines not counted before 42 days after birth
_MIN_AGE_DAYS_180 = 180  # influenza not counted before 180 days


def _get_immunization_dates(
    bundle: dict,
    imm_vs_name: str,
    proc_vs_name: str,
    birth_date: date,
    second_birthday: date,
    min_age_days: int = 0,
    earliest: date | None = None,
) -> list[date]:
    """Collect unique vaccination dates from Immunization and Procedure resources."""
    dates: set[date] = set()
    imm_codes = all_codes(VALUE_SETS, imm_vs_name)
    proc_codes = all_codes(VALUE_SETS, proc_vs_name)
    min_date = birth_date + timedelta(days=min_age_days) if min_age_days else birth_date
    if earliest and earliest > min_date:
        min_date = earliest

    for imm in get_resources_by_type(bundle, "Immunization"):
        occ = parse_date(imm.get("occurrenceDateTime") or (imm.get("occurrenceString")))
        if not occ:
            continue
        if occ < min_date or occ > second_birthday:
            continue
        if resource_has_any_code(imm, imm_codes):
            dates.add(occ)
        # Also check vaccineCode
        vc = imm.get("vaccineCode", {})
        if codeable_concept_has_any_code(vc, imm_codes):
            dates.add(occ)

    for proc, proc_date in find_procedures_with_codes(
        bundle, proc_codes, min_date, second_birthday
    ):
        if proc_date:
            dates.add(proc_date)

    return sorted(dates)


def _has_anaphylaxis(bundle: dict, snomed_code: str, by_date: date) -> bool:
    """Check for anaphylaxis SNOMED code on or before a date."""
    far_past = date(1900, 1, 1)
    codes = {SNOMED: {snomed_code}}
    return len(find_conditions_with_codes(bundle, codes, far_past, by_date)) > 0


def _has_history_illness(
    bundle: dict,
    vs_name: str,
    by_date: date,
) -> bool:
    """Check for history of illness on or before a date."""
    far_past = date(1900, 1, 1)
    illness_codes = all_codes(VALUE_SETS, vs_name)
    if not illness_codes:
        return False
    return len(find_conditions_with_codes(bundle, illness_codes, far_past, by_date)) > 0


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Children who turn 2 during the measurement year."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    my_start, my_end = measurement_year_dates(measurement_year)
    second_birthday = date(birth_date.year + 2, birth_date.month, birth_date.day)
    if my_start <= second_birthday <= my_end:
        return True, []
    return False, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Hospice, death, contraindications, organ/bone marrow transplants."""
    excluded, refs = check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=False,
    )
    if excluded:
        return True, refs

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, refs
    second_birthday = date(birth_date.year + 2, birth_date.month, birth_date.day)

    # Contraindications to childhood vaccines
    contra_codes = all_codes(VALUE_SETS, "Contraindications to Childhood Vaccines")
    if contra_codes:
        far_past = date(1900, 1, 1)
        found = find_conditions_with_codes(
            bundle, contra_codes, far_past, second_birthday
        )
        if found:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]
        found_proc = find_procedures_with_codes(
            bundle, contra_codes, far_past, second_birthday
        )
        if found_proc:
            return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found_proc]

    # Organ and bone marrow transplants
    transplant_codes = all_codes(VALUE_SETS, "Organ and Bone Marrow Transplants")
    if transplant_codes:
        far_past = date(1900, 1, 1)
        found = find_conditions_with_codes(
            bundle, transplant_codes, far_past, second_birthday
        )
        if found:
            return True, refs + [f"Condition/{c.get('id')}" for c, _ in found]
        found_proc = find_procedures_with_codes(
            bundle, transplant_codes, far_past, second_birthday
        )
        if found_proc:
            return True, refs + [f"Procedure/{p.get('id')}" for p, _ in found_proc]

    return False, refs


# ---------------------------------------------------------------------------
# Numerator - individual antigens
# ---------------------------------------------------------------------------


def _check_dtap(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 4 DTaP on different dates, not before 42 days; or anaphylaxis/encephalitis."""
    dates = _get_immunization_dates(
        bundle,
        "DTaP Immunization",
        "DTaP Vaccine Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_42,
    )
    if len(dates) >= 4:
        return True
    if _has_anaphylaxis(bundle, "471311000124103", second_birthday):
        return True
    ana_codes = all_codes(
        VALUE_SETS, "Anaphylaxis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if ana_codes and find_conditions_with_codes(
        bundle, ana_codes, date(1900, 1, 1), second_birthday
    ):
        return True
    enc_codes = all_codes(
        VALUE_SETS, "Encephalitis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if enc_codes and find_conditions_with_codes(
        bundle, enc_codes, date(1900, 1, 1), second_birthday
    ):
        return True
    return False


def _check_ipv(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 3 IPV on different dates, not before 42 days; or anaphylaxis."""
    dates = _get_immunization_dates(
        bundle,
        "Inactivated Polio Vaccine (IPV) Immunization",
        "Inactivated Polio Vaccine (IPV) Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_42,
    )
    if len(dates) >= 3:
        return True
    if _has_anaphylaxis(bundle, "471321000124106", second_birthday):
        return True
    return False


def _check_mmr(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 1 MMR between 1st and 2nd birthday; or history of all three illnesses; or anaphylaxis."""
    first_birthday = date(birth_date.year + 1, birth_date.month, birth_date.day)
    dates = _get_immunization_dates(
        bundle,
        "Measles, Mumps and Rubella (MMR) Immunization",
        "Measles, Mumps and Rubella (MMR) Vaccine Procedure",
        birth_date,
        second_birthday,
        earliest=first_birthday,
    )
    if len(dates) >= 1:
        return True
    # History of all three illnesses
    if (
        _has_history_illness(bundle, "Measles", second_birthday)
        and _has_history_illness(bundle, "Mumps", second_birthday)
        and _has_history_illness(bundle, "Rubella", second_birthday)
    ):
        return True
    if _has_anaphylaxis(bundle, "471331000124109", second_birthday):
        return True
    return False


def _check_hib(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 3 HiB on different dates, not before 42 days; or anaphylaxis."""
    dates = _get_immunization_dates(
        bundle,
        "Haemophilus Influenzae Type B (HiB) Immunization",
        "Haemophilus Influenzae Type B (HiB) Vaccine Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_42,
    )
    if len(dates) >= 3:
        return True
    if _has_anaphylaxis(bundle, "433621000124101", second_birthday):
        return True
    return False


def _check_hepb(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 3 HepB on different dates; or history of illness; or anaphylaxis."""
    dates = _get_immunization_dates(
        bundle,
        "Hepatitis B Immunization",
        "Hepatitis B Vaccine Procedure",
        birth_date,
        second_birthday,
    )
    if len(dates) >= 3:
        return True
    if _has_history_illness(bundle, "Hepatitis B", second_birthday):
        return True
    if _has_anaphylaxis(bundle, "428321000124101", second_birthday):
        return True
    return False


def _check_vzv(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 1 VZV between 1st and 2nd birthday; or history; or anaphylaxis."""
    first_birthday = date(birth_date.year + 1, birth_date.month, birth_date.day)
    dates = _get_immunization_dates(
        bundle,
        "Varicella Zoster (VZV) Immunization",
        "Varicella Zoster (VZV) Vaccine Procedure",
        birth_date,
        second_birthday,
        earliest=first_birthday,
    )
    if len(dates) >= 1:
        return True
    if _has_history_illness(bundle, "Varicella Zoster", second_birthday):
        return True
    if _has_anaphylaxis(bundle, "471341000124104", second_birthday):
        return True
    return False


def _check_pcv(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 4 PCV on different dates, not before 42 days; or anaphylaxis."""
    dates = _get_immunization_dates(
        bundle,
        "Pneumococcal Conjugate Immunization",
        "Pneumococcal Conjugate Vaccine Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_42,
    )
    if len(dates) >= 4:
        return True
    if _has_anaphylaxis(bundle, "471141000124102", second_birthday):
        return True
    return False


def _check_hepa(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 1 HepA between 1st and 2nd birthday; or history; or anaphylaxis."""
    first_birthday = date(birth_date.year + 1, birth_date.month, birth_date.day)
    dates = _get_immunization_dates(
        bundle,
        "Hepatitis A Immunization",
        "Hepatitis A Vaccine Procedure",
        birth_date,
        second_birthday,
        earliest=first_birthday,
    )
    if len(dates) >= 1:
        return True
    if _has_history_illness(bundle, "Hepatitis A", second_birthday):
        return True
    if _has_anaphylaxis(bundle, "471311000124103", second_birthday):
        return True
    return False


def _check_rotavirus(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """2-dose or 3-dose rotavirus schedule, or mixed; or anaphylaxis."""
    # 2-dose: CVX 119 / procedure value set
    two_dose_dates = _get_immunization_dates(
        bundle,
        "Rotavirus Vaccine (2 Dose Schedule) Procedure",
        "Rotavirus Vaccine (2 Dose Schedule) Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_42,
    )
    # Also check CVX 119 directly in Immunization resources
    for imm in get_resources_by_type(bundle, "Immunization"):
        occ = parse_date(imm.get("occurrenceDateTime"))
        if not occ:
            continue
        min_d = birth_date + timedelta(days=_MIN_AGE_DAYS_42)
        if occ < min_d or occ > second_birthday:
            continue
        vc = imm.get("vaccineCode", {})
        for coding in vc.get("coding", []):
            if coding.get("system") == CVX and coding.get("code") == "119":
                two_dose_dates.append(occ)
    two_dose_dates = sorted(set(two_dose_dates))

    # 3-dose
    three_dose_dates = _get_immunization_dates(
        bundle,
        "Rotavirus (3 Dose Schedule) Immunization",
        "Rotavirus Vaccine (3 Dose Schedule) Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_42,
    )

    if len(two_dose_dates) >= 2:
        return True
    if len(three_dose_dates) >= 3:
        return True
    # Mixed: 1 two-dose + 2 three-dose on different dates
    all_dates = sorted(set(two_dose_dates + three_dose_dates))
    if len(two_dose_dates) >= 1 and len(three_dose_dates) >= 2 and len(all_dates) >= 3:
        return True
    if _has_anaphylaxis(bundle, "428331000124103", second_birthday):
        return True
    return False


def _check_influenza(bundle: dict, birth_date: date, second_birthday: date) -> bool:
    """At least 2 influenza on different dates, not before 180 days; or anaphylaxis.

    An LAIV vaccine on the 2nd birthday counts as one of the two.
    """
    dates = _get_immunization_dates(
        bundle,
        "Influenza Immunization",
        "Influenza Vaccine Procedure",
        birth_date,
        second_birthday,
        min_age_days=_MIN_AGE_DAYS_180,
    )
    # LAIV on the second birthday
    laiv_dates = _get_immunization_dates(
        bundle,
        "Influenza Virus LAIV Immunization",
        "Influenza Virus LAIV Vaccine Procedure",
        birth_date,
        second_birthday,
        earliest=second_birthday,
    )
    all_dates = sorted(set(dates + laiv_dates))
    if len(all_dates) >= 2:
        return True
    if _has_anaphylaxis(bundle, "471361000124100", second_birthday):
        return True
    return False


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Evaluate all antigen rates and combination rates.

    Returns True if Combo 10 (all antigens) is met; the full detail
    is in the multi-rate report built by calculate_cis_e_measure.
    """
    # This is only used by run_measure for a simple single-rate call.
    # The real logic is in calculate_cis_e_measure.
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []
    second_birthday = date(birth_date.year + 2, birth_date.month, birth_date.day)
    results = _evaluate_all_antigens(bundle, birth_date, second_birthday)
    combo10 = all(results.values())
    return combo10, []


def _evaluate_all_antigens(
    bundle: dict,
    birth_date: date,
    second_birthday: date,
) -> dict[str, bool]:
    return {
        "DTaP": _check_dtap(bundle, birth_date, second_birthday),
        "IPV": _check_ipv(bundle, birth_date, second_birthday),
        "MMR": _check_mmr(bundle, birth_date, second_birthday),
        "HiB": _check_hib(bundle, birth_date, second_birthday),
        "HepB": _check_hepb(bundle, birth_date, second_birthday),
        "VZV": _check_vzv(bundle, birth_date, second_birthday),
        "PCV": _check_pcv(bundle, birth_date, second_birthday),
        "HepA": _check_hepa(bundle, birth_date, second_birthday),
        "Rotavirus": _check_rotavirus(bundle, birth_date, second_birthday),
        "Influenza": _check_influenza(bundle, birth_date, second_birthday),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_COMBO3_ANTIGENS = ("DTaP", "IPV", "MMR", "HiB", "HepB", "VZV", "PCV")
_COMBO7_ANTIGENS = _COMBO3_ANTIGENS + ("HepA", "Rotavirus")
_COMBO10_ANTIGENS = _COMBO7_ANTIGENS + ("Influenza",)


def calculate_cis_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate CIS-E with multi-rate report."""
    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
    all_evaluated = eligible_refs + exclusion_refs

    if not is_eligible:
        # Build empty multi-rate report
        groups = []
        for antigen in list(_COMBO10_ANTIGENS) + ["Combo3", "Combo7", "Combo10"]:
            groups.append(
                {
                    "code": f"CIS-E-{antigen}",
                    "display": f"CIS-E {antigen}",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                }
            )
        return build_multi_rate_measure_report(
            patient_id=get_patient_id(bundle),
            measure_abbreviation="CIS-E",
            measure_name="Childhood Immunization Status",
            measurement_year=measurement_year,
            groups=groups,
            evaluated_resources=all_evaluated,
        )

    birth_date = get_patient_birth_date(bundle)
    second_birthday = date(birth_date.year + 2, birth_date.month, birth_date.day)
    results = _evaluate_all_antigens(bundle, birth_date, second_birthday)

    combo3 = all(results[a] for a in _COMBO3_ANTIGENS)
    combo7 = all(results[a] for a in _COMBO7_ANTIGENS)
    combo10 = all(results[a] for a in _COMBO10_ANTIGENS)

    groups = []
    for antigen in _COMBO10_ANTIGENS:
        groups.append(
            {
                "code": f"CIS-E-{antigen}",
                "display": f"CIS-E {antigen}",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": results[antigen],
            }
        )
    for combo_name, combo_result in [
        ("Combo3", combo3),
        ("Combo7", combo7),
        ("Combo10", combo10),
    ]:
        groups.append(
            {
                "code": f"CIS-E-{combo_name}",
                "display": f"CIS-E {combo_name}",
                "initial_population": True,
                "denominator_exclusion": is_excluded,
                "numerator": combo_result,
            }
        )

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="CIS-E",
        measure_name="Childhood Immunization Status",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
