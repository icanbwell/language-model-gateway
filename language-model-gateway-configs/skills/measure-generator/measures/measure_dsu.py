"""
HEDIS MY 2025 - Diagnosed Substance Use Disorders (DSU)

The percentage of members 13 years of age and older who were diagnosed with a
substance use disorder during the measurement year. Four rates are reported:
(1) alcohol disorder, (2) opioid disorder, (3) other or unspecified drugs,
and (4) any substance use disorder. Reported for Commercial, Medicaid, and
Medicare product lines with age stratifications (13-17, 18-64, 65+, Total).

NOTE: This is a descriptive prevalence measure. Neither a higher nor a lower
rate indicates better performance. It reports diagnosed prevalence across an
enrolled population and cannot be meaningfully calculated from an individual
patient's FHIR clinical data alone.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_dsu_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Diagnosed Substance Use Disorders is a descriptive prevalence measure.

    It reports the diagnosed prevalence of substance use disorders across an
    enrolled population. As a prevalence measure where neither higher nor
    lower rates indicate better performance, it cannot be meaningfully
    calculated from an individual patient's FHIR Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="DSU",
        measure_name="Diagnosed Substance Use Disorders",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
