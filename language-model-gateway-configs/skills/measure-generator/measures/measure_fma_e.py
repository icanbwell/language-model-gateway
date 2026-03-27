"""
HEDIS MY 2025 - Follow-Up After Abnormal Mammogram Assessment (FMA-E)

The percentage of episodes for members 40-74 years of age with inconclusive
or high-risk BI-RADS assessments that received appropriate follow-up
within 90 days of the assessment.

Episode-based measure.
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
    get_condition_onset,
    get_observation_date,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("FMA-E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_abnormal_birads_episodes(
    bundle: dict,
    measurement_year: int,
) -> list[tuple[dict, date, str]]:
    """Find high-risk or inconclusive BI-RADS episodes during intake.

    Returns list of (resource, episode_date, birads_type) where
    birads_type is 'high_risk' or 'inconclusive'.

    Intake period: Oct 3 prior year to Oct 2 of MY.
    """
    intake_start = date(measurement_year - 1, 10, 3)
    intake_end = date(measurement_year, 10, 2)

    high_risk_codes = all_codes(VALUE_SETS, "High Risk BIRADS")
    inconclusive_codes = all_codes(VALUE_SETS, "Inconclusive BIRADS")

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return []

    episodes: list[tuple[dict, date, str]] = []

    def _check_resource(resource: dict, resource_date: date | None) -> None:
        if not resource_date or not is_date_in_range(
            resource_date, intake_start, intake_end
        ):
            return
        age = calculate_age(birth_date, resource_date)
        if not (40 <= age <= 74):
            return
        if resource_has_any_code(resource, high_risk_codes):
            episodes.append((resource, resource_date, "high_risk"))
        elif resource_has_any_code(resource, inconclusive_codes):
            episodes.append((resource, resource_date, "inconclusive"))

    for obs in get_resources_by_type(bundle, "Observation"):
        _check_resource(obs, get_observation_date(obs))

    for dr in get_resources_by_type(bundle, "DiagnosticReport"):
        dr_date = parse_date(
            dr.get("effectiveDateTime")
            or (dr.get("effectivePeriod") or {}).get("start")
        )
        _check_resource(dr, dr_date)

    for cond in get_resources_by_type(bundle, "Condition"):
        _check_resource(cond, get_condition_onset(cond))

    return episodes


# ---------------------------------------------------------------------------
# Eligible population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict,
    measurement_year: int,
) -> tuple[bool, list[str]]:
    """Episodes with high-risk or inconclusive BI-RADS for members 40-74."""
    episodes = _find_abnormal_birads_episodes(bundle, measurement_year)
    if episodes:
        refs = [
            f"{e.get('resourceType', 'Resource')}/{e.get('id')}" for e, _, _ in episodes
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
    """Appropriate follow-up within 90 days of abnormal BI-RADS.

    - High-risk: breast biopsy within 90 days.
    - Inconclusive: mammogram or breast ultrasound within 90 days.
    """
    evaluated: list[str] = []
    episodes = _find_abnormal_birads_episodes(bundle, measurement_year)
    if not episodes:
        return False, evaluated

    biopsy_codes = all_codes(VALUE_SETS, "Breast Biopsy")
    mammo_codes = all_codes(VALUE_SETS, "Mammography")
    ultrasound_codes = all_codes(VALUE_SETS, "Breast Ultrasound")

    for episode_resource, episode_date, birads_type in episodes:
        window_end = episode_date + timedelta(days=90)

        if birads_type == "high_risk" and biopsy_codes:
            found = find_procedures_with_codes(
                bundle, biopsy_codes, episode_date, window_end
            )
            if found:
                evaluated.append(f"Procedure/{found[0][0].get('id')}")
                return True, evaluated

        if birads_type == "inconclusive":
            if mammo_codes:
                found_proc = find_procedures_with_codes(
                    bundle, mammo_codes, episode_date, window_end
                )
                if found_proc:
                    evaluated.append(f"Procedure/{found_proc[0][0].get('id')}")
                    return True, evaluated
                found_obs = find_observations_with_codes(
                    bundle, mammo_codes, episode_date, window_end
                )
                if found_obs:
                    evaluated.append(f"Observation/{found_obs[0][0].get('id')}")
                    return True, evaluated
            if ultrasound_codes:
                found_proc = find_procedures_with_codes(
                    bundle, ultrasound_codes, episode_date, window_end
                )
                if found_proc:
                    evaluated.append(f"Procedure/{found_proc[0][0].get('id')}")
                    return True, evaluated
                found_obs = find_observations_with_codes(
                    bundle, ultrasound_codes, episode_date, window_end
                )
                if found_obs:
                    evaluated.append(f"Observation/{found_obs[0][0].get('id')}")
                    return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_fma_e_measure(
    bundle: dict,
    measurement_year: int = 2025,
) -> dict:
    """Calculate FMA-E measure."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="FMA-E",
        measure_name="Follow-Up After Abnormal Mammogram Assessment",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
