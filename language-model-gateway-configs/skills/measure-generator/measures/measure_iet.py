"""
HEDIS MY 2025 - Initiation and Engagement of Substance Use Disorder
Treatment (IET).

Episode-based measure for members 13+ with a new SUD episode. Two rates:
  1. Initiation of SUD Treatment (within 14 days of SUD episode date)
  2. Engagement of SUD Treatment (2+ events within 34 days of initiation)

Intake period: Nov 15 prior year - Nov 14 measurement year.
194-day negative diagnosis/medication history required.
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
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_date,
    get_encounter_end_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_medications_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("IET")

# SUD diagnosis value set names
_SUD_DIAGNOSIS_VS = [
    "Alcohol Abuse and Dependence",
    "Opioid Abuse and Dependence",
    "Other Drug Abuse and Dependence",
]

# Visit type value set names that can qualify as SUD episode encounters
_EPISODE_VISIT_VS = [
    "Visit Setting Unspecified",
    "BH Outpatient",
    "Partial Hospitalization or Intensive Outpatient",
    "Substance Use Disorder Services",
    "Substance Abuse Counseling and Surveillance",
    "ED",
    "Telephone Visits",
    "Online Assessments",
    "OUD Weekly Non Drug Service",
    "OUD Monthly Office Based Treatment",
    "OUD Weekly Drug Treatment Service",
    "Detoxification",
]

# SUD medication value set names for negative medication history
_SUD_MED_VS = [
    "Naltrexone Injection",
    "Buprenorphine Oral",
    "Buprenorphine Oral Weekly",
    "Buprenorphine Injection",
    "Buprenorphine Implant",
    "Buprenorphine Naloxone",
    "Methadone Oral",
    "Methadone Oral Weekly",
]


def _get_all_sud_diag_codes() -> dict[str, set[str]]:
    """Aggregate all SUD diagnosis codes."""
    combined: dict[str, set[str]] = {}
    for vs_name in _SUD_DIAGNOSIS_VS:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _get_all_visit_codes() -> dict[str, set[str]]:
    """Aggregate all visit type codes for episode identification."""
    combined: dict[str, set[str]] = {}
    for vs_name in _EPISODE_VISIT_VS:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _get_all_sud_med_codes() -> dict[str, set[str]]:
    """Aggregate all SUD medication codes."""
    combined: dict[str, set[str]] = {}
    for vs_name in _SUD_MED_VS:
        for system, codes in all_codes(VALUE_SETS, vs_name).items():
            combined.setdefault(system, set()).update(codes)
    return combined


def _encounter_has_sud_diagnosis(enc: dict) -> bool:
    """Check if an encounter has any SUD diagnosis code."""
    sud_codes = _get_all_sud_diag_codes()
    if not sud_codes:
        return False
    if resource_has_any_code(enc, sud_codes):
        return True
    for t in enc.get("type", []):
        if codeable_concept_has_any_code(t, sud_codes):
            return True
    for reason in enc.get("reasonCode", []):
        if codeable_concept_has_any_code(reason, sud_codes):
            return True
    return False


def _find_sud_episodes(bundle: dict, measurement_year: int) -> list[tuple[dict, date]]:
    """Find new SUD episodes during the intake period.

    Applies negative diagnosis history (194 days) and negative medication
    history (194 days), then deduplicates same-day episodes.
    """
    intake_start = date(measurement_year - 1, 11, 15)
    intake_end = date(measurement_year, 11, 14)
    birth_date = get_patient_birth_date(bundle)

    visit_codes = _get_all_visit_codes()
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")

    # Step 1: Identify all SUD episodes
    episodes: list[tuple[dict, date]] = []
    for enc in get_resources_by_type(bundle, "Encounter"):
        enc_date = get_encounter_date(enc)
        if not enc_date:
            continue
        if not is_date_in_range(enc_date, intake_start, intake_end):
            # For inpatient, use discharge date
            discharge = get_encounter_end_date(enc)
            if not discharge or not is_date_in_range(
                discharge, intake_start, intake_end
            ):
                continue
            # Inpatient discharge is the episode date
            if not _encounter_has_sud_diagnosis(enc):
                continue
            if birth_date and calculate_age(birth_date, discharge) < 13:
                continue
            episodes.append((enc, discharge))
            continue

        if not _encounter_has_sud_diagnosis(enc):
            continue

        # Check if this is an inpatient stay -- use discharge date
        is_inpatient = False
        if inpatient_codes and resource_has_any_code(enc, inpatient_codes):
            is_inpatient = True
        if not is_inpatient and inpatient_codes:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, inpatient_codes):
                    is_inpatient = True
                    break

        if is_inpatient:
            discharge = get_encounter_end_date(enc) or enc_date
            episode_date = discharge
        else:
            episode_date = enc_date

        if birth_date and calculate_age(birth_date, episode_date) < 13:
            continue

        episodes.append((enc, episode_date))

    if not episodes:
        return []

    # Step 2: Negative SUD diagnosis history (194 days prior)
    sud_codes = _get_all_sud_diag_codes()
    # Exclude ED and Detoxification from history check per spec
    ed_codes = all_codes(VALUE_SETS, "ED")
    detox_codes = all_codes(VALUE_SETS, "Detoxification")

    filtered: list[tuple[dict, date]] = []
    for enc, ep_date in episodes:
        lookback_start = ep_date - timedelta(days=194)
        lookback_end = ep_date - timedelta(days=1)

        has_prior_dx = False
        if sud_codes:
            # Check encounters with SUD diagnosis in lookback
            prior_encs = find_encounters_with_codes(
                bundle, sud_codes, lookback_start, lookback_end
            )
            # Exclude ED and detoxification encounters from history
            for prior_enc, _ in prior_encs:
                is_ed = ed_codes and resource_has_any_code(prior_enc, ed_codes)
                is_detox = detox_codes and resource_has_any_code(prior_enc, detox_codes)
                if not is_ed and not is_detox:
                    has_prior_dx = True
                    break
            if not has_prior_dx:
                prior_conds = find_conditions_with_codes(
                    bundle, sud_codes, lookback_start, lookback_end
                )
                if prior_conds:
                    has_prior_dx = True

        if not has_prior_dx:
            filtered.append((enc, ep_date))

    episodes = filtered
    if not episodes:
        return []

    # Step 3: Negative SUD medication history (194 days prior)
    sud_med_codes = _get_all_sud_med_codes()
    if sud_med_codes:
        filtered = []
        for enc, ep_date in episodes:
            lookback_start = ep_date - timedelta(days=194)
            lookback_end = ep_date - timedelta(days=1)
            prior_meds = find_medications_with_codes(
                bundle, sud_med_codes, lookback_start, lookback_end
            )
            if not prior_meds:
                filtered.append((enc, ep_date))
        episodes = filtered

    if not episodes:
        return []

    # Step 5: Deduplicate same-day episodes
    episodes.sort(key=lambda x: x[1])
    seen_dates: set[date] = set()
    deduped: list[tuple[dict, date]] = []
    for enc, ep_date in episodes:
        if ep_date not in seen_dates:
            deduped.append((enc, ep_date))
            seen_dates.add(ep_date)

    return deduped


def _check_initiation(
    bundle: dict, enc: dict, ep_date: date, measurement_year: int
) -> tuple[bool, date | None, list[str]]:
    """Check if SUD episode has initiation within 14 days.

    Returns (is_compliant, initiation_date, evaluated_refs).
    """
    evaluated: list[str] = []
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")

    # Step 1: If inpatient discharge, automatically compliant
    is_inpatient = False
    if inpatient_codes:
        if resource_has_any_code(enc, inpatient_codes):
            is_inpatient = True
        if not is_inpatient:
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, inpatient_codes):
                    is_inpatient = True
                    break
    if is_inpatient:
        evaluated.append(f"Encounter/{enc.get('id')}")
        return True, ep_date, evaluated

    # Step 2: Monthly OUD treatment service
    oud_monthly_codes = all_codes(VALUE_SETS, "OUD Monthly Office Based Treatment")
    if oud_monthly_codes and resource_has_any_code(enc, oud_monthly_codes):
        evaluated.append(f"Encounter/{enc.get('id')}")
        return True, ep_date, evaluated

    # Step 3: Treatment within 14 days (episode date + 13 days after)
    window_end = ep_date + timedelta(days=13)

    # Check encounters with SUD diagnosis
    visit_codes = _get_all_visit_codes()
    sud_codes = _get_all_sud_diag_codes()
    if visit_codes:
        matches = find_encounters_with_codes(bundle, visit_codes, ep_date, window_end)
        for m_enc, m_date in matches:
            if m_enc.get("id") == enc.get("id") and m_date == ep_date:
                # Same-day same-provider doesn't count (except meds)
                continue
            if _encounter_has_sud_diagnosis(m_enc):
                evaluated.append(f"Encounter/{m_enc.get('id')}")
                return True, m_date, evaluated

    # Check inpatient admissions with SUD diagnosis
    if inpatient_codes and sud_codes:
        ip_matches = find_encounters_with_codes(
            bundle, inpatient_codes, ep_date, window_end
        )
        for ip_enc, ip_date in ip_matches:
            if _encounter_has_sud_diagnosis(ip_enc):
                evaluated.append(f"Encounter/{ip_enc.get('id')}")
                return True, ip_date, evaluated

    # Check OUD treatment services
    for vs_name in [
        "OUD Weekly Non Drug Service",
        "OUD Monthly Office Based Treatment",
        "OUD Weekly Drug Treatment Service",
    ]:
        oud_codes = all_codes(VALUE_SETS, vs_name)
        if oud_codes:
            matches = find_encounters_with_codes(bundle, oud_codes, ep_date, window_end)
            if matches:
                evaluated.extend(f"Encounter/{m.get('id')}" for m, _ in matches)
                return True, matches[0][1], evaluated

    # Check medication dispensing/administration
    sud_med_codes = _get_all_sud_med_codes()
    if sud_med_codes:
        med_matches = find_medications_with_codes(
            bundle, sud_med_codes, ep_date, window_end
        )
        if med_matches:
            evaluated.extend(
                f"MedicationDispense/{m.get('id')}" for m, _ in med_matches
            )
            return True, med_matches[0][1], evaluated

    return False, None, evaluated


def _check_engagement(
    bundle: dict, initiation_date: date, measurement_year: int
) -> tuple[bool, list[str]]:
    """Check engagement: 2+ events in 34 days after initiation.

    The 34-day period begins the day after initiation.
    """
    evaluated: list[str] = []
    eng_start = initiation_date + timedelta(days=1)
    eng_end = initiation_date + timedelta(days=34)

    event_count = 0

    # Check for OUD monthly/weekly treatment with medication
    for vs_name in [
        "OUD Monthly Office Based Treatment",
        "OUD Weekly Drug Treatment Service",
    ]:
        oud_codes = all_codes(VALUE_SETS, vs_name)
        if oud_codes:
            matches = find_encounters_with_codes(bundle, oud_codes, eng_start, eng_end)
            if matches:
                evaluated.extend(f"Encounter/{m.get('id')}" for m, _ in matches)
                return True, evaluated

    # Check long-acting medication (single event suffices)
    for vs_name in [
        "Naltrexone Injection",
        "Buprenorphine Injection",
        "Buprenorphine Implant",
    ]:
        la_codes = all_codes(VALUE_SETS, vs_name)
        if la_codes:
            med_matches = find_medications_with_codes(
                bundle, la_codes, eng_start, eng_end
            )
            if med_matches:
                evaluated.extend(
                    f"MedicationDispense/{m.get('id')}" for m, _ in med_matches
                )
                return True, evaluated

    # Count engagement visits
    visit_codes = _get_all_visit_codes()
    if visit_codes:
        matches = find_encounters_with_codes(bundle, visit_codes, eng_start, eng_end)
        for m_enc, _ in matches:
            if _encounter_has_sud_diagnosis(m_enc):
                event_count += 1
                evaluated.append(f"Encounter/{m_enc.get('id')}")

    # Count engagement medication treatment events
    sud_med_codes = _get_all_sud_med_codes()
    if sud_med_codes:
        med_matches = find_medications_with_codes(
            bundle, sud_med_codes, eng_start, eng_end
        )
        event_count += len(med_matches)
        evaluated.extend(f"MedicationDispense/{m.get('id')}" for m, _ in med_matches)

    return event_count >= 2, evaluated


def calculate_iet_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate IET measure (2 rates) and return a FHIR MeasureReport."""
    patient_id = get_patient_id(bundle)
    all_evaluated: list[str] = []

    episodes = _find_sud_episodes(bundle, measurement_year)
    is_eligible = len(episodes) > 0

    if is_eligible:
        all_evaluated.extend(f"Encounter/{e.get('id')}" for e, _ in episodes)

    if not is_eligible:
        return build_multi_rate_measure_report(
            patient_id=patient_id,
            measure_abbreviation="IET",
            measure_name="Initiation and Engagement of SUD Treatment",
            measurement_year=measurement_year,
            groups=[
                {
                    "code": "IET-1",
                    "display": "Initiation of SUD Treatment",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
                {
                    "code": "IET-2",
                    "display": "Engagement of SUD Treatment",
                    "initial_population": False,
                    "denominator_exclusion": False,
                    "numerator": False,
                },
            ],
            evaluated_resources=[],
        )

    # Check exclusions
    is_excluded, excl_refs = check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )
    all_evaluated.extend(excl_refs)

    # Check initiation (Rate 1)
    r1_num = False
    r2_num = False
    initiation_date: date | None = None

    if not is_excluded:
        for enc, ep_date in episodes:
            compliant, init_date, init_refs = _check_initiation(
                bundle, enc, ep_date, measurement_year
            )
            all_evaluated.extend(init_refs)
            if compliant and init_date:
                r1_num = True
                initiation_date = init_date
                break

        # Check engagement (Rate 2) -- only if initiation was met
        if r1_num and initiation_date:
            eng_compliant, eng_refs = _check_engagement(
                bundle, initiation_date, measurement_year
            )
            all_evaluated.extend(eng_refs)
            r2_num = eng_compliant

    groups = [
        {
            "code": "IET-1",
            "display": "Initiation of SUD Treatment",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r1_num,
        },
        {
            "code": "IET-2",
            "display": "Engagement of SUD Treatment",
            "initial_population": True,
            "denominator_exclusion": is_excluded,
            "numerator": r2_num,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=patient_id,
        measure_abbreviation="IET",
        measure_name="Initiation and Engagement of SUD Treatment",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
