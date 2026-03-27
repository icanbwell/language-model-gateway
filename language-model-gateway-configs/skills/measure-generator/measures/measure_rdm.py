"""
HEDIS MY 2025 - Race/Ethnicity Diversity of Membership (RDM)

An unduplicated count and percentage of members enrolled any time during
the measurement year, by race and ethnicity. Reported for Commercial,
Medicaid, and Medicare product lines separately, with data source tracking
(direct, imputed, unknown, no data) and standard OMB race/ethnicity
reporting categories.

NOTE: This measure is a population-level descriptive measure and cannot be
calculated from individual patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_rdm_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Race/Ethnicity Diversity of Membership is a population-level descriptive measure.

    It requires population-level enrollment and race/ethnicity data
    aggregated across all members and cannot be calculated from an individual
    patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="RDM",
        measure_name="Race/Ethnicity Diversity of Membership",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
