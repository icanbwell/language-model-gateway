"""
HEDIS MY 2025 - Transitions of Care (TRC).

Four indicators for members 18+ with inpatient discharges:
  1. Notification of Inpatient Admission (admin not available - hybrid only)
  2. Receipt of Discharge Information (admin not available - hybrid only)
  3. Patient Engagement After Inpatient Discharge (within 30 days)
  4. Medication Reconciliation Post-Discharge (within 31 days)

Discharge-based measure (Jan 1 - Dec 1 of MY).
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
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_end_date,
    find_encounters_with_codes,
    find_procedures_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("TRC")


def _find_qualifying_discharges(
    bundle: dict, measurement_year: int
) -> list[tuple[dict, date]]:
    """Find acute/nonacute inpatient discharges between Jan 1 and Dec 1 of MY."""
    my_start = date(measurement_year, 1, 1)
    discharge_end = date(measurement_year, 12, 1)

    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    if not inpatient_codes:
        return []

    discharges: list[tuple[dict, date]] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        if not resource_has_any_code(enc, inpatient_codes):
            has_type = any(
                codeable_concept_has_any_code(t, inpatient_codes)
                for t in enc.get("type", [])
            )
            if not has_type:
                continue
        discharge_date = get_encounter_end_date(enc)
        if not discharge_date:
            continue
        if is_date_in_range(discharge_date, my_start, discharge_end):
            discharges.append((enc, discharge_date))

    return discharges


def calculate_trc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate TRC measure (4 indicators) and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    # Check age: 18+ as of Dec 31 MY
    birth_date = get_patient_birth_date(bundle)
    _, my_end = measurement_year_dates(measurement_year)
    if not birth_date or calculate_age(birth_date, my_end) < 18:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="TRC",
            measure_name="Transitions of Care",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "TRC-1",
                    "display": "Notification of Inpatient Admission",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "TRC-2",
                    "display": "Receipt of Discharge Information",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "TRC-3",
                    "display": "Patient Engagement After Inpatient Discharge",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "TRC-4",
                    "display": "Medication Reconciliation Post-Discharge",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    discharges = _find_qualifying_discharges(bundle, measurement_year)
    is_eligible = len(discharges) > 0

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="TRC",
            measure_name="Transitions of Care",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "TRC-1",
                    "display": "Notification of Inpatient Admission",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "TRC-2",
                    "display": "Receipt of Discharge Information",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "TRC-3",
                    "display": "Patient Engagement After Inpatient Discharge",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "TRC-4",
                    "display": "Medication Reconciliation Post-Discharge",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    all_evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in discharges)

    # Check exclusions
    is_excluded, excl_refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(excl_refs)

    # Indicators 1 & 2: Admin not available (always False for admin-only)
    r1_num = False
    r2_num = False

    # Indicator 3: Patient Engagement After Inpatient Discharge
    r3_num = False
    outpatient_codes = all_codes(VALUE_SETS, "Outpatient and Telehealth")
    tcm_codes = all_codes(VALUE_SETS, "Transitional Care Management Services")

    if not is_excluded:
        for enc, discharge_date in discharges:
            day_after = discharge_date + timedelta(days=1)
            window_end = discharge_date + timedelta(days=30)

            if outpatient_codes:
                matches = find_encounters_with_codes(
                    bundle, outpatient_codes, day_after, window_end
                )
                if matches:
                    all_evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
                    r3_num = True
                    break

            if not r3_num and tcm_codes:
                matches = find_encounters_with_codes(
                    bundle, tcm_codes, day_after, window_end
                )
                if matches:
                    all_evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
                    r3_num = True
                    break

    # Indicator 4: Medication Reconciliation Post-Discharge
    r4_num = False
    med_rec_enc_codes = all_codes(VALUE_SETS, "Medication Reconciliation Encounter")
    med_rec_int_codes = all_codes(VALUE_SETS, "Medication Reconciliation Intervention")

    if not is_excluded:
        for enc, discharge_date in discharges:
            window_end = discharge_date + timedelta(days=30)

            if med_rec_enc_codes:
                matches = find_encounters_with_codes(
                    bundle, med_rec_enc_codes, discharge_date, window_end
                )
                if matches:
                    all_evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
                    r4_num = True
                    break

            if not r4_num and med_rec_int_codes:
                proc_matches = find_procedures_with_codes(
                    bundle, med_rec_int_codes, discharge_date, window_end
                )
                if proc_matches:
                    all_evaluated.extend(
                        f"Procedure/{p.get('id')}" for p, _ in proc_matches
                    )
                    r4_num = True
                    break

    groups = [
        {
            "code": "TRC-1",
            "display": "Notification of Inpatient Admission",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r1_num,
        },
        {
            "code": "TRC-2",
            "display": "Receipt of Discharge Information",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r2_num,
        },
        {
            "code": "TRC-3",
            "display": "Patient Engagement After Inpatient Discharge",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r3_num,
        },
        {
            "code": "TRC-4",
            "display": "Medication Reconciliation Post-Discharge",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r4_num,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="TRC",
        measure_name="Transitions of Care",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
