"""
HEDIS MY 2025 - Language Diversity of Membership (LDM)

An unduplicated count and percentage of members enrolled at any time during
the measurement year by spoken language preferred for health care and
preferred language for written materials. Reported for Commercial, Medicaid,
and Medicare product lines separately.

NOTE: This measure is a population-level descriptive measure and cannot be
calculated from individual patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_ldm_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Language Diversity of Membership is a population-level descriptive measure.

    It requires population-level enrollment and language preference data
    aggregated across all members and cannot be calculated from an individual
    patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="LDM",
        measure_name="Language Diversity of Membership",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
