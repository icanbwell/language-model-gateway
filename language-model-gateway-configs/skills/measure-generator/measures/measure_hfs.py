"""
HEDIS MY 2025 - Hospitalization Following Discharge From a Skilled Nursing
Facility (HFS).

For members 65 years of age and older, the percentage of skilled nursing
facility discharges (SND) to the community that were followed by an
unplanned acute hospitalization for any diagnosis within 30 days and
within 60 days.

This is a discharge-based, risk-adjusted measure. For individual patient
calculation we report the observed hospitalization (not expected).
Two rates: 30-day and 60-day.
"""

from datetime import date

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("HFS")


def _get_snf_discharges(
    bundle: dict, start: date, end: date
) -> list[tuple[dict, date]]:
    """Identify skilled nursing facility discharges in the date range."""
    snf_codes = all_codes(VALUE_SETS, "Skilled Nursing Stay")
    if not snf_codes:
        return []

    results = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        if not (
            resource_has_any_code(enc, snf_codes)
            or any(
                codeable_concept_has_any_code(t, snf_codes) for t in enc.get("type", [])
            )
        ):
            continue

        discharge_date = get_encounter_end_date(enc)
        admission_date = get_encounter_date(enc)
        if not discharge_date or not is_date_in_range(discharge_date, start, end):
            continue

        # Exclude same-day stays (admission == discharge)
        if admission_date and admission_date == discharge_date:
            continue

        results.append((enc, discharge_date))

    return results


def _get_acute_stays(bundle: dict) -> list[dict]:
    """Identify acute inpatient and observation stays (excluding nonacute)."""
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    observation_codes = all_codes(VALUE_SETS, "Observation Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")

    stays = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        is_acute = False
        is_nonacute = False

        for code_set in (inpatient_codes, observation_codes):
            if code_set and (
                resource_has_any_code(enc, code_set)
                or any(
                    codeable_concept_has_any_code(t, code_set)
                    for t in enc.get("type", [])
                )
            ):
                is_acute = True

        if nonacute_codes and (
            resource_has_any_code(enc, nonacute_codes)
            or any(
                codeable_concept_has_any_code(t, nonacute_codes)
                for t in enc.get("type", [])
            )
        ):
            is_nonacute = True

        if is_acute and not is_nonacute:
            stays.append(enc)

    return stays


def _is_planned_stay(encounter: dict) -> bool:
    """Check if a hospital stay is planned (numerator exclusion)."""
    chemo_codes = all_codes(VALUE_SETS, "Chemotherapy Encounter")
    rehab_codes = all_codes(VALUE_SETS, "Rehabilitation")
    kidney_codes = all_codes(VALUE_SETS, "Kidney Transplant")
    bmt_codes = all_codes(VALUE_SETS, "Bone Marrow Transplant")
    organ_codes = all_codes(VALUE_SETS, "Organ Transplant Other Than Kidney")
    pancreatic_codes = all_codes(
        VALUE_SETS, "Introduction of Autologous Pancreatic Cells"
    )
    planned_proc_codes = all_codes(VALUE_SETS, "Potentially Planned Procedures")
    planned_pac_codes = all_codes(
        VALUE_SETS, "Potentially Planned Post Acute Care Hospitalization"
    )
    acute_dx_codes = all_codes(VALUE_SETS, "Acute Condition")

    if chemo_codes and resource_has_any_code(encounter, chemo_codes):
        return True
    if rehab_codes and resource_has_any_code(encounter, rehab_codes):
        return True

    for transplant_codes in (kidney_codes, bmt_codes, organ_codes, pancreatic_codes):
        if transplant_codes and (
            resource_has_any_code(encounter, transplant_codes)
            or any(
                codeable_concept_has_any_code(t, transplant_codes)
                for t in encounter.get("type", [])
            )
        ):
            return True

    # Potentially planned procedure without acute principal diagnosis
    all_planned = {}
    for pc in (planned_proc_codes, planned_pac_codes):
        if pc:
            for sys, codes in pc.items():
                all_planned.setdefault(sys, set()).update(codes)

    if all_planned:
        has_planned = resource_has_any_code(encounter, all_planned) or any(
            codeable_concept_has_any_code(t, all_planned)
            for t in encounter.get("type", [])
        )
        if has_planned:
            has_acute = acute_dx_codes and (
                resource_has_any_code(encounter, acute_dx_codes)
                or any(
                    codeable_concept_has_any_code(t, acute_dx_codes)
                    for t in encounter.get("type", [])
                )
            )
            if not has_acute:
                return True

    return False


