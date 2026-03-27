"""
HEDIS MY 2025 - Persistence of Beta-Blocker Treatment After a Heart Attack (PBH)

The percentage of members 18 years of age and older during the measurement year
who were hospitalized and discharged with a diagnosis of AMI (from July 1 of the
year prior to the measurement year to June 30 of the measurement year) and who
received persistent beta-blocker treatment for 180 days (6 months) after discharge.

Numerator: At least 135 covered days of beta-blocker therapy during the 180-day
measurement interval following discharge (allows up to 45 gap days).
"""

from datetime import date, timedelta

from .hedis_common import (
    load_value_sets_from_csv,
    run_measure,
    check_common_exclusions,
    get_patient_birth_date,
    get_resources_by_type,
    calculate_age,
    is_date_in_range,
    measurement_year_dates,
    resource_has_any_code,
    codeable_concept_has_any_code,
    get_encounter_end_date,
    get_medication_date,
    find_conditions_with_codes,
    all_codes,
)

VALUE_SETS = load_value_sets_from_csv("PBH")

# ---------------------------------------------------------------------------
# Intake period: July 1 prior year through June 30 measurement year
# ---------------------------------------------------------------------------

REQUIRED_BETA_BLOCKER_DAYS = 135
MEASUREMENT_INTERVAL_DAYS = 180


def _get_intake_period(measurement_year: int) -> tuple[date, date]:
    """Return the intake period for the PBH measure."""
    return date(measurement_year - 1, 7, 1), date(measurement_year, 6, 30)


def _find_ami_discharge(bundle: dict, measurement_year: int) -> date | None:
    """
    Find the first AMI discharge during the intake period.

    Identifies acute inpatient stays (Inpatient Stay) excluding nonacute stays,
    with an AMI diagnosis on the discharge claim.
    Returns the discharge date of the first qualifying event.
    """
    intake_start, intake_end = _get_intake_period(measurement_year)
    ami_codes = all_codes(VALUE_SETS, "AMI")
    inpatient_codes = all_codes(VALUE_SETS, "Inpatient Stay")
    nonacute_codes = all_codes(VALUE_SETS, "Nonacute Inpatient Stay")

    encounters = get_resources_by_type(bundle, "Encounter")
    discharge_dates: list[date] = []

    for enc in encounters:
        # Must be an inpatient stay
        if not resource_has_any_code(enc, inpatient_codes):
            is_inpatient = False
            for t in enc.get("type", []):
                if codeable_concept_has_any_code(t, inpatient_codes):
                    is_inpatient = True
                    break
            if not is_inpatient:
                continue

        # Exclude nonacute inpatient stays
        if resource_has_any_code(enc, nonacute_codes):
            continue
        is_nonacute = False
        for t in enc.get("type", []):
            if codeable_concept_has_any_code(t, nonacute_codes):
                is_nonacute = True
                break
        if is_nonacute:
            continue

        discharge_date = get_encounter_end_date(enc)
        if not discharge_date or not is_date_in_range(
            discharge_date, intake_start, intake_end
        ):
            continue

        # Check for AMI diagnosis on the encounter
        conditions = get_resources_by_type(bundle, "Condition")
        has_ami = False
        for cond in conditions:
            if resource_has_any_code(cond, ami_codes):
                has_ami = True
                break
        # Also check encounter diagnosis directly
        for diag in enc.get("diagnosis", []):
            cc = diag.get("condition", {})
            if codeable_concept_has_any_code(cc, ami_codes):
                has_ami = True
                break

        if has_ami:
            discharge_dates.append(discharge_date)

    if not discharge_dates:
        return None
    return min(discharge_dates)  # First discharge


