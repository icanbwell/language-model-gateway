# FHIR MeasureReport Output Template

The generated Python code must produce a FHIR R4 MeasureReport resource. This document defines the exact structure.

## MeasureReport Resource Structure

```json
{
  "resourceType": "MeasureReport",
  "id": "<generated-uuid>",
  "meta": {
    "profile": ["http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm"]
  },
  "status": "complete",
  "type": "individual",
  "measure": "http://ncqa.org/fhir/Measure/<measure-abbreviation>",
  "subject": {
    "reference": "Patient/<patient-id>"
  },
  "date": "<calculation-datetime-ISO8601>",
  "period": {
    "start": "<measurement-year>-01-01",
    "end": "<measurement-year>-12-31"
  },
  "group": [
    {
      "code": {
        "coding": [
          {
            "system": "http://ncqa.org/fhir/CodeSystem/measure-group",
            "code": "<measure-abbreviation>",
            "display": "<measure-full-name>"
          }
        ]
      },
      "population": [
        {
          "code": {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                "code": "initial-population",
                "display": "Initial Population"
              }
            ]
          },
          "count": 1
        },
        {
          "code": {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                "code": "denominator",
                "display": "Denominator"
              }
            ]
          },
          "count": 1
        },
        {
          "code": {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                "code": "denominator-exclusion",
                "display": "Denominator Exclusion"
              }
            ]
          },
          "count": 0
        },
        {
          "code": {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                "code": "numerator",
                "display": "Numerator"
              }
            ]
          },
          "count": 1
        }
      ],
      "measureScore": {
        "value": 1.0
      }
    }
  ],
  "evaluatedResource": [
    {
      "reference": "Patient/<patient-id>"
    },
    {
      "reference": "Condition/<condition-id>"
    },
    {
      "reference": "Observation/<observation-id>"
    }
  ]
}
```

## Population Count Logic

For an **individual** MeasureReport (single patient), population counts are 0 or 1:

| Population | Count = 1 when | Count = 0 when |
|---|---|---|
| initial-population | Patient meets age, enrollment, benefit, and event/diagnosis criteria | Patient does not meet criteria |
| denominator | Patient is in initial population AND not excluded | Patient not in initial population or excluded |
| denominator-exclusion | Patient meets any required exclusion criteria | No exclusion criteria met |
| numerator | Patient meets the numerator clinical criteria | Patient does not meet numerator criteria |

## measureScore Calculation

For an individual report:
- `measureScore.value` = `numerator.count / denominator.count`
- If `denominator.count` = 0, omit measureScore (or set to null)
- For a compliant patient: `1.0`
- For a non-compliant patient: `0.0`

## Measures With Multiple Rates/Indicators

Some measures have multiple numerators or indicators (e.g., TRC has 4 indicators). Each indicator is a separate `group` entry in the MeasureReport:

```json
{
  "group": [
    {
      "code": { "coding": [{ "code": "indicator-1" }] },
      "population": [ ... ],
      "measureScore": { "value": 1.0 }
    },
    {
      "code": { "coding": [{ "code": "indicator-2" }] },
      "population": [ ... ],
      "measureScore": { "value": 0.0 }
    }
  ]
}
```

## evaluatedResource

List all FHIR resources that were used in the calculation. This provides traceability back to the source data. Include references to:
- The Patient resource
- Condition resources used for diagnosis criteria
- Encounter resources used for visit criteria
- Observation resources used for lab/vital results
- MedicationDispense/MedicationRequest resources used for medication criteria
- Procedure resources used for procedure criteria
- Coverage resources used for enrollment criteria

## Python Code Template for Building MeasureReport

```python
import uuid
from datetime import datetime, date
from typing import Any


def build_measure_report(
    patient_id: str,
    measure_abbreviation: str,
    measure_name: str,
    measurement_year: int,
    initial_population: bool,
    denominator: bool,
    denominator_exclusion: bool,
    numerator: bool,
    evaluated_resources: list[str],
) -> dict[str, Any]:
    """Build a FHIR MeasureReport for an individual patient."""

    denominator_count = 1 if (initial_population and not denominator_exclusion) else 0
    numerator_count = 1 if (denominator_count == 1 and numerator) else 0

    measure_score = None
    if denominator_count > 0:
        measure_score = numerator_count / denominator_count

    report: dict[str, Any] = {
        "resourceType": "MeasureReport",
        "id": str(uuid.uuid4()),
        "status": "complete",
        "type": "individual",
        "measure": f"http://ncqa.org/fhir/Measure/{measure_abbreviation}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "date": datetime.now().isoformat(),
        "period": {
            "start": f"{measurement_year}-01-01",
            "end": f"{measurement_year}-12-31",
        },
        "group": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://ncqa.org/fhir/CodeSystem/measure-group",
                            "code": measure_abbreviation,
                            "display": measure_name,
                        }
                    ]
                },
                "population": [
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "initial-population",
                                    "display": "Initial Population",
                                }
                            ]
                        },
                        "count": 1 if initial_population else 0,
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "denominator",
                                    "display": "Denominator",
                                }
                            ]
                        },
                        "count": denominator_count,
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "denominator-exclusion",
                                    "display": "Denominator Exclusion",
                                }
                            ]
                        },
                        "count": 1 if denominator_exclusion else 0,
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "numerator",
                                    "display": "Numerator",
                                }
                            ]
                        },
                        "count": numerator_count,
                    },
                ],
            }
        ],
        "evaluatedResource": [
            {"reference": ref} for ref in evaluated_resources
        ],
    }

    if measure_score is not None:
        report["group"][0]["measureScore"] = {"value": measure_score}

    return report
```
