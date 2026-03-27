"""
HEDIS MY 2025 - Management of Urinary Incontinence in Older Adults (MUI)

This measure assesses management of urinary incontinence in Medicare members
65 years and older through three components: (1) Discussing Urinary
Incontinence, (2) Discussing Treatment of Urinary Incontinence, and
(3) Impact of Urinary Incontinence (where a lower rate indicates better
performance).

NOTE: This measure is survey-based (collected via the Medicare Health Outcomes
Survey) and cannot be calculated from individual patient FHIR clinical data.
"""

from typing import Any

from .hedis_common import build_measure_report, get_patient_id


def calculate_mui_measure(bundle: dict, measurement_year: int = 2025) -> dict[str, Any]:
    """
    Management of Urinary Incontinence in Older Adults is a survey-based measure.

    It requires HOS survey responses about urinary incontinence discussions
    and treatment and cannot be calculated from an individual patient's FHIR
    Bundle.
    Returns an empty MeasureReport.
    """
    return build_measure_report(
        patient_id=get_patient_id(bundle),
        measure_abbreviation="MUI",
        measure_name="Management of Urinary Incontinence in Older Adults",
        measurement_year=measurement_year,
        initial_population=False,
        denominator_exclusion=False,
        numerator=False,
        evaluated_resources=[],
    )
