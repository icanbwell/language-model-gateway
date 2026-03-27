"""
HEDIS MY 2025 - CAHPS Health Plan Survey 5.1H, Adult Version (CPA)

This measure provides information on the experiences of commercial and
Medicaid members with the organization and gives a general indication of how
well the organization meets members' expectations. Results summarize member
experiences through four global ratings (All Health Care, Health Plan,
Personal Doctor, Specialist Seen Most Often), five composite scores (Claims
Processing, Customer Service, Getting Care Quickly, Getting Needed Care, How
Well Doctors Communicate), and question summary rates including Coordination
of Care.

NOTE: This measure is survey-based and cannot be calculated from individual
patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_cpa_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    CAHPS Health Plan Survey, Adult Version is a survey-based measure.

    It requires CAHPS survey responses from health plan members about their
    experiences and cannot be calculated from an individual patient's FHIR
    Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="CPA",
        measure_name="CAHPS Health Plan Survey 5.1H, Adult Version",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
