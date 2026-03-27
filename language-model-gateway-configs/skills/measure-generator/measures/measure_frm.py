"""
HEDIS MY 2025 - Fall Risk Management (FRM)

This measure assesses different facets of fall risk management for Medicare
members 65 years and older: (1) Discussing Fall Risk - the percentage who
discussed falls or problems with balance or walking with their practitioner,
and (2) Managing Fall Risk - the percentage who received a recommendation for
how to prevent falls or treat problems with balance or walking.

NOTE: This measure is survey-based (collected via the Medicare Health Outcomes
Survey) and cannot be calculated from individual patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_frm_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Fall Risk Management is a survey-based measure.

    It requires HOS survey responses about fall risk discussions and
    management recommendations and cannot be calculated from an individual
    patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="FRM",
        measure_name="Fall Risk Management",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