def _has_pregnancy_or_perinatal(encounter: dict) -> bool:
    """Check for pregnancy or perinatal principal diagnosis."""
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy")
    perinatal_codes = all_codes(VALUE_SETS, "Perinatal Conditions")

    if pregnancy_codes and resource_has_any_code(encounter, pregnancy_codes):
        return True
    if perinatal_codes and resource_has_any_code(encounter, perinatal_codes):
        return True
    return False


def _is_direct_transfer_to_acute(snd_date: date, bundle: dict) -> bool:
    """Check if SND has a direct transfer to acute hospital (within 1 day)."""
    acute_stays = _get_acute_stays(bundle)
    for stay in acute_stays:
        admission = get_encounter_date(stay)
        if not admission:
            continue
        diff = (admission - snd_date).days
        if 0 <= diff <= 1:
            return True
    return False


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check if patient has an SND between Jan 1 and Nov 1 of MY, age 65+."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    snd_start = date(measurement_year, 1, 1)
    snd_end = date(measurement_year, 11, 1)
    evaluated: list[str] = []

    snf_discharges = _get_snf_discharges(bundle, snd_start, snd_end)
    for enc, snd_date in snf_discharges:
        age = calculate_age(birth_date, snd_date)
        if age < 65:
            continue

        # Exclude SNDs that are direct transfers to acute hospital
        if _is_direct_transfer_to_acute(snd_date, bundle):
            continue

        evaluated.append(f"Encounter/{enc.get('id')}")
        return True, evaluated

    return False, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check required exclusions: hospice and LTI."""
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check if any SND had an unplanned acute hospitalization within 30 days."""
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, []

    snd_start = date(measurement_year, 1, 1)
    snd_end = date(measurement_year, 11, 1)
    evaluated: list[str] = []

    snf_discharges = _get_snf_discharges(bundle, snd_start, snd_end)
    acute_stays = _get_acute_stays(bundle)

    for snf_enc, snd_date in snf_discharges:
        age = calculate_age(birth_date, snd_date)
        if age < 65:
            continue
        if _is_direct_transfer_to_acute(snd_date, bundle):
            continue

        # Check for acute hospitalization within 30 days of SND
        for stay in acute_stays:
            admission = get_encounter_date(stay)
            if not admission:
                continue
            days_diff = (admission - snd_date).days
            if days_diff < 2:
                # Within 1 day = direct transfer (already excluded from denom)
                continue
            if 2 <= days_diff <= 30:
                if _has_pregnancy_or_perinatal(stay):
                    continue
                if _is_planned_stay(stay):
                    continue
                evaluated.append(f"Encounter/{stay.get('id')}")
                return True, evaluated

    return False, evaluated


def calculate_hfs_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the HFS measure with 30-day and 60-day rates."""
    patient_id = get_patient_id(bundle)
    birth_date = get_patient_birth_date(bundle)
    all_evaluated: list[str] = []

    is_eligible, elig_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(elig_refs)

    is_excluded, excl_refs = check_exclusions(bundle, measurement_year)
    all_evaluated.extend(excl_refs)

    # 30-day numerator
    has_30day, num30_refs = check_numerator(bundle, measurement_year)
    all_evaluated.extend(num30_refs)

    # 60-day numerator: same logic but with 60-day window
    has_60day = has_30day  # If 30-day is true, 60-day is also true
    if not has_60day and is_eligible and not is_excluded and birth_date:
        snd_start = date(measurement_year, 1, 1)
        snd_end = date(measurement_year, 11, 1)
        snf_discharges = _get_snf_discharges(bundle, snd_start, snd_end)
        acute_stays = _get_acute_stays(bundle)

        for snf_enc, snd_date in snf_discharges:
            age = calculate_age(birth_date, snd_date)
            if age < 65:
                continue
            if _is_direct_transfer_to_acute(snd_date, bundle):
                continue
            for stay in acute_stays:
                admission = get_encounter_date(stay)
                if not admission:
                    continue
                days_diff = (admission - snd_date).days
                if days_diff < 2:
                    continue
                if 2 <= days_diff <= 60:
                    if _has_pregnancy_or_perinatal(stay):
                        continue
                    if _is_planned_stay(stay):
                        continue
                    all_evaluated.append(f"Encounter/{stay.get('id')}")
                    has_60day = True
                    break
            if has_60day:
                break

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="HFS",
        measure_name="Hospitalization Following Discharge From a Skilled Nursing Facility",
        measurement_year=measurement_year,
        groups=[
            {
                "code": "HFS-30Day",
                "display": "Hospitalization Within 30 Days",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": has_30day,
            },
            {
                "code": "HFS-60Day",
                "display": "Hospitalization Within 60 Days",
                "initial_population": is_eligible,
                "denominator_exclusion": is_excluded if is_eligible else False,
                "numerator": has_60day,
            },
        ],
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
