"""
HEDIS MY 2025 - Documented Assessment After Mammogram (DBM-E)

The percentage of episodes of mammograms documented in the form of a
BI-RADS assessment within 14 days of the mammogram for members 40-74
years of age.

This is an episode-based measure (denominator is episodes, not members).
"""

from __future__ import annotations

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    parse_date,
    is_date_in_range,
    resource_has_any_code,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("DBM-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_mammogram_episodes(
    bundle: dict,
    measurement_year: int,
) -> list[tuple[dict, date]]:
    """Find mammogram episodes during the intake period for members 40-74."""
    # Intake period: Dec 18 prior year to Dec 17 of MY
    intake_start = date(measurement_year - 1, 12, 18)
    intake_end = date(measurement_year, 12, 17)

    mammo_codes = all_codes(VALUE_SETS, "Mammography")
    if not mammo_codes:
        return []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return []

    episodes: list[tuple[dict, date]] = []

    # Check Procedures
    for proc, proc_date in find_procedures_with_codes(
        bundle, mammo_codes, intake_start, intake_end
    ):
        if proc_date:
            age_at_episode = calculate_age(birth_date, proc_date)
            if 40 <= age_at_episode <= 74:
                episodes.append((proc, proc_date))

    # Check Observations
    for obs, obs_date in find_observations_with_codes(
        bundle, mammo_codes, intake_start, intake_end
    ):
        if obs_date:
            age_at_episode = calculate_age(birth_date, obs_date)
            if 40 <= age_at_episode <= 74:
                episodes.append((obs, obs_date))

    # Check DiagnosticReports
    for dr in get_resources_by_type(bundle, "DiagnosticReport"):
        dr_date = parse_date(
            dr.get("effectiveDateTime")
            or (dr.get("effectivePeriod") or {}).get("start")
        )
        if dr_date and is_date_in_range(dr_date, intake_start, intake_end):
            if resource_has_any_code(dr, mammo_codes):
                age_at_episode = calculate_age(birth_date, dr_date)
                if 40 <= age_at_episode <= 74:
                    episodes.append((dr, dr_date))

    return episodes


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Episodes of mammograms during intake for members 40-74."""
    episodes = _find_mammogram_episodes(bundle, measurement_year)
    if episodes:
        refs = [
            f"{e.get('resourceType', 'Resource')}/{e.get('id')}" for e, _ in episodes
        ]
        return True, refs
    return False, []


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Death and hospice during MY."""
    return check_common_exclusions(
        bundle,
        VALUE_SETS,
        measurement_year,
        check_frailty=False,
    )


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """BI-RADS assessment on or within 14 days of the episode date."""
    evaluated: list[str] = []
    birads_codes = all_codes(VALUE_SETS, "BIRADS Assessment")
    if not birads_codes:
        return False, evaluated

    episodes = _find_mammogram_episodes(bundle, measurement_year)
    if not episodes:
        return False, evaluated

    for episode_resource, episode_date in episodes:
        window_end = episode_date + timedelta(days=14)

        # Check Observations for BIRADS
        for obs, obs_date in find_observations_with_codes(
            bundle,
            birads_codes,
            episode_date,
            window_end,
        ):
            evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

        # Check DiagnosticReports
        for dr in get_resources_by_type(bundle, "DiagnosticReport"):
            dr_date = parse_date(
                dr.get("effectiveDateTime")
                or (dr.get("effectivePeriod") or {}).get("start")
            )
            if dr_date and is_date_in_range(dr_date, episode_date, window_end):
                if resource_has_any_code(dr, birads_codes):
                    evaluated.append(f"DiagnosticReport/{dr.get('id')}")
                    return True, evaluated

        # Check Conditions (findings)
        found = find_conditions_with_codes(
            bundle, birads_codes, episode_date, window_end
        )
        if found:
            evaluated.append(f"Condition/{found[0][0].get('id')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_dbm_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate DBM-E measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="DBM-E",
        measure_name="Documented Assessment After Mammogram",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
