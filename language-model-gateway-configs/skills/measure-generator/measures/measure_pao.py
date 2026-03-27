"""
HEDIS MY 2025 - Physical Activity in Older Adults (PAO)

This measure assesses different facets of promoting physical activity in
Medicare members 65 years and older: (1) Discussing Physical Activity - the
percentage who spoke with a provider about their level of exercise or physical
activity, and (2) Advising Physical Activity - the percentage who received
advice to start, increase or maintain their level of exercise or physical
activity.

NOTE: This measure is survey-based (collected via the Medicare Health Outcomes
Survey) and cannot be calculated from individual patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_pao_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Physical Activity in Older Adults is a survey-based measure.

    It requires HOS survey responses about physical activity discussions
    and advice and cannot be calculated from an individual patient's FHIR
    Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="PAO",
        measure_name="Physical Activity in Older Adults",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
