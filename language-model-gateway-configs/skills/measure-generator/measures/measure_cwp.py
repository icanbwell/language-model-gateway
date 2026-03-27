"""
HEDIS MY 2025 - Appropriate Testing for Pharyngitis (CWP).

The percentage of episodes for members 3 years and older where the member was
diagnosed with pharyngitis, dispensed an antibiotic and received a group A
streptococcus (strep) test for the episode.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    calculate_age,
    resource_has_any_code,
    codeable_concept_has_any_code,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    find_medications_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("CWP")


def _get_intake_period(measurement_year: int) -> tuple[date, date]:
    """Intake period: July 1 prior year to June 30 measurement year."""
    return date(measurement_year - 1, 7, 1), date(measurement_year, 6, 30)


# ---------------------------------------------------------------------------
# Eligible Population
# ---------------------------------------------------------------------------


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Eligible population identification follows an episode-based approach:

    Step 1: Outpatient/ED/telehealth visit with pharyngitis diagnosis during
            the intake period (Jul 1 prior year - Jun 30 measurement year).
    Step 2: Determine pharyngitis episode dates.
    Step 3: Antibiotic dispensed on or up to 3 days after episode date.
    Step 4: Negative comorbid condition history (365 days prior to episode).
    Step 5: Negative medication history (30 days prior to episode).
    Step 6: Negative competing diagnosis (episode date + 3 days).
    Step 7: Continuous enrollment (simplified here).
    Step 8: Deduplicate episodes (31-day window).

    Member must be 3 years or older as of the episode date.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    intake_start, intake_end = _get_intake_period(measurement_year)

    # Step 1: Find outpatient/ED/telehealth encounters with pharyngitis
    encounter_codes = all_codes(VALUE_SETS, "Outpatient, ED and Telehealth")
    pharyngitis_codes = all_codes(VALUE_SETS, "Pharyngitis")
    if not encounter_codes or not pharyngitis_codes:
        return False, evaluated

    qualifying_encounters = find_encounters_with_codes(
        bundle, encounter_codes, intake_start, intake_end
    )

    # Filter to those with pharyngitis diagnosis
    episode_dates: list[tuple[date, dict]] = []
    for enc, enc_date in qualifying_encounters:
        if not enc_date:
            continue
        age_at_episode = calculate_age(birth_date, enc_date)
        if age_at_episode < 3:
            continue

        # Check if encounter has pharyngitis diagnosis
        has_pharyngitis = False
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, pharyngitis_codes):
                has_pharyngitis = True
                break
        if not has_pharyngitis and resource_has_any_code(enc, pharyngitis_codes):
            has_pharyngitis = True

        # Also check conditions linked to this encounter period
        if not has_pharyngitis:
            pharyngitis_conditions = find_conditions_with_codes(
                bundle, pharyngitis_codes, enc_date, enc_date
            )
            if pharyngitis_conditions:
                has_pharyngitis = True

        if has_pharyngitis:
            episode_dates.append((enc_date, enc))

    if not episode_dates:
        return False, evaluated

    # Step 2: Exclude visits resulting in inpatient stay
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")

    # Step 3: Check for antibiotic dispensed within 3 days
    # We use [Direct Reference] for CWP Antibiotic Medications
    antibiotic_codes = all_codes(VALUE_SETS, "[Direct Reference]")

    valid_episodes: list[tuple[date, dict]] = []
    for ep_date, enc in episode_dates:
        window_end = ep_date + timedelta(days=3)

        # Check antibiotic within 3 days
        has_antibiotic = False
        if antibiotic_codes:
            med_hits = find_medications_with_codes(
                bundle, antibiotic_codes, ep_date, window_end
            )
            if med_hits:
                has_antibiotic = True

        if not has_antibiotic:
            continue

        # Step 4: Negative comorbid condition history (365 days prior)
        comorbid_codes = all_codes(VALUE_SETS, "Comorbid Conditions")
        if comorbid_codes:
            lookback_start = ep_date - timedelta(days=365)
            comorbid_hits = find_conditions_with_codes(
                bundle, comorbid_codes, lookback_start, ep_date
            )
            if comorbid_hits:
                continue

        # Step 5: Negative medication history (30 days prior)
        if antibiotic_codes:
            med_lookback_start = ep_date - timedelta(days=30)
            med_lookback_end = ep_date - timedelta(days=1)
            prior_meds = find_medications_with_codes(
                bundle, antibiotic_codes, med_lookback_start, med_lookback_end
            )
            if prior_meds:
                continue

        # Step 6: Negative competing diagnosis
        competing_codes = all_codes(VALUE_SETS, "Competing Diagnosis")
        if competing_codes:
            competing_hits = find_conditions_with_codes(
                bundle, competing_codes, ep_date, window_end
            )
            if competing_hits:
                continue

        valid_episodes.append((ep_date, enc))

    if not valid_episodes:
        return False, evaluated

    # Step 8: Deduplicate (keep first episode per 31-day window)
    valid_episodes.sort(key=lambda x: x[0])
    deduped: list[tuple[date, dict]] = []
    last_date = None
    for ep_date, enc in valid_episodes:
        if last_date is None or (ep_date - last_date).days >= 31:
            deduped.append((ep_date, enc))
            last_date = ep_date

    if not deduped:
        return False, evaluated

    for _, enc in deduped:
        evaluated.append(f"Encounter/{enc.get('id')}")

    return True, evaluated


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Required exclusions: hospice, death.
    """
    return check_common_exclusions(
        bundle, VALUE_SETS, measurement_year, check_frailty=False
    )


