"""
HEDIS MY 2025 - CAHPS Health Plan Survey 5.1H, Child Version (CPC)

This measure provides information on parents' experience with their child's
Medicaid organization. Results summarize member experiences through four
global ratings (All Health Care, Health Plan, Personal Doctor, Specialist
Seen Most Often), four composite scores (Customer Service, Getting Care
Quickly, Getting Needed Care, How Well Doctors Communicate), and question
summary rates including Coordination of Care.

NOTE: This measure is survey-based and cannot be calculated from individual
patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_cpc_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    CAHPS Health Plan Survey, Child Version is a survey-based measure.

    It requires CAHPS survey responses from parents about their child's
    health plan experience and cannot be calculated from an individual
    patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="CPC",
        measure_name="CAHPS Health Plan Survey 5.1H, Child Version",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
