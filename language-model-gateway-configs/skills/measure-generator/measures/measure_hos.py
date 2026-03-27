"""
HEDIS MY 2025 - Medicare Health Outcomes Survey (HOS)

This measure provides a general indication of how well a Medicare Advantage
Organization (MAO) manages the physical and mental health of its members.
The survey measures physical and mental health status at the beginning of a
2-year period and again at the end, when a change score is calculated. Each
member's health status is categorized as "better than expected," "the same as
expected" or "worse than expected," accounting for death and risk-adjustment
factors.

NOTE: This measure is survey-based and cannot be calculated from individual
patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_hos_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Medicare Health Outcomes Survey is a survey-based measure.

    It requires HOS survey responses administered over a 2-year period
    and cannot be calculated from an individual patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="HOS",
        measure_name="Medicare Health Outcomes Survey",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
