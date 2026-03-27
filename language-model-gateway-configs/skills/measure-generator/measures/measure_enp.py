"""
HEDIS MY 2025 - Enrollment by Product Line (ENP)

The total number of members enrolled in the product line, stratified by age.
Reported as member months converted to member years for Medicaid, Commercial,
and Medicare product lines across age bands from less than 1 year through 90+.

NOTE: This measure is a population-level descriptive measure and cannot be
calculated from individual patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_enp_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Enrollment by Product Line is a population-level descriptive measure.

    It requires population-level enrollment data aggregated across all
    members by product line and age stratification and cannot be calculated
    from an individual patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="ENP",
        measure_name="Enrollment by Product Line",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
