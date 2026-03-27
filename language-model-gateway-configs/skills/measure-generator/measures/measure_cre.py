"""
HEDIS MY 2025 - Cardiac Rehabilitation (CRE)

The percentage of members 18 years and older who attended cardiac rehabilitation
following a qualifying cardiac event. Four rates are reported:
  - Initiation: >= 2 sessions within 30 days after the episode date.
  - Engagement 1: >= 12 sessions within 90 days after the episode date.
  - Engagement 2: >= 24 sessions within 180 days after the episode date.
  - Achievement: >= 36 sessions within 180 days after the episode date.

Qualifying events: MI, CABG, PCI, heart/heart-lung transplant, heart valve
repair/replacement during the intake period (July 1 PY through June 30 MY).
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    check_common_exclusions,
    get_patient_id,
    get_patient_birth_date,
    calculate_age,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    build_multi_rate_measure_report,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("CRE")

# Qualifying cardiac event value set names
CARDIAC_EVENT_VS_NAMES = [
    "MI",
    "CABG",
    "Percutaneous CABG",
    "PCI",
    "Other PCI",
    "Heart Transplant",
    "Heart Valve Repair or Replacement",
]


def _get_intake_period(measurement_year: int) -> tuple[date, date]:
    """Return the intake period: July 1 PY through June 30 MY."""
    return date(measurement_year - 1, 7, 1), date(measurement_year, 6, 30)


def _find_episode_date(bundle: dict, measurement_year: int) -> date | None:
    """
    Find the most recent qualifying cardiac event during the intake period.

    For inpatient events (MI, CABG, transplant, valve), the episode date is
    the discharge date. For PCI, the episode date is the date of service.
    Returns the most recent qualifying episode date.
    """
    intake_start, intake_end = _get_intake_period(measurement_year)
    episode_dates: list[date] = []

    # Inpatient events: MI, CABG, Heart Transplant, Heart Valve Repair
    inpatient_vs_names = [
        "MI",
        "CABG",
        "Percutaneous CABG",
        "Heart Transplant",
        "Heart Valve Repair or Replacement",
    ]
    for vs_name in inpatient_vs_names:
        codes = all_codes(VALUE_SETS, vs_name)
        if not codes:
            continue
        # Check conditions (MI) and procedures (CABG, etc.)
        for cond, onset in find_conditions_with_codes(
            bundle, codes, intake_start, intake_end
        ):
            if onset:
                episode_dates.append(onset)
        for proc, proc_date in find_procedures_with_codes(
            bundle, codes, intake_start, intake_end
        ):
            if proc_date:
                episode_dates.append(proc_date)

    # PCI events (date of service)
    for vs_name in ("PCI", "Other PCI"):
        codes = all_codes(VALUE_SETS, vs_name)
        if not codes:
            continue
        for proc, proc_date in find_procedures_with_codes(
            bundle, codes, intake_start, intake_end
        ):
            if proc_date:
                episode_dates.append(proc_date)

    if not episode_dates:
        return None
    return max(episode_dates)  # Most recent


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check CRE eligible population:
    - Age >= 18 as of the episode date
    - Had a qualifying cardiac event during the intake period
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    episode_date = _find_episode_date(bundle, measurement_year)
    if episode_date is None:
        return False, evaluated

    age = calculate_age(birth_date, episode_date)
    if age < 18:
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check CRE exclusions:
    - Common exclusions (hospice, death, palliative care, frailty/advanced illness)
    - Another qualifying cardiac event within 180 days after the episode date
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    episode_date = _find_episode_date(bundle, measurement_year)
    if episode_date is None:
        return False, refs

    # Exclude if there is another cardiac event in the 180 days after the episode
    post_start = episode_date + timedelta(days=1)
    post_end = episode_date + timedelta(days=180)

    for vs_name in CARDIAC_EVENT_VS_NAMES:
        codes = all_codes(VALUE_SETS, vs_name)
        if not codes:
            continue
        if find_conditions_with_codes(bundle, codes, post_start, post_end):
            return True, refs
        if find_procedures_with_codes(bundle, codes, post_start, post_end):
            return True, refs

    return False, refs


def _count_rehab_sessions(
    bundle: dict,
    episode_date: date,
    window_days: int,
) -> int:
    """
    Count cardiac rehabilitation sessions within a window after the episode date.

    Window includes the episode date itself (e.g., 30-day window = episode date + 30 days = 31 total).
    Multiple sessions on the same date count as multiple sessions.
    """
    window_start = episode_date
    window_end = episode_date + timedelta(days=window_days)

    rehab_codes = all_codes(VALUE_SETS, "Cardiac Rehabilitation")
    if not rehab_codes:
        return 0

    session_count = 0
    # Check procedures
    for proc, proc_date in find_procedures_with_codes(
        bundle, rehab_codes, window_start, window_end
    ):
        session_count += 1

    # Check encounters
    for enc, enc_date in find_encounters_with_codes(
        bundle, rehab_codes, window_start, window_end
    ):
        session_count += 1

    return session_count


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check CRE Initiation numerator (>= 2 sessions within 30 days)."""
    evaluated: list[str] = []
    episode_date = _find_episode_date(bundle, measurement_year)
    if episode_date is None:
        return False, evaluated

    sessions = _count_rehab_sessions(bundle, episode_date, 30)
    return sessions >= 2, evaluated


def calculate_cre_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the CRE measure (all four rates) for a patient bundle."""
    all_evaluated: list[str] = []

    is_eligible, eligible_refs = check_eligible_population(bundle, measurement_year)
    all_evaluated.extend(eligible_refs)

    is_excluded = False
    if is_eligible:
        is_excluded, exclusion_refs = check_exclusions(bundle, measurement_year)
        all_evaluated.extend(exclusion_refs)

    episode_date = _find_episode_date(bundle, measurement_year)

    initiation = False
    engagement1 = False
    engagement2 = False
    achievement = False

    if is_eligible and episode_date:
        initiation = _count_rehab_sessions(bundle, episode_date, 30) >= 2
        engagement1 = _count_rehab_sessions(bundle, episode_date, 90) >= 12
        engagement2 = _count_rehab_sessions(bundle, episode_date, 180) >= 24
        achievement = _count_rehab_sessions(bundle, episode_date, 180) >= 36

    groups = [
        {
            "code": "CRE-Initiation",
            "display": "Initiation (>=2 sessions within 30 days)",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": initiation,
        },
        {
            "code": "CRE-Engagement1",
            "display": "Engagement 1 (>=12 sessions within 90 days)",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": engagement1,
        },
        {
            "code": "CRE-Engagement2",
            "display": "Engagement 2 (>=24 sessions within 180 days)",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": engagement2,
        },
        {
            "code": "CRE-Achievement",
            "display": "Achievement (>=36 sessions within 180 days)",
            "initial_population": is_eligible,
            "denominator_exclusion": is_excluded,
            "numerator": achievement,
        },
    ]

    return build_multi_rate_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="CRE",
        measure_name="Cardiac Rehabilitation",
        measurement_year=measurement_year,
        groups=groups,
        evaluated_resources=list(dict.fromkeys(all_evaluated)),
    )
