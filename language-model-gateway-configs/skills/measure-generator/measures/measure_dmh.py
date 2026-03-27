"""
HEDIS MY 2025 - Diagnosed Mental Health Disorders (DMH)

The percentage of members 1 year of age and older who were diagnosed with a
mental health disorder during the measurement year. Reported for Commercial,
Medicaid, and Medicare product lines with age stratifications (1-17, 18-64,
65+, Total).

NOTE: This is a descriptive prevalence measure. Neither a higher nor a lower
rate indicates better performance. It reports diagnosed prevalence across an
enrolled population and cannot be meaningfully calculated from an individual
patient's FHIR clinical data alone.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_dmh_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Diagnosed Mental Health Disorders is a descriptive prevalence measure.

    It reports the diagnosed prevalence of mental health disorders across an
    enrolled population. As a prevalence measure where neither higher nor
    lower rates indicate better performance, it cannot be meaningfully
    calculated from an individual patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="DMH",
        measure_name="Diagnosed Mental Health Disorders",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