def check_eligible_population(
    bundle: dict, measurement_year: int
) -> tuple[bool, list[str]]:
    """
    Check if the patient is in the PBH eligible population.

    Criteria:
    - Age >= 18 as of Dec 31 of measurement year
    - Had an acute inpatient discharge with AMI diagnosis during the intake period
      (July 1 prior year through June 30 measurement year)
    """
    evaluated: list[str] = []
    birth_date = get_patient_birth_date(bundle)
    if not birth_date:
        return False, evaluated

    _, my_end = measurement_year_dates(measurement_year)
    age = calculate_age(birth_date, my_end)
    if age < 18:
        return False, evaluated

    discharge_date = _find_ami_discharge(bundle, measurement_year)
    if discharge_date is None:
        return False, evaluated

    return True, evaluated


def check_exclusions(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check PBH exclusions:
    - Common exclusions (hospice, death, frailty/advanced illness)
    - Beta-blocker contraindication diagnosis (Beta Blocker Contraindications)
    - Asthma exclusion medications (inhaled corticosteroids, bronchodilator combos)
    """
    excluded, refs = check_common_exclusions(bundle, VALUE_SETS, measurement_year)
    if excluded:
        return True, refs

    # Beta-blocker contraindication diagnosis
    contra_codes = all_codes(VALUE_SETS, "Beta Blocker Contraindications")
    if contra_codes:
        # Any time in member history through end of continuous enrollment
        far_past = date(1900, 1, 1)
        _, my_end = measurement_year_dates(measurement_year)
        if find_conditions_with_codes(bundle, contra_codes, far_past, my_end):
            return True, refs

    return False, refs


def _calculate_covered_days(
    bundle: dict,
    discharge_date: date,
    measurement_year: int,
) -> int:
    """
    Calculate the number of days covered by beta-blocker prescriptions
    within the 180-day measurement interval after discharge.
    """
    interval_start = discharge_date
    interval_end = discharge_date + timedelta(days=MEASUREMENT_INTERVAL_DAYS - 1)

    # Collect all beta-blocker medication dispensing events
    covered_days: set[date] = set()

    for rtype in ("MedicationDispense", "MedicationRequest"):
        for med in get_resources_by_type(bundle, rtype):
            med_date = get_medication_date(med)
            if not med_date:
                continue

            # Check if it's a beta-blocker (we check against known medication names)
            # In FHIR, days supply is in daysSupply or quantity
            days_supply = (
                med.get("daysSupply", {}).get("value")
                or med.get("quantity", {}).get("value")
                or 30  # default assumption
            )
            if isinstance(days_supply, str):
                try:
                    days_supply = int(float(days_supply))
                except (ValueError, TypeError):
                    days_supply = 30

            # Calculate which days in the interval are covered
            rx_start = med_date
            rx_end = med_date + timedelta(days=int(days_supply) - 1)

            # Overlap with measurement interval
            overlap_start = max(rx_start, interval_start)
            overlap_end = min(rx_end, interval_end)

            if overlap_start <= overlap_end:
                for i in range((overlap_end - overlap_start).days + 1):
                    covered_days.add(overlap_start + timedelta(days=i))

    return len(covered_days)


def check_numerator(bundle: dict, measurement_year: int) -> tuple[bool, list[str]]:
    """
    Check if the patient meets the PBH numerator:
    At least 135 days of beta-blocker treatment during the 180-day
    measurement interval after AMI discharge.
    """
    evaluated: list[str] = []
    discharge_date = _find_ami_discharge(bundle, measurement_year)
    if discharge_date is None:
        return False, evaluated

    covered = _calculate_covered_days(bundle, discharge_date, measurement_year)

    if covered >= REQUIRED_BETA_BLOCKER_DAYS:
        return True, evaluated

    return False, evaluated


def calculate_pbh_measure(bundle: dict, measurement_year: int = 2025) -> dict:
    """Calculate the PBH measure for a patient bundle."""
    return run_measure(
        bundle=bundle,
        measure_abbreviation="PBH",
        measure_name="Persistence of Beta-Blocker Treatment After a Heart Attack",
        measurement_year=measurement_year,
        check_eligible_population_fn=check_eligible_population,
        check_exclusions_fn=check_exclusions,
        check_numerator_fn=check_numerator,
    )