# ---------------------------------------------------------------------------
# Numerator
# ---------------------------------------------------------------------------


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    A group A streptococcus test (Group A Strep Tests Value Set) in the 7-day
    period from 3 days prior to the episode date through 3 days after the
    episode date.

    For simplicity, we check all qualifying episodes and require at least
    one strep test within the window of any episode.
    """
    evaluated: list[str] = []

    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    intake_start, intake_end = _get_intake_period(measurement_year)

    strep_codes = all_codes(VALUE_SETS, "Group A Strep Tests")
    if not strep_codes:
        return False, evaluated

    # Re-identify episode dates (simplified: use all pharyngitis encounters
    # in intake period)
    encounter_codes = all_codes(VALUE_SETS, "Outpatient, ED and Telehealth")
    pharyngitis_codes = all_codes(VALUE_SETS, "Pharyngitis")
    if not encounter_codes or not pharyngitis_codes:
        return False, evaluated

    qualifying_encounters = find_encounters_with_codes(
        bundle, encounter_codes, intake_start, intake_end
    )

    for enc, enc_date in qualifying_encounters:
        if not enc_date:
            continue

        has_pharyngitis = False
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, pharyngitis_codes):
                has_pharyngitis = True
                break
        if not has_pharyngitis and resource_has_any_code(enc, pharyngitis_codes):
            has_pharyngitis = True
        if not has_pharyngitis:
            pharyngitis_conditions = find_conditions_with_codes(
                bundle, pharyngitis_codes, enc_date, enc_date
            )
            if pharyngitis_conditions:
                has_pharyngitis = True

        if not has_pharyngitis:
            continue

        # Check for strep test within 3 days before to 3 days after
        test_start = enc_date - timedelta(days=3)
        test_end = enc_date + timedelta(days=3)

        obs_hits = find_observations_with_codes(
            bundle, strep_codes, test_start, test_end
        )
        if obs_hits:
            for obs, _ in obs_hits:
                evaluated.append(f"Observation/{obs.get('id')}")
            return True, evaluated

        proc_hits = find_procedures_with_codes(
            bundle, strep_codes, test_start, test_end
        )
        if proc_hits:
            for proc, _ in proc_hits:
                evaluated.append(f"Procedure/{proc.get('id')}")
            return True, evaluated

    return False, evaluated


# ---------------------------------------------------------------------------
# Main Calculation
# ---------------------------------------------------------------------------


def calculate_cwp_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the CWP measure for an individual patient."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="CWP",
        measure_name="Appropriate Testing for Pharyngitis",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
