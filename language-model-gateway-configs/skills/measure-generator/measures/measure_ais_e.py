"""
HEDIS MY 2025 - Adult Immunization Status (AIS-E).

The percentage of members 19 years of age and older who are up to date on
recommended routine vaccines for influenza, tetanus and diphtheria (Td) or
tetanus, diphtheria and acellular pertussis (Tdap), zoster, pneumococcal
and hepatitis B.

Rate 1 - Influenza (19+)
Rate 2 - Td/Tdap (19+)
Rate 3 - Zoster (50+)
Rate 4 - Pneumococcal (65+)
Rate 5 - Hepatitis B (19-59)
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    get_patient,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
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

VALUE_SETS = load_value_sets_from_csv("AIS-E")


def _find_immunizations(
    bundle: dict,
    code_sets: dict[str, set[str]],
    start: date | None = None,
    end: date | None = None,
) -> list[tuple[dict, date | None]]:
    """Find Immunization resources matching code sets within optional date range."""
    results = []
    for imm in get_resources_by_type(bundle, "Immunization"):
        imm_date = parse_date(imm.get("occurrenceDateTime"))
        if start and end and not is_date_in_range(imm_date, start, end):
            continue
        if start and not end and imm_date and imm_date < start:
            continue
        if end and not start and imm_date and imm_date > end:
            continue
        vaccine_code = imm.get("vaccineCode", {})
        if codeable_concept_has_any_code(vaccine_code, code_sets):
            results.append((imm, imm_date))
    return results


def _find_immunizations_by_cvx(
    bundle: dict,
    cvx_codes: set[str],
    start: date | None = None,
    end: date | None = None,
) -> list[tuple[dict, date | None]]:
    """Find Immunization resources by CVX codes."""
    return _find_immunizations(bundle, {CVX: cvx_codes}, start, end)


def _has_anaphylaxis_snomed(bundle: dict, snomed_code: str) -> bool:
    """Check for anaphylaxis condition by SNOMED code any time."""
    for cond in get_resources_by_type(bundle, "Condition"):
        for coding in cond.get("code", {}).get("coding", []):
            if coding.get("system") == SNOMED and coding.get("code") == snomed_code:
                return True
    return False


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Initial population: members 19 years and older at start of measurement period."""
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start)
    if age < 19:
        return False, evaluated

    patient = get_patient(bundle)
    if patient:
        evaluated.append(f"Patient/{patient.get('id')}")
    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Exclusions: hospice during measurement period, death during measurement period."""
    evaluated: list[str] = []

    from .hedis_common import check_hospice, check_death

    excluded, refs = check_hospice(bundle, VALUE_SETS, measurement_year)
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    excluded, refs = check_death(bundle, measurement_year)
    evaluated.extend(refs)
    if excluded:
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator checks per antigen
# ---------------------------------------------------------------------------


def _check_influenza(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Numerator 1 - Influenza: received influenza vaccine between July 1 of prior
    year and June 30 of measurement year, or anaphylaxis contraindication.
    """
    evaluated: list[str] = []
    flu_start = date(measurement_year - 1, 7, 1)
    flu_end = date(measurement_year, 6, 30)

    # Immunization resources
    for vs_name in (
        "Adult Influenza Immunization",
        "Influenza Virus LAIV Immunization",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if vs_codes:
            for imm, _ in _find_immunizations(bundle, vs_codes, flu_start, flu_end):
                evaluated.append(f"Immunization/{imm.get('id')}")
                return True, evaluated

    # Procedure resources
    for vs_name in (
        "Adult Influenza Vaccine Procedure",
        "Influenza Virus LAIV Vaccine Procedure",
    ):
        vs_codes = all_codes(VALUE_SETS, vs_name)
        if vs_codes:
            for proc, _ in find_procedures_with_codes(
                bundle, vs_codes, flu_start, flu_end
            ):
                evaluated.append(f"Procedure/{proc.get('id')}")
                return True, evaluated

    # Anaphylaxis contraindication
    if _has_anaphylaxis_snomed(bundle, "471361000124100"):
        return True, evaluated

    return False, evaluated


def _check_td_tdap(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Numerator 2 - Td/Tdap: received Td or Tdap vaccine between 9 years prior
    to start of measurement period and end of measurement period, or
    contraindications.
    """
    evaluated: list[str] = []
    my_start, my_end = measurement_year_dates(measurement_year)
    lookback_start = date(measurement_year - 9, 1, 1)

    # Td vaccine
    td_codes = all_codes(VALUE_SETS, "Td Immunization")
    if td_codes:
        for imm, _ in _find_immunizations(bundle, td_codes, lookback_start, my_end):
            evaluated.append(f"Immunization/{imm.get('id')}")
            return True, evaluated
    td_proc_codes = all_codes(VALUE_SETS, "Td Vaccine Procedure")
    if td_proc_codes:
        for proc, _ in find_procedures_with_codes(
            bundle, td_proc_codes, lookback_start, my_end
        ):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    # Tdap vaccine (CVX 115)
    tdap_imms = _find_immunizations_by_cvx(bundle, {"115"}, lookback_start, my_end)
    if tdap_imms:
        evaluated.append(f"Immunization/{tdap_imms[0][0].get('id')}")
        return True, evaluated
    tdap_proc_codes = all_codes(VALUE_SETS, "Tdap Vaccine Procedure")
    if tdap_proc_codes:
        for proc, _ in find_procedures_with_codes(
            bundle, tdap_proc_codes, lookback_start, my_end
        ):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    # Contraindications
    anaph_codes = all_codes(
        VALUE_SETS, "Anaphylaxis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if anaph_codes:
        for cond, _ in find_conditions_with_codes(bundle, anaph_codes, None, None):
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated
    enceph_codes = all_codes(
        VALUE_SETS, "Encephalitis Due to Diphtheria, Tetanus or Pertussis Vaccine"
    )
    if enceph_codes:
        for cond, _ in find_conditions_with_codes(bundle, enceph_codes, None, None):
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    return False, evaluated


def _check_zoster(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Numerator 3 - Zoster: two doses of recombinant zoster vaccine (CVX 187)
    at least 28 days apart on or after Oct 1, 2017 through end of measurement
    period, or anaphylaxis contraindication.
    """
    evaluated: list[str] = []
    _, my_end = measurement_year_dates(measurement_year)
    zoster_start = date(2017, 10, 1)

    # Recombinant zoster vaccine (CVX 187)
    zoster_imms = _find_immunizations_by_cvx(bundle, {"187"}, zoster_start, my_end)
    # Also check procedure value set
    zoster_proc_codes = all_codes(
        VALUE_SETS, "Herpes Zoster Recombinant Vaccine Procedure"
    )
    zoster_procs = []
    if zoster_proc_codes:
        zoster_procs = find_procedures_with_codes(
            bundle, zoster_proc_codes, zoster_start, my_end
        )

    all_dates: list[date] = []
    all_refs: list[str] = []
    for imm, imm_date in zoster_imms:
        if imm_date:
            all_dates.append(imm_date)
            all_refs.append(f"Immunization/{imm.get('id')}")
    for proc, proc_date in zoster_procs:
        if proc_date:
            all_dates.append(proc_date)
            all_refs.append(f"Procedure/{proc.get('id')}")

    if len(all_dates) >= 2:
        all_dates.sort()
        for i in range(len(all_dates) - 1):
            if (all_dates[i + 1] - all_dates[i]).days >= 28:
                evaluated.extend(all_refs)
                return True, evaluated

    # Anaphylaxis contraindication
    anaph_codes = all_codes(VALUE_SETS, "Anaphylaxis Due to Herpes Zoster Vaccine")
    if anaph_codes:
        for cond, _ in find_conditions_with_codes(bundle, anaph_codes, None, None):
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    return False, evaluated


def _check_pneumococcal(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Numerator 4 - Pneumococcal: at least one adult pneumococcal vaccine on or
    after 19th birthday, or anaphylaxis contraindication.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    nineteenth_bday = date(birth_date.year + 19, birth_date.month, birth_date.day)
    _, my_end = measurement_year_dates(measurement_year)

    pneumo_codes = all_codes(VALUE_SETS, "Adult Pneumococcal Immunization")
    if pneumo_codes:
        for imm, _ in _find_immunizations(
            bundle, pneumo_codes, nineteenth_bday, my_end
        ):
            evaluated.append(f"Immunization/{imm.get('id')}")
            return True, evaluated
    pneumo_proc_codes = all_codes(VALUE_SETS, "Adult Pneumococcal Vaccine Procedure")
    if pneumo_proc_codes:
        for proc, _ in find_procedures_with_codes(
            bundle, pneumo_proc_codes, nineteenth_bday, my_end
        ):
            evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    # Anaphylaxis contraindication
    if _has_anaphylaxis_snomed(bundle, "471141000124102"):
        return True, evaluated

    return False, evaluated


def _check_hepatitis_b(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Numerator 5 - Hepatitis B: childhood series (3 doses before 19th birthday),
    or adult series (2-dose or 3-dose after 19th birthday), or positive serology,
    or history of hepatitis B illness, or anaphylaxis contraindication.
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    nineteenth_bday = date(birth_date.year + 19, birth_date.month, birth_date.day)
    _, my_end = measurement_year_dates(measurement_year)

    # Childhood hepatitis B (3 doses before 19th birthday)
    child_codes = all_codes(VALUE_SETS, "Hepatitis B Immunization")
    child_proc_codes = all_codes(VALUE_SETS, "Hepatitis B Vaccine Procedure")
    child_dates: list[date] = []
    if child_codes:
        for imm, imm_date in _find_immunizations(
            bundle, child_codes, None, nineteenth_bday
        ):
            if imm_date:
                child_dates.append(imm_date)
    if child_proc_codes:
        for proc, proc_date in find_procedures_with_codes(
            bundle, child_proc_codes, date(1900, 1, 1), nineteenth_bday
        ):
            if proc_date:
                child_dates.append(proc_date)
    unique_child_dates = set(child_dates)
    if len(unique_child_dates) >= 3:
        return True, evaluated

    # Adult 2-dose series (CVX 189, at least 28 days apart)
    adult_2dose_imms = _find_immunizations_by_cvx(
        bundle, {"189"}, nineteenth_bday, my_end
    )
    adult_2dose_proc_codes = all_codes(
        VALUE_SETS, "Adult Hepatitis B Vaccine Procedure (2 dose)"
    )
    adult_2dose_dates: list[date] = []
    for imm, imm_date in adult_2dose_imms:
        if imm_date:
            adult_2dose_dates.append(imm_date)
    if adult_2dose_proc_codes:
        for proc, proc_date in find_procedures_with_codes(
            bundle, adult_2dose_proc_codes, nineteenth_bday, my_end
        ):
            if proc_date:
                adult_2dose_dates.append(proc_date)
    if len(set(adult_2dose_dates)) >= 2:
        adult_2dose_dates.sort()
        if (adult_2dose_dates[-1] - adult_2dose_dates[0]).days >= 28:
            return True, evaluated

    # Adult 3-dose series (different days of service)
    adult_3dose_codes = all_codes(VALUE_SETS, "Adult Hepatitis B Immunization (3 dose)")
    adult_3dose_proc_codes = all_codes(
        VALUE_SETS, "Adult Hepatitis B Vaccine Procedure (3 dose)"
    )
    adult_3dose_dates: list[date] = []
    if adult_3dose_codes:
        for imm, imm_date in _find_immunizations(
            bundle, adult_3dose_codes, nineteenth_bday, my_end
        ):
            if imm_date:
                adult_3dose_dates.append(imm_date)
    if adult_3dose_proc_codes:
        for proc, proc_date in find_procedures_with_codes(
            bundle, adult_3dose_proc_codes, nineteenth_bday, my_end
        ):
            if proc_date:
                adult_3dose_dates.append(proc_date)
    if len(set(adult_3dose_dates)) >= 3:
        return True, evaluated

    # Positive serology
    hep_b_test_codes = all_codes(VALUE_SETS, "Hepatitis B Tests With Threshold of 10")
    if hep_b_test_codes:
        for obs in get_resources_by_type(bundle, "Observation"):
            if resource_has_any_code(obs, hep_b_test_codes):
                value = obs.get("valueQuantity", {}).get("value")
                if value is not None and value > 10:
                    evaluated.append(f"Observation/{obs.get('id')}")
                    return True, evaluated

    prevac_codes = all_codes(VALUE_SETS, "Hepatitis B Prevaccination Tests")
    immunity_codes = all_codes(VALUE_SETS, "Hepatitis B Immunity Finding")
    if prevac_codes and immunity_codes:
        for obs in get_resources_by_type(bundle, "Observation"):
            if resource_has_any_code(obs, prevac_codes):
                interpretation = obs.get("interpretation", [])
                value_cc = obs.get("valueCodeableConcept", {})
                if codeable_concept_has_any_code(value_cc, immunity_codes):
                    evaluated.append(f"Observation/{obs.get('id')}")
                    return True, evaluated
                for interp in interpretation:
                    if codeable_concept_has_any_code(interp, immunity_codes):
                        evaluated.append(f"Observation/{obs.get('id')}")
                        return True, evaluated

    # History of hepatitis B illness
    hep_b_illness_codes = all_codes(VALUE_SETS, "Hepatitis B")
    if hep_b_illness_codes:
        for cond, _ in find_conditions_with_codes(
            bundle, hep_b_illness_codes, None, None
        ):
            evaluated.append(f"Condition/{cond.get('id')}")
            return True, evaluated

    # Anaphylaxis contraindication
    if _has_anaphylaxis_snomed(bundle, "428321000124101"):
        return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Numerator (combined - not used by multi-rate)
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Not used directly; see calculate function for multi-rate logic."""
    return False, []


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------


def calculate_ais_e_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """
    Calculate AIS-E measure for a patient bundle.

    Returns a FHIR MeasureReport with five rate groups for each antigen.
    """
    all_evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    my_start, _ = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_start) if birth_date else 0

    # Rate 1: Influenza (19+)
    flu_met = False
    if is_eligible and not is_excluded:
        flu_met, flu_refs = _check_influenza(bundle, measurement_year)
        all_evaluated.extend(flu_refs)

    # Rate 2: Td/Tdap (19+)
    td_met = False
    if is_eligible and not is_excluded:
        td_met, td_refs = _check_td_tdap(bundle, measurement_year)
        all_evaluated.extend(td_refs)

    # Rate 3: Zoster (50+)
    zoster_eligible = is_eligible and age >= 50
    zoster_met = False
    if zoster_eligible and not is_excluded:
        zoster_met, zoster_refs = _check_zoster(bundle, measurement_year)
        all_evaluated.extend(zoster_refs)

    # Rate 4: Pneumococcal (65+)
    pneumo_eligible = is_eligible and age >= 65
    pneumo_met = False
    if pneumo_eligible and not is_excluded:
        pneumo_met, pneumo_refs = _check_pneumococcal(bundle, measurement_year)
        all_evaluated.extend(pneumo_refs)

    # Rate 5: Hepatitis B (19-59)
    hepb_eligible = is_eligible and 19 <= age <= 59
    hepb_met = False
    if hepb_eligible and not is_excluded:
        hepb_met, hepb_refs = _check_hepatitis_b(bundle, measurement_year)
        all_evaluated.extend(hepb_refs)

    groups = [
        {
            "code": "influenza",
            "display": "Immunization Status: Influenza",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": flu_met,
        },
        {
            "code": "td-tdap",
            "display": "Immunization Status: Td/Tdap",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": td_met,
        },
        {
            "code": "zoster",
            "display": "Immunization Status: Zoster",
            "initial_population": zoster_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": zoster_met,
        },
        {
            "code": "pneumococcal",
            "display": "Immunization Status: Pneumococcal",
            "initial_population": pneumo_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": pneumo_met,
        },
        {
            "code": "hepatitis-b",
            "display": "Immunization Status: Hepatitis B",
            "initial_population": hepb_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": hepb_met,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="AIS-E",
        measure_name="Adult Immunization Status",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
