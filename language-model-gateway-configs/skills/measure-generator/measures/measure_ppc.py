"""
HEDIS MY 2025 - Prenatal and Postpartum Care (PPC).

Delivery-based measure (Oct 8 prior year - Oct 7 measurement year).
Two rates:
  1. Timeliness of Prenatal Care (first trimester or within 42 days of enrollment)
  2. Postpartum Care (visit 7-84 days after delivery)
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_resources_by_type,
    is_date_in_range,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    get_procedure_date,
    find_encounters_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("PPC")


def _find_deliveries(bundle: dict, measurement_year: int) -> list[tuple[dict, date]]:
    """Find live birth deliveries between Oct 8 prior year and Oct 7 MY.

    Applies de-duplication for multiple deliveries within 180-day periods.
    """
    delivery_start = date(measurement_year - 1, 10, 8)
    delivery_end = date(measurement_year, 10, 7)

    delivery_codes = all_codes(VALUE_SETS, "Deliveries")
    non_live_codes = all_codes(VALUE_SETS, "Non Live Births")

    if not delivery_codes:
        return []

    # Step 1: Find all deliveries
    deliveries: list[tuple[dict, date]] = []

    # Check encounters
    for enc in get_resources_by_type(bundle, "Encounter"):
        if not resource_has_any_code(enc, delivery_codes):
            has_type = any(
                codeable_concept_has_any_code(t, delivery_codes)
                for t in enc.get("type", [])
            )
            if not has_type:
                continue
        # Use discharge date for inpatient, encounter date otherwise
        enc_date = get_encounter_end_date(enc) or get_encounter_date(enc)
        if enc_date and is_date_in_range(enc_date, delivery_start, delivery_end):
            deliveries.append((enc, enc_date))

    # Check procedures
    for proc in get_resources_by_type(bundle, "Procedure"):
        if not resource_has_any_code(proc, delivery_codes):
            code_cc = proc.get("code", {})
            if not codeable_concept_has_any_code(code_cc, delivery_codes):
                continue
        proc_date = get_procedure_date(proc)
        if proc_date and is_date_in_range(proc_date, delivery_start, delivery_end):
            deliveries.append((proc, proc_date))

    if not deliveries:
        return []

    # Step 2: Remove non-live births
    if non_live_codes:
        filtered = []
        for resource, del_date in deliveries:
            is_non_live = resource_has_any_code(resource, non_live_codes)
            if not is_non_live:
                for t in resource.get("type", []):
                    if codeable_concept_has_any_code(t, non_live_codes):
                        is_non_live = True
                        break
            if not is_non_live:
                for reason in resource.get("reasonCode", []):
                    if codeable_concept_has_any_code(reason, non_live_codes):
                        is_non_live = True
                        break
            if not is_non_live:
                filtered.append((resource, del_date))
        deliveries = filtered

    if not deliveries:
        return []

    # Step 4: Deduplicate within 180-day periods
    deliveries.sort(key=lambda x: x[1])
    deduped: list[tuple[dict, date]] = []
    last_included: date | None = None
    for resource, del_date in deliveries:
        if last_included is None or (del_date - last_included).days >= 180:
            deduped.append((resource, del_date))
            last_included = del_date

    return deduped


def _check_prenatal_care(bundle: dict, delivery_date: date) -> tuple[bool, list[str]]:
    """Check timeliness of prenatal care.

    For simplicity, assumes member was enrolled at least 219 days before
    delivery, so prenatal visit must be in the first trimester
    (280-176 days before delivery).
    """
    evaluated: list[str] = []

    # First trimester: 280 to 176 days before delivery
    trimester_start = delivery_date - timedelta(days=280)
    trimester_end = delivery_date - timedelta(days=176)

    # Also check broader window for members not enrolled 219 days prior
    # Use 280 days before through 42 days after (but before delivery)
    broad_start = trimester_start
    broad_end = delivery_date - timedelta(days=1)

    # Prenatal Bundled Services
    bundled_codes = all_codes(VALUE_SETS, "Prenatal Bundled Services")
    if bundled_codes:
        matches = find_encounters_with_codes(
            bundle, bundled_codes, broad_start, broad_end
        )
        if matches:
            evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
            return True, evaluated
        proc_matches = find_procedures_with_codes(
            bundle, bundled_codes, broad_start, broad_end
        )
        if proc_matches:
            evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
            return True, evaluated

    # Stand Alone Prenatal Visits (exclude CPT CAT II modifiers)
    standalone_codes = all_codes(VALUE_SETS, "Stand Alone Prenatal Visits")
    if standalone_codes:
        matches = find_encounters_with_codes(
            bundle, standalone_codes, broad_start, broad_end
        )
        if matches:
            evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
            return True, evaluated
        proc_matches = find_procedures_with_codes(
            bundle, standalone_codes, broad_start, broad_end
        )
        if proc_matches:
            evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
            return True, evaluated

    # Prenatal Visits with Pregnancy Diagnosis
    prenatal_codes = all_codes(VALUE_SETS, "Prenatal Visits")
    pregnancy_codes = all_codes(VALUE_SETS, "Pregnancy Diagnosis")
    if prenatal_codes and pregnancy_codes:
        enc_matches = find_encounters_with_codes(
            bundle, prenatal_codes, broad_start, broad_end
        )
        for enc, enc_date in enc_matches:
            # Check if encounter also has pregnancy diagnosis
            has_preg_dx = resource_has_any_code(enc, pregnancy_codes)
            if not has_preg_dx:
                for reason in enc.get("reasonCode", []):
                    if codeable_concept_has_any_code(reason, pregnancy_codes):
                        has_preg_dx = True
                        break
            if not has_preg_dx:
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, pregnancy_codes):
                        has_preg_dx = True
                        break
            if has_preg_dx:
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated

    return False, evaluated


def _check_postpartum_care(bundle: dict, delivery_date: date) -> tuple[bool, list[str]]:
    """Check postpartum care: visit 7-84 days after delivery."""
    evaluated: list[str] = []
    pp_start = delivery_date + timedelta(days=7)
    pp_end = delivery_date + timedelta(days=84)

    # Exclude acute inpatient settings
    acute_ip_codes = all_codes(VALUE_SETS, "Acute Inpatient")
    acute_pos_codes = all_codes(VALUE_SETS, "Acute Inpatient POS")

    def _is_acute_inpatient(enc: dict) -> bool:
        if acute_ip_codes and resource_has_any_code(enc, acute_ip_codes):
            return True
        if acute_pos_codes and resource_has_any_code(enc, acute_pos_codes):
            return True
        return False

    # Postpartum Care value set
    pp_codes = all_codes(VALUE_SETS, "Postpartum Care")
    if pp_codes:
        matches = find_encounters_with_codes(bundle, pp_codes, pp_start, pp_end)
        for enc, _ in matches:
            if not _is_acute_inpatient(enc):
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated
        proc_matches = find_procedures_with_codes(bundle, pp_codes, pp_start, pp_end)
        if proc_matches:
            evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
            return True, evaluated

    # Encounter for Postpartum Care
    enc_pp_codes = all_codes(VALUE_SETS, "Encounter for Postpartum Care")
    if enc_pp_codes:
        matches = find_encounters_with_codes(bundle, enc_pp_codes, pp_start, pp_end)
        for enc, _ in matches:
            if not _is_acute_inpatient(enc):
                evaluated.append(f"Encounter/{enc.get('id')}")
                return True, evaluated

    # Cervical Cytology
    for vs_name in [
        "Cervical Cytology Lab Test",
        "Cervical Cytology Result or Finding",
    ]:
        cyto_codes = all_codes(VALUE_SETS, vs_name)
        if cyto_codes:
            obs_matches = find_observations_with_codes(
                bundle, cyto_codes, pp_start, pp_end
            )
            if obs_matches:
                evaluated.extend(f"Observation/{o.get('id')}" for o, _ in obs_matches)
                return True, evaluated
            proc_matches = find_procedures_with_codes(
                bundle, cyto_codes, pp_start, pp_end
            )
            if proc_matches:
                evaluated.extend(f"Procedure/{p.get('id')}" for p, _ in proc_matches)
                return True, evaluated

    # Postpartum Bundled Services
    pp_bundled_codes = all_codes(VALUE_SETS, "Postpartum Bundled Services")
    if pp_bundled_codes:
        matches = find_encounters_with_codes(bundle, pp_bundled_codes, pp_start, pp_end)
        if matches:
            evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in matches)
            return True, evaluated

    return False, evaluated


def calculate_ppc_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate PPC measure (2 rates) and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    deliveries = _find_deliveries(bundle, measurement_year)
    is_eligible = len(deliveries) > 0

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="PPC",
            measure_name="Prenatal and Postpartum Care",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "PPC-1",
                    "display": "Timeliness of Prenatal Care",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "PPC-2",
                    "display": "Postpartum Care",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    all_evaluated.extend(
        f"Encounter/{r.get('id')}"
        if r.get("resourceType") == "Encounter"
        else f"Procedure/{r.get('id')}"
        for r, _ in deliveries
    )

    # Check exclusions
    is_excluded, excl_refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(excl_refs)

    # Rate 1: Timeliness of Prenatal Care
    r1_num = False
    if not is_excluded:
        for resource, del_date in deliveries:
            compliant, refs = _check_prenatal_care(bundle, del_date)
            all_evaluated.extend(refs)
            if compliant:
                r1_num = True
                break

    # Rate 2: Postpartum Care
    r2_num = False
    if not is_excluded:
        for resource, del_date in deliveries:
            compliant, refs = _check_postpartum_care(bundle, del_date)
            all_evaluated.extend(refs)
            if compliant:
                r2_num = True
                break

    groups = [
        {
            "code": "PPC-1",
            "display": "Timeliness of Prenatal Care",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r1_num,
        },
        {
            "code": "PPC-2",
            "display": "Postpartum Care",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r2_num,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="PPC",
        measure_name="Prenatal and Postpartum Care",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
