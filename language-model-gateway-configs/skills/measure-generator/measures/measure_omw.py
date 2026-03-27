"""
HEDIS MY 2025 - Osteoporosis Management in Women Who Had a Fracture (OMW)

The percentage of women 67-85 years of age who suffered a fracture and who had
either a bone mineral density (BMD) test or prescription for a drug to treat
osteoporosis in the 180 days (6 months) after the fracture.

Intake period: July 1 PY through June 30 MY. Uses the earliest eligible fracture
episode (IESD) after applying negative diagnosis history, continuous enrollment,
and prior treatment/testing exclusions.
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_patient_gender,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_end_date,
    get_medication_date,
    find_encounters_with_codes,
    find_conditions_with_codes,
    find_procedures_with_codes,
    find_observations_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("OMW")


def _get_intake_period(measurement_year: int) -> tuple[date, date]:
    """Return the intake period: July 1 PY through June 30 MY."""
    return date(measurement_year - 1, 7, 1), date(measurement_year, 6, 30)


def _find_fracture_episodes(bundle: dict, measurement_year: int) -> list[date]:
    """
    Find all fracture episode dates during the intake period.

    For outpatient/ED visits, the episode date is the date of service.
    For inpatient stays, the episode date is the discharge date.
    """
    intake_start, intake_end = _get_intake_period(measurement_year)
    fracture_codes = all_codes(VALUE_SETS, "Fractures")
    if not fracture_codes:
        return []

    episode_dates: list[date] = []

    # Outpatient/ED visits with fracture
    outpatient_codes = all_codes(VALUE_SETS, "Outpatient and ED")
    if outpatient_codes:
        for enc, enc_date in find_encounters_with_codes(
            bundle, outpatient_codes, intake_start, intake_end
        ):
            # Check for fracture diagnosis on encounter
            for diag in enc.get("diagnosis", []):
                cc = diag.get("condition", {})
                if codeable_concept_has_any_code(cc, fracture_codes):
                    if enc_date:
                        episode_dates.append(enc_date)
                    break

    # Inpatient stays with fracture on discharge claim
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    if inpatient_codes:
        encounters = get_resources_by_type(bundle, "Encounter")
        for enc in encounters:
            if not resource_has_any_code(enc, inpatient_codes):
                is_inpatient = False
                for t in enc.get("type", []):
                    if codeable_concept_has_any_code(t, inpatient_codes):
                        is_inpatient = True
                        break
                if not is_inpatient:
                    continue

            discharge_date = get_encounter_end_date(enc)
            if not discharge_date or not is_date_in_range(
                discharge_date, intake_start, intake_end
            ):
                continue

            # Check fracture diagnosis
            for diag in enc.get("diagnosis", []):
                cc = diag.get("condition", {})
                if codeable_concept_has_any_code(cc, fracture_codes):
                    episode_dates.append(discharge_date)
                    break

    # Also check conditions directly
    for cond, onset in find_conditions_with_codes(
        bundle, fracture_codes, intake_start, intake_end
    ):
        if onset:
            episode_dates.append(onset)

    return sorted(set(episode_dates))


def _apply_negative_history(
    episode_dates: list[date],
    bundle: dict,
    measurement_year: int,
) -> list[date]:
    """
    Remove episodes where the member had a fracture in the 60 days prior.
    """
    fracture_codes = all_codes(VALUE_SETS, "Fractures")
    if not fracture_codes:
        return episode_dates

    filtered: list[date] = []
    for ep_date in episode_dates:
        lookback_start = ep_date - timedelta(days=60)
        lookback_end = ep_date - timedelta(days=1)
        prior_fractures = find_conditions_with_codes(
            bundle, fracture_codes, lookback_start, lookback_end
        )
        if not prior_fractures:
            filtered.append(ep_date)

    return filtered


def _apply_prior_treatment_exclusion(
    episode_dates: list[date],
    bundle: dict,
    measurement_year: int,
) -> list[date]:
    """
    Remove episodes where the member had prior BMD test (730 days) or
    osteoporosis treatment (365 days) before the episode.
    """
    filtered: list[date] = []

    bmd_codes = all_codes(VALUE_SETS, "Bone Mineral Density Tests")
    osteo_therapy_codes = all_codes(VALUE_SETS, "Osteoporosis Medication Therapy")

    for ep_date in episode_dates:
        excluded = False

        # BMD test in prior 730 days
        if bmd_codes:
            bmd_start = ep_date - timedelta(days=730)
            bmd_end = ep_date - timedelta(days=1)
            if find_procedures_with_codes(bundle, bmd_codes, bmd_start, bmd_end):
                excluded = True
            if not excluded and find_observations_with_codes(
                bundle, bmd_codes, bmd_start, bmd_end
            ):
                excluded = True

        # Osteoporosis therapy in prior 365 days
        if not excluded and osteo_therapy_codes:
            therapy_start = ep_date - timedelta(days=365)
            therapy_end = ep_date - timedelta(days=1)
            if find_procedures_with_codes(
                bundle, osteo_therapy_codes, therapy_start, therapy_end
            ):
                excluded = True

        # Osteoporosis medication in prior 365 days
        if not excluded:
            med_start = ep_date - timedelta(days=365)
            med_end = ep_date - timedelta(days=1)
            for rtype in ("MedicationDispense", "MedicationRequest"):
                for med in get_resources_by_type(bundle, rtype):
                    med_date = get_medication_date(med)
                    if med_date and is_date_in_range(med_date, med_start, med_end):
                        excluded = True
                        break
                if excluded:
                    break

        if not excluded:
            filtered.append(ep_date)

    return filtered


def _find_iesd(bundle: dict, measurement_year: int) -> date | None:
    """Find the IESD (earliest eligible fracture episode date)."""
    episodes = _find_fracture_episodes(bundle, measurement_year)
    if not episodes:
        return None

    episodes = _apply_negative_history(episodes, bundle, measurement_year)
    if not episodes:
        return None

    episodes = _apply_prior_treatment_exclusion(episodes, bundle, measurement_year)
    if not episodes:
        return None

    return min(episodes)


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check OMW eligible population:
    - Women 67-85 as of Dec 31 of MY
    - Had a qualifying fracture during the intake period (IESD exists)
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    gender = get_patient_gender(bundle)
    if not birth_date or gender != "female":
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if not (67 <= age <= 85):
        return False, evaluated

    iesd = _find_iesd(bundle, measurement_year)
    if iesd is None:
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """Check OMW exclusions (common exclusions)."""
    return check_common_exclusions(bundle, VALUE_SETS, measurement_year)


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check OMW numerator: BMD test or osteoporosis medication/therapy
    on the IESD or within 180 days after the IESD.
    """
    evaluated: list[str] = []
    iesd = _find_iesd(bundle, measurement_year)
    if iesd is None:
        return False, evaluated

    window_start = iesd
    window_end = iesd + timedelta(days=180)

    # BMD test
    bmd_codes = all_codes(VALUE_SETS, "Bone Mineral Density Tests")
    if bmd_codes:
        if find_procedures_with_codes(bundle, bmd_codes, window_start, window_end):
            return True, evaluated
        if find_observations_with_codes(bundle, bmd_codes, window_start, window_end):
            return True, evaluated

    # Osteoporosis medication therapy
    osteo_therapy_codes = all_codes(VALUE_SETS, "Osteoporosis Medication Therapy")
    if osteo_therapy_codes:
        if find_procedures_with_codes(
            bundle, osteo_therapy_codes, window_start, window_end
        ):
            return True, evaluated

    # Long-acting osteoporosis medications
    long_acting_codes = all_codes(VALUE_SETS, "Long Acting Osteoporosis Medications")
    if long_acting_codes:
        if find_procedures_with_codes(
            bundle, long_acting_codes, window_start, window_end
        ):
            return True, evaluated

    # Dispensed osteoporosis medication
    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if med_date and is_date_in_range(med_date, window_start, window_end):
                return True, evaluated

    return False, evaluated


def calculate_omw_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the OMW measure for a patient bundle."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="OMW",
        measure_name="Osteoporosis Management in Women Who Had a Fracture",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
