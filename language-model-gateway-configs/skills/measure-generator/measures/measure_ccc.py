"""
HEDIS MY 2025 - Children With Chronic Conditions (CCC)

This measure provides information on parents' experience with their child's
Medicaid organization for the population of children with chronic conditions.
Three composites summarize satisfaction: (1) Access to Specialized Services,
(2) Family Centered Care: Personal Doctor Who Knows Child, and
(3) Coordination of Care for Children With Chronic Conditions. Additional
question summary rates cover Access to Prescription Medicines and Family
Centered Care: Getting Needed Information.

NOTE: This measure is survey-based and cannot be calculated from individual
patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_ccc_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Children With Chronic Conditions is a survey-based measure.

    It requires CAHPS survey responses from parents of children with chronic
    conditions about their health plan experience and cannot be calculated
    from an individual patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="CCC",
        measure_name="Children With Chronic Conditions",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
